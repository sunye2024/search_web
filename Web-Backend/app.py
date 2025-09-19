# /unified_service/app.py

import os
import logging
import config
import sys
from flask import Flask, send_from_directory, g, jsonify
from flask_cors import CORS
from config import Config
from routes import api as api_blueprint
from services import search_service
from flask.json.provider import DefaultJSONProvider
from db_adapter import DatabaseAdapter

# 尝试导入database_config
DB_CONFIG = None
try:
    # 添加父目录到Python路径，使其能够导入database_config
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)
    
    from database_config import DatabaseConfig
    DB_CONFIG = DatabaseConfig()
    logging.info("成功导入database_config")
except ImportError as e:
    logging.warning(f"无法导入database_config，将使用环境变量配置: {str(e)}")


# 自定义 JSONProvider，确保输出中文
class CustomJSONProvider(DefaultJSONProvider):
    def dumps(self, obj, **kwargs):
        kwargs.setdefault("ensure_ascii", False)  # 关闭 ASCII 转义
        return super().dumps(obj, **kwargs)
    
    def loads(self, s, **kwargs):
        return super().loads(s, **kwargs)

# 全局数据库适配器实例
# 注意：这只是一个全局引用，实际初始化在app创建时
# 避免循环导入问题
db_adapter = None

def setup_database_config():
    """设置数据库配置"""
    # 如果有DB_CONFIG，则使用它
    if DB_CONFIG:
        try:
            # 设置MongoDB配置
            mongodb_config = {
                'host': os.environ.get('MONGODB_HOST', 'localhost'),
                'port': int(os.environ.get('MONGODB_PORT', 27017)),
                'username': os.environ.get('MONGODB_USERNAME', ''),
                'password': os.environ.get('MONGODB_PASSWORD', ''),
                'db_name': os.environ.get('MONGODB_DB', 'admin'),
                'collection_name': os.environ.get('MONGODB_COLLECTION', 'event')
            }
            DB_CONFIG.set_database_config('mongodb', mongodb_config)
            
            # 设置Nebula配置（即使当前不可用，也要预留配置）
            nebula_config = {
                'host': os.environ.get('NEBULA_HOST', 'localhost'),
                'port': int(os.environ.get('NEBULA_PORT', 9669)),
                'username': os.environ.get('NEBULA_USERNAME', 'root'),
                'password': os.environ.get('NEBULA_PASSWORD', 'nebula'),
                'space': os.environ.get('NEBULA_SPACE', 'search_space')
            }
            DB_CONFIG.set_database_config('nebula', nebula_config)
            
            logging.info("已设置数据库配置")
        except Exception as e:
            logging.warning(f"设置数据库配置时出错: {str(e)}")


def create_app(config_class=Config):
    """工厂函数，用于创建和配置Flask应用"""
    global db_adapter
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # 全局替换 JSONProvider
    app.json = CustomJSONProvider(app)
    
    # 配置日志
    logging.basicConfig(
        level=app.config['LOG_LEVEL'],
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 设置环境变量
    os.environ['HF_ENDPOINT'] = app.config['HF_ENDPOINT']
    
    # 如果环境中未设置MONGODB_COLLECTION，则使用默认值
    if not os.environ.get('MONGODB_COLLECTION'):
        os.environ['MONGODB_COLLECTION'] = 'event'  # 默认集合名称

    # 初始化数据库配置
    setup_database_config()

    # 初始化CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}}) # 仅对/api路径下的路由启用CORS

    # 初始化数据库适配器
    db_adapter = DatabaseAdapter()
    
    # 在应用上下文中初始化搜索服务
    with app.app_context():
        search_service.init_search_clients(app.config)

    # 添加数据库适配器到应用上下文
    @app.before_request
    def before_request():
        g.db = db_adapter

    # 注册Blueprint
    # 为所有路由添加 /api 前缀
    app.register_blueprint(api_blueprint, url_prefix='/api')

    @app.route('/uploads/<filename>')
    def uploaded_files(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # 添加根路径处理程序
    @app.route('/')
    def home():
        """应用程序首页，显示API信息和可用端点"""
        return jsonify({
            "message": "欢迎使用搜索服务API",
            "api_version": "1.0",
            "available_endpoints": [
                "/api/getAllEvents",
                "/api/getEventsByKeyword",
                "/api/getEventById",
                "/api/getDatabaseStats",
                "/api/search/text",
                "/api/search/picture",
                "/api/search/video",
                "/api/upload",
                "/api/db-status",
                "/api/switch-db/<db_type>"
            ],
            "note": "所有API端点都需要通过/api前缀访问"
        })
    
    # 检查数据库连接状态
    @app.route('/api/db-status')
    def db_status():
        status_info = {
            'status': 'success',
            'databases': {}
        }
        
        # 检查所有数据库的状态
        for db_type, error_msg in getattr(db_adapter, 'error_messages', {}).items():
            if error_msg:
                status_info['status'] = 'partial'
                status_info['databases'][db_type] = {
                    'status': 'error',
                    'message': error_msg
                }
            else:
                status_info['databases'][db_type] = {
                    'status': 'success',
                    'message': 'Connected successfully'
                }
        
        # 如果没有错误信息，添加可用数据库信息
        if not getattr(db_adapter, 'error_messages', None):
            for db_type in getattr(db_adapter, 'db_services', []):
                status_info['databases'][db_type] = {
                    'status': 'success',
                    'message': 'Connected successfully'
                }
        
        # 添加默认数据库信息
        if hasattr(db_adapter, 'default_db_type'):
            status_info['default_db'] = db_adapter.default_db_type
        
        if status_info['status'] == 'error':
            return jsonify(status_info), 500
        
        return jsonify(status_info)
    
    # 切换默认数据库的API（可选，用于动态切换数据库）
    @app.route('/api/switch-db/<db_type>')
    def switch_db(db_type):
        if hasattr(db_adapter, 'set_default_db') and db_adapter.set_default_db(db_type):
            return jsonify({
                'status': 'success',
                'message': f'Default database switched to {db_type}',
                'current_default': db_adapter.default_db_type
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Database type {db_type} not available'
            }), 400

    app.logger.info("应用启动成功，运行在 http://0.0.0.0:5000")
    
    # 记录数据库适配器状态
    if hasattr(db_adapter, 'error_messages') and any(db_adapter.error_messages.values()):
        for db_type, error_msg in db_adapter.error_messages.items():
            if error_msg:
                app.logger.warning(f"{db_type} 数据库适配器警告: {error_msg}")
    else:
        app.logger.info(f"数据库适配器已成功初始化")
        
    return app

app = create_app()



if __name__ == '__main__':
    # 使用 gunicorn 或 uwsgi 部署时，不会执行这部分
    # 仅用于开发环境
    app.run(host='0.0.0.0', port=5000, debug=True)