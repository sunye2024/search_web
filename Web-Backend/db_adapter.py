import os
import os
import sys

# 尝试导入database_config，如果失败则创建默认配置
try:
    from database_config import DB_CONFIG
except ImportError:
    # 如果导入失败，创建一个基本的默认配置类
    class DefaultDBConfig:
        def get_database_config(self, db_type):
            # 为MongoDB提供默认配置
            if db_type == 'mongodb':
                return {
                    'host': os.environ.get('MONGODB_HOST', 'localhost'),
                    'port': int(os.environ.get('MONGODB_PORT', '27017')),
                    'username': os.environ.get('MONGODB_USERNAME', ''),
                    'password': os.environ.get('MONGODB_PASSWORD', ''),
                    'db_name': os.environ.get('MONGODB_DB', 'news_search'),
                    'collection_name': os.environ.get('MONGODB_COLLECTION', 'events')
                }
            # 为Nebula提供默认配置
            elif db_type == 'nebula':
                return {
                    'host': os.environ.get('NEBULA_HOST', 'localhost'),
                    'port': int(os.environ.get('NEBULA_PORT', '9669')),
                    'username': os.environ.get('NEBULA_USERNAME', 'root'),
                    'password': os.environ.get('NEBULA_PASSWORD', 'nebula'),
                    'space': os.environ.get('NEBULA_SPACE', 'news')
                }
            return {}
    
    DB_CONFIG = DefaultDBConfig()
    print("警告: 无法导入database_config模块，将使用默认配置")

# 确保能导入MongoDBService
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.mongodb_service import MongoDBService

