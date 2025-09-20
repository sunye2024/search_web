#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
应用程序启动脚本
这个脚本替代了bat文件，用于设置必要的环境变量并启动应用程序
"""

import os
import sys
import subprocess
import time
import logging

# 设置日志格式
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 添加当前目录到Python路径，使其能够导入database_config
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 尝试导入database_config
try:
    from database_config import DatabaseConfig
    DB_CONFIG = DatabaseConfig()
    logger.info("成功导入database_config")
except ImportError as e:
    logger.warning(f"无法导入database_config，将使用默认配置: {str(e)}")
    DB_CONFIG = None


def set_environment_variables():
    """设置必要的环境变量"""
    # 默认环境变量设置
    os.environ['MONGODB_COLLECTION'] = 'event'
    os.environ['DB_TYPE'] = 'mongodb'
    os.environ['MONGODB_HOST'] = 'localhost'
    os.environ['MONGODB_PORT'] = '27017'
    os.environ['MONGODB_DB'] = 'admin'
    os.environ['MONGODB_USERNAME'] = ''
    os.environ['MONGODB_PASSWORD'] = ''
    
    # 如果有database_config，则使用其中的配置
    if DB_CONFIG:
        try:
            # 设置MongoDB配置
            mongo_config = DB_CONFIG.get_mongodb_config()
            if mongo_config:
                for key, value in mongo_config.items():
                    env_key = f"MONGODB_{key.upper()}"
                    if value is not None:
                        os.environ[env_key] = str(value)
            
            # 设置Nebula配置（如果有）
            nebula_config = DB_CONFIG.get_nebula_config()
            if nebula_config:
                for key, value in nebula_config.items():
                    env_key = f"NEBULA_{key.upper()}"
                    if value is not None:
                        os.environ[env_key] = str(value)
            
            logger.info("已从database_config加载数据库配置")
        except Exception as e:
            logger.warning(f"加载database_config时出错: {str(e)}")
    
    print("已设置环境变量：")
    print(f"  MONGODB_COLLECTION: {os.environ['MONGODB_COLLECTION']}")
    print(f"  DB_TYPE: {os.environ['DB_TYPE']}")
    print(f"  MONGODB_HOST: {os.environ['MONGODB_HOST']}")
    print(f"  MONGODB_PORT: {os.environ['MONGODB_PORT']}")
    print(f"  MONGODB_DB: {os.environ['MONGODB_DB']}")


def check_mongodb_connection():
    """检查MongoDB连接是否可用"""
    try:
        # 尝试导入pymongo模块
        import pymongo
        from pymongo.errors import ConnectionFailure
        
        # 从环境变量获取MongoDB配置
        host = os.environ.get('MONGODB_HOST', 'localhost')
        port = int(os.environ.get('MONGODB_PORT', 27017))
        db_name = os.environ.get('MONGODB_DB', 'admin')
        
        # 创建连接字符串
        username = os.environ.get('MONGODB_USERNAME', '')
        password = os.environ.get('MONGODB_PASSWORD', '')
        
        if username and password:
            connection_string = f"mongodb://{username}:{password}@{host}:{port}/{db_name}"
        else:
            connection_string = f"mongodb://{host}:{port}/{db_name}"
        
        # 尝试连接MongoDB
        client = pymongo.MongoClient(connection_string, serverSelectionTimeoutMS=2000)
        client.server_info()  # 这将抛出异常如果连接失败
        
        # 验证集合是否存在
        db = client[db_name]
        collection_name = os.environ.get('MONGODB_COLLECTION', 'event')
        collections = db.list_collection_names()
        
        if collection_name in collections:
            print(f"✓ MongoDB连接成功：{host}:{port}/{db_name}")
            print(f"✓ 集合 '{collection_name}' 存在")
        else:
            print(f"✓ MongoDB连接成功：{host}:{port}/{db_name}")
            print(f"⚠ 警告：集合 '{collection_name}' 不存在")
        
        return True
    except ImportError:
        print("⚠ 警告：未安装pymongo模块，无法检查MongoDB连接")
        return True  # 继续启动应用，让应用自己处理
    except ConnectionFailure:
        print("✗ MongoDB连接失败，请确保MongoDB服务正在运行")
        return False
    except Exception as e:
        print(f"✗ 检查MongoDB连接时发生错误：{str(e)}")
        return False


def start_application():
    """启动应用程序"""
    # 导航到应用目录
    app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'graph-database-backend_1')
    
    if not os.path.exists(app_dir):
        print(f"错误：应用目录不存在：{app_dir}")
        return False
    
    # 切换到应用目录
    os.chdir(app_dir)
    
    print(f"已切换到应用目录：{os.getcwd()}")
    
    # 检查app.py文件是否存在
    if not os.path.exists('app.py'):
        print("错误：app.py文件不存在")
        return False
    
    try:
        # 启动应用程序
        print("正在启动应用程序...")
        print("注意：应用启动后，可以通过按Ctrl+C停止")
        
        # 使用subprocess启动应用程序，并等待它结束
        process = subprocess.Popen(
            [sys.executable, 'app.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False
        )
        
        # 实时打印输出
        while True:
            stdout_line = process.stdout.readline()
            stderr_line = process.stderr.readline()
            
            if stdout_line:
                print(f"[应用输出] {stdout_line.strip()}")
            if stderr_line:
                print(f"[应用错误] {stderr_line.strip()}")
            
            # 检查进程是否已经结束
            if process.poll() is not None:
                # 读取剩余的输出
                for line in process.stdout.readlines():
                    print(f"[应用输出] {line.strip()}")
                for line in process.stderr.readlines():
                    print(f"[应用错误] {line.strip()}")
                
                if process.returncode != 0:
                    print(f"应用程序异常退出，返回码：{process.returncode}")
                else:
                    print("应用程序已正常退出")
                break
            
            # 短暂休眠，避免CPU占用过高
            time.sleep(0.1)
        
        return True
    except Exception as e:
        print(f"启动应用程序时发生错误：{str(e)}")
        return False


def check_available_databases():
    """检查可用的数据库"""
    if DB_CONFIG:
        try:
            available_dbs = DB_CONFIG.get_available_dbs()
            if available_dbs:
                print("\n可用的数据库类型：")
                for db_type in available_dbs:
                    status = "✓ 已配置" if DB_CONFIG.is_db_configured(db_type) else "⚠ 未完全配置"
                    print(f"  {db_type}: {status}")
        except Exception as e:
            logger.warning(f"检查可用数据库时出错: {str(e)}")


def main():
    """主函数"""
    print("=" * 60)
    print("应用程序启动工具")
    print("=" * 60)
    
    # 设置环境变量
    set_environment_variables()
    
    # 检查可用数据库
    check_available_databases()
    
    # 检查MongoDB连接
    if not check_mongodb_connection():
        choice = input("是否继续启动应用程序？(y/n): ")
        if choice.lower() != 'y':
            print("已取消启动")
            return
    
    # 启动应用程序
    start_application()
    
    # 等待用户按任意键退出
    print("\n应用程序已停止")
    input("按任意键退出...")


if __name__ == '__main__':
    main()