class DatabaseAdapter:
    """数据库适配器，支持同时使用多个数据库"""
    def __init__(self):
        # 存储所有数据库服务实例的字典
        self.db_services = {}
        # 当前默认使用的数据库类型
        self.default_db_type = os.environ.get('DB_TYPE', 'mongodb').lower()
        # 记录错误信息
        self.error_messages = {}
        
        # 初始化所有支持的数据库服务
        self._initialize_all_services()
        
    @property
    def db_service(self):
        """获取当前默认的数据库服务"""
        return self.get_service()
        
    @property
    def db_type(self):
        """获取当前默认的数据库类型"""
        return self.default_db_type

    def _initialize_all_services(self):
        """初始化所有支持的数据库服务"""
        # 初始化MongoDB服务
        self._initialize_service('mongodb')
        
        # 初始化其他数据库服务（如NebulaGraph）
        try:
            self._initialize_service('nebula')
        except Exception as e:
            self.error_messages['nebula'] = f"无法初始化Nebula服务: {str(e)}"
            # 即使其他数据库初始化失败，也继续运行，只使用可用的数据库

    def _initialize_service(self, db_type):
        """初始化指定类型的数据库服务"""
        try:
            if db_type == 'mongodb':
                # 使用配置初始化MongoDB服务
                config = DB_CONFIG.get_database_config('mongodb')
                self.db_services['mongodb'] = MongoDBService(
                    host=config['host'],
                    port=config['port'],
                    username=config['username'],
                    password=config['password'],
                    db_name=config['db_name'],
                    collection_name=config['collection_name']
                )
                connected = self.db_services['mongodb'].connect()
                if not connected:
                    self.error_messages['mongodb'] = "MongoDB连接失败，请检查配置"
            elif db_type == 'nebula':
                # 初始化NebulaGraph服务
                from services.nebula_service import NebulaService
                config = DB_CONFIG.get_database_config('nebula')
                self.db_services['nebula'] = NebulaService(
                    host=config['host'],
                    port=config['port'],
                    username=config['username'],
                    password=config['password'],
                    space=config['space']
                )
                # 初始化Nebula服务池
                if hasattr(self.db_services['nebula'], 'init_nebula_pool'):
                    self.db_services['nebula'].init_nebula_pool()
            # 添加更多数据库类型...
        except Exception as e:
            self.error_messages[db_type] = f"{db_type}数据库初始化错误: {str(e)}"
            # 不使用模拟服务，而是让调用方决定如何处理错误

    def set_default_db(self, db_type):
        """设置默认使用的数据库类型"""
        if db_type.lower() in self.db_services:
            self.default_db_type = db_type.lower()
            return True
        return False

    def get_service(self, db_type=None):
        """获取指定类型的数据库服务实例，如果未指定则返回默认服务"""
        if db_type:
            return self.db_services.get(db_type.lower())
        return self.db_services.get(self.default_db_type)

    def execute_query(self, query, params=None):
        """执行查询"""
        try:
            # 获取当前数据库服务
            service = self.get_service()
            if not service:
                return {'error': f'未找到数据库服务: {self.default_db_type}'}
                
            if hasattr(service, 'execute_query'):
                return service.execute_query(query, params)
            elif hasattr(service, 'search_events') and self.db_type == 'mongodb':
                # 对于MongoDB，转换查询格式
                mongo_query = self._convert_to_mongo_query(query)
                # 使用默认分页参数
                events, total = service.search_events(query=mongo_query, page=1, page_size=10)
                return {'data': events, 'total': total}
            else:
                # 如果没有相应方法，返回模拟数据
                return {'data': [], 'error': '不支持的查询方法'}
        except Exception as e:
            return {'error': str(e)}

    def get_event_by_id(self, event_id):
        """根据ID获取事件"""
        try:
            # 获取当前数据库服务
            service = self.get_service()
            if not service:
                return {'error': f'未找到数据库服务: {self.default_db_type}'}
                
            if hasattr(service, 'get_event_by_id'):
                return service.get_event_by_id(event_id)
            else:
                return None
        except Exception as e:
            return {'error': str(e)}

    def insert_event(self, event_data):
        """插入事件"""
        try:
            # 获取当前数据库服务
            service = self.get_service()
            if not service:
                return {'error': f'未找到数据库服务: {self.default_db_type}'}
                
            if hasattr(service, 'insert_event'):
                return service.insert_event(event_data)
            else:
                return None
        except Exception as e:
            return {'error': str(e)}

    def update_event(self, event_id, update_data):
        """更新事件"""
        try:
            # 获取当前数据库服务
            service = self.get_service()
            if not service:
                return {'error': f'未找到数据库服务: {self.default_db_type}'}
                
            if hasattr(service, 'update_event'):
                return service.update_event(event_id, update_data)
            else:
                return False
        except Exception as e:
            return {'error': str(e)}

    def delete_event(self, event_id):
        """删除事件"""
        try:
            # 获取当前数据库服务
            service = self.get_service()
            if not service:
                return {'error': f'未找到数据库服务: {self.default_db_type}'}
                
            if hasattr(service, 'delete_event'):
                return service.delete_event(event_id)
            else:
                return False
        except Exception as e:
            return {'error': str(e)}
    
    def get_statistics(self):
        """获取数据库统计信息"""
        try:
            # 获取当前数据库服务
            service = self.get_service()
            if not service:
                return {'error': f'未找到数据库服务: {self.default_db_type}'}
                
            if hasattr(service, 'get_statistics'):
                return service.get_statistics()
            else:
                return {'total_events': 0, 'risk_events': 0, 'platforms': [], 'types': []}
        except Exception as e:
            return {'error': str(e)}
    
    def search_events(self, query=None, page=1, page_size=10, sort_by=None, sort_order=1):
        """搜索事件"""
        try:
            # 获取当前数据库服务
            service = self.get_service()
            if not service:
                return [], 0
                
            if hasattr(service, 'search_events'):
                # Convert page_size to limit for backward compatibility
                return service.search_events(query, page, page_size, sort_by, sort_order)
            else:
                return [], 0
        except Exception as e:
            return [], 0

    def _convert_to_mongo_query(self, query):
        """将通用查询转换为MongoDB查询格式"""
        # 这里可以根据实际需求进行更复杂的转换
        if isinstance(query, dict):
            return query
        # 如果是字符串，尝试解析为查询条件
        elif isinstance(query, str):
            # 简单的文本搜索
            return {"$text": {"$search": query}}
        else:
            return {}

    def close(self):
        """关闭数据库连接"""
        try:
            # 获取当前数据库服务
            service = self.get_service()
            if service and hasattr(service, 'disconnect'):
                service.disconnect()
        except Exception as e:
            print(f"关闭数据库连接错误: {str(e)}")


class MockDatabaseService:
    """模拟数据库服务，用于在真实数据库不可用时提供基础功能"""
    def __init__(self):
        # 模拟数据存储
        self.mock_data = []
        self.next_id = 1
        
        # 添加一些示例数据，基于用户提供的数据格式
        self._add_mock_data()

    def _add_mock_data(self):
        """添加示例数据"""
        # 基于用户提供的数据格式创建完整的示例数据
        sample_data = {
            "_id": "68bda4292a53c85d40e10c7b",
            "Event": "任嘉伦#任嘉伦春晚进行时拒绝三连##任嘉伦周生辰破次元同框#总有那么一个人，在那么一瞬间让人怦然心动，猝不及防。从此以后，对于世界而言，你只是一个人，而对于牵挂你的我们而言，你是整个世界。无论你能走多远，我们都会一直在，浅浅笑，轻轻爱，永相随！@任嘉伦Allen",
            "Comment": 237,
            "IP": "",
            "Link": " https://weibo.com/4740612161011806/Lh2vu4fds ",
            "Modal": "文本,图片",
            "Reblog": 6,
            "Time": "2022-02-25 04:11",
            "Tool": "",
            "Type": "影视",
            "account": "心念偲超",
            "language": "中文",
            "platform": "微博",
            "region": "",
            "isRisk": "false",
            "Praise": 18,
            "Pre_node": "",
            "Platform": "微博"
        }
        self.mock_data.append(sample_data)
        self.next_id += 1

    def get_event_by_id(self, event_id):
        """根据ID获取事件"""
        for event in self.mock_data:
            if event.get('_id') == event_id:
                return event
        return None

    def insert_event(self, event_data):
        """插入事件"""
        # 确保数据格式正确
        event = event_data.copy()
        if '_id' not in event:
            event['_id'] = str(self.next_id)
            self.next_id += 1
        
        # 确保必要字段存在
        required_fields = ['Event', 'Comment', 'Link', 'Modal', 'Reblog', 'Time', 'Type', 'account', 'language', 'platform', 'isRisk', 'Praise']
        for field in required_fields:
            if field not in event:
                event[field] = '' if field != 'Comment' and field != 'Reblog' and field != 'Praise' else 0
                
        # 处理isRisk字段
        if 'isRisk' in event and isinstance(event['isRisk'], str):
            event['isRisk'] = event['isRisk'].lower() == 'true'
            
        self.mock_data.append(event)
        return event.get('_id')

    def search_events(self, query=None, page=1, page_size=10, sort_by='Time', sort_order=-1):
        """搜索事件数据"""
        # 如果没有查询条件，返回所有数据
        if query is None:
            query = {}
            
        # 简单的查询实现
        results = []
        for event in self.mock_data:
            match = True
            # 检查查询条件
            for key, value in query.items():
                if key in event and event[key] != value:
                    match = False
                    break
            if match:
                results.append(event)
                
        # 排序
        if sort_by and sort_by in results[0]:
            results.sort(key=lambda x: x.get(sort_by, ''), reverse=(sort_order == -1))
            
        # 分页
        start = (page - 1) * page_size
        end = start + page_size
        paged_results = results[start:end]
        
        return paged_results, len(results)

    def execute_query(self, query, params=None):
        """执行查询"""
        # 简单的查询实现
        try:
            events, total = self.search_events(query)
            return {'data': events, 'total': total}
        except Exception as e:
            return {'error': str(e)}

    def update_event(self, event_id, update_data):
        """更新事件"""
        for event in self.mock_data:
            if event.get('_id') == event_id:
                event.update(update_data)
                return True
        return False

    def delete_event(self, event_id):
        """删除事件"""
        for i, event in enumerate(self.mock_data):
            if event.get('_id') == event_id:
                self.mock_data.pop(i)
                return True
        return False

    def get_statistics(self):
        """获取统计信息"""
        total_events = len(self.mock_data)
        risk_events = sum(1 for event in self.mock_data if event.get('isRisk', False) is True)
        platforms = list(set(event.get('platform', '') for event in self.mock_data))
        types = list(set(event.get('Type', '') for event in self.mock_data))
        
        return {
            'total_events': total_events,
            'risk_events': risk_events,
            'platforms': platforms,
            'types': types
        }