import os
import pymongo
from pymongo.errors import ConnectionFailure
from datetime import datetime
import json
from bson import ObjectId
import os
import logging

class JSONEncoder(json.JSONEncoder):
    """用于处理ObjectId和其他MongoDB特殊类型的JSON编码器"""
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return o.strftime('%Y-%m-%d %H:%M')
        return json.JSONEncoder.default(self, o)

class MongoDBService:
    def __init__(self, host=None, port=None, username=None, password=None, db_name=None, collection_name=None):
        """初始化MongoDB连接"""
        # 使用配置或环境变量
        self.host = host or os.environ.get('MONGODB_HOST', 'localhost')
        self.port = int(port or os.environ.get('MONGODB_PORT', 27017))
        self.username = username or os.environ.get('MONGODB_USERNAME', '')
        self.password = password or os.environ.get('MONGODB_PASSWORD', '')
        self.db_name = db_name or os.environ.get('MONGODB_DB', 'admin')
        self.collection_name = collection_name or os.environ.get('MONGODB_COLLECTION', 'event')
        self.client = None
        self.db = None
        self.collection = None

    def connect(self):
        """建立MongoDB连接"""
        try:
            # 创建连接字符串
            if self.username and self.password:
                connection_string = f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}/"
            else:
                connection_string = f"mongodb://{self.host}:{self.port}/"
            
            # 连接MongoDB
            self.client = pymongo.MongoClient(
                connection_string,
                serverSelectionTimeoutMS=5000
            )
            
            # 验证连接
            self.client.server_info()
            
            # 选择数据库和集合
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
            
            print(f"MongoDB连接成功: {self.host}:{self.port}/{self.db_name}/{self.collection_name}")
            return True
        except ConnectionFailure as e:
            print(f"MongoDB连接失败: {e}")
            return False
        except Exception as e:
            print(f"MongoDB连接发生错误: {e}")
            return False

    def disconnect(self):
        """关闭MongoDB连接"""
        if self.client:
            self.client.close()
            print("MongoDB连接已关闭")

    def insert_event(self, event_data):
        """插入单个事件数据"""
        if not self.collection:
            if not self.connect():
                return None
        
        try:
            # 确保数据格式正确
            event = self._prepare_event_data(event_data)
            result = self.collection.insert_one(event)
            return str(result.inserted_id)
        except Exception as e:
            print(f"插入事件数据失败: {e}")
            return None

    def insert_events(self, events_data):
        """批量插入事件数据"""
        if not self.collection:
            if not self.connect():
                return []
        
        try:
            # 确保数据格式正确
            events = [self._prepare_event_data(event) for event in events_data]
            result = self.collection.insert_many(events)
            return [str(id) for id in result.inserted_ids]
        except Exception as e:
            print(f"批量插入事件数据失败: {e}")
            return []

    def get_event_by_id(self, event_id):
        """根据ID获取事件数据"""
        if not self.collection:
            if not self.connect():
                return None
        
        try:
            # 尝试将字符串ID转换为ObjectId
            try:
                obj_id = ObjectId(event_id)
                event = self.collection.find_one({'_id': obj_id})
            except:
                # 如果转换失败，尝试直接查找
                event = self.collection.find_one({'_id': event_id})
                
            if event:
                return self._convert_objectid_to_string(event)
            return None
        except Exception as e:
            print(f"获取事件数据失败: {e}")
            return None

    def search_events(self, query=None, page=1, page_size=10, sort_by='Time', sort_order=-1):
        """搜索事件数据"""
        if self.collection is None:
            if not self.connect():
                return [], 0
        
        try:
            # 构建查询条件
            search_query = query or {}
            
            # 执行查询并分页
            skip = (page - 1) * page_size
            
            # 使用collection.count_documents()替代cursor.count()
            total_count = self.collection.count_documents(search_query)
            
            # 执行查询
            cursor = self.collection.find(search_query)
            
            # 排序
            if sort_by:
                cursor = cursor.sort(sort_by, sort_order)
            
            # 分页
            events = list(cursor.skip(skip).limit(page_size))
            
            # 转换ObjectId为字符串
            events = [self._convert_objectid_to_string(event) for event in events]
            
            return events, total_count
        except Exception as e:
            print(f"搜索事件数据失败: {e}")
            return [], 0

    def update_event(self, event_id, update_data):
        """更新事件数据"""
        if not self.collection:
            if not self.connect():
                return False
        
        try:
            # 尝试将字符串ID转换为ObjectId
            try:
                obj_id = ObjectId(event_id)
                result = self.collection.update_one({'_id': obj_id}, {'$set': update_data})
            except:
                result = self.collection.update_one({'_id': event_id}, {'$set': update_data})
                
            return result.modified_count > 0
        except Exception as e:
            print(f"更新事件数据失败: {e}")
            return False

    def delete_event(self, event_id):
        """删除事件数据"""
        if not self.collection:
            if not self.connect():
                return False
        
        try:
            # 尝试将字符串ID转换为ObjectId
            try:
                obj_id = ObjectId(event_id)
                result = self.collection.delete_one({'_id': obj_id})
            except:
                result = self.collection.delete_one({'_id': event_id})
                
            return result.deleted_count > 0
        except Exception as e:
            print(f"删除事件数据失败: {e}")
            return False

    def _prepare_event_data(self, event_data):
        """准备事件数据，确保格式正确"""
        # 创建一个副本以避免修改原始数据
        data = event_data.copy()
        
        # 处理时间字段
        if 'Time' in data and isinstance(data['Time'], str):
            try:
                # 尝试解析时间字符串
                datetime.strptime(data['Time'], '%Y-%m-%d %H:%M')
            except ValueError:
                # 如果解析失败，设置为当前时间
                data['Time'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        # 确保isRisk字段是布尔值
        if 'isRisk' in data:
            if isinstance(data['isRisk'], str):
                data['isRisk'] = data['isRisk'].lower() == 'true'
            elif not isinstance(data['isRisk'], bool):
                data['isRisk'] = bool(data['isRisk'])
        
        # 确保数值字段是数字
        numeric_fields = ['Comment', 'Reblog', 'Praise']
        for field in numeric_fields:
            if field in data:
                try:
                    data[field] = int(data[field])
                except (ValueError, TypeError):
                    data[field] = 0
        
        return data

    def _convert_objectid_to_string(self, data):
        """将数据中的ObjectId转换为字符串"""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, ObjectId):
                    data[key] = str(value)
                elif isinstance(value, dict):
                    data[key] = self._convert_objectid_to_string(value)
                elif isinstance(value, list):
                    data[key] = [self._convert_objectid_to_string(item) if isinstance(item, (dict, ObjectId)) else item for item in value]
        elif isinstance(data, ObjectId):
            return str(data)
        return data

    def export_to_json(self, file_path, query=None):
        """导出数据到JSON文件"""
        if not self.collection:
            if not self.connect():
                return False
        
        try:
            events, _ = self.search_events(query)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(events, f, ensure_ascii=False, cls=JSONEncoder, indent=2)
            return True
        except Exception as e:
            print(f"导出数据到JSON文件失败: {e}")
            return False

    def import_from_json(self, file_path):
        """从JSON文件导入数据"""
        if not self.collection:
            if not self.connect():
                return False, 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                events = json.load(f)
                
            # 确保是列表格式
            if not isinstance(events, list):
                events = [events]
                
            # 插入数据
            inserted_ids = self.insert_events(events)
            return True, len(inserted_ids)
        except Exception as e:
            print(f"从JSON文件导入数据失败: {e}")
            return False, 0

    def create_index(self, field, unique=False):
        """创建索引以提高查询性能"""
        if not self.collection:
            if not self.connect():
                return False
        
        try:
            self.collection.create_index(field, unique=unique)
            return True
        except Exception as e:
            print(f"创建索引失败: {e}")
            return False

    def get_statistics(self):
        """获取数据库统计信息"""
        if self.collection is None:
            if not self.connect():
                return {}
        
        try:
            total_events = self.collection.count_documents({})
            risk_events = self.collection.count_documents({'isRisk': "true"})
            platforms = self.collection.distinct('platform')
            types = self.collection.distinct('Type')
            
            return {
                'total_events': total_events,
                'risk_events': risk_events,
                'platforms': platforms,
                'types': types
            }
        except Exception as e:
            print(f"获取数据库统计信息失败: {e}")
            return {}
    
    def execute_query(self, query_type, params=None):
        """执行查询操作，与db_adapter.py保持兼容性"""
        if not self.collection:
            if not self.connect():
                return {'error': 'MongoDB未连接'}
        
        try:
            # 确保params不为None
            params = params or {}
            
            if query_type == 'getEventsByKeyword':
                # 根据关键词获取事件列表
                keyword = params.get('keyword', '')
                limit = params.get('limit', 10)
                offset = params.get('offset', 0)
                
                # 构建查询条件
                search_query = {}
                if keyword:
                    search_query = {
                        '$or': [
                            {'Event': {'$regex': keyword, '$options': 'i'}},
                            {'Content': {'$regex': keyword, '$options': 'i'}}
                        ]
                    }
                
                # 计算页码
                page = 1
                if offset > 0 and limit > 0:
                    page = (offset // limit) + 1
                
                # 执行查询
                events, total = self.search_events(
                    search_query, 
                    page=page, 
                    page_size=limit,
                    sort_by='Time',
                    sort_order=-1
                )
                
                return {'events': events, 'total': total}
            
            elif query_type == 'getEventDetail':
                # 获取事件详情
                event_id = params.get('event_id')
                if not event_id:
                    return {'error': '缺少事件ID'}
                
                event = self.get_event_by_id(event_id)
                return event if event else None
            
            elif query_type == 'getRelatedEvents':
                # 获取相关事件
                event_id = params.get('event_id')
                limit = params.get('limit', 5)
                
                if not event_id:
                    return {'error': '缺少事件ID'}
                
                # 首先获取当前事件
                current_event = self.get_event_by_id(event_id)
                
                if not current_event:
                    return {'events': [], 'total': 0}
                
                # 提取关键词（这里简化处理，实际应用可能需要更复杂的文本分析）
                keywords = []
                if 'Event' in current_event:
                    keywords.extend(current_event['Event'].split())
                if 'Content' in current_event:
                    keywords.extend(current_event['Content'].split())
                
                # 构建查询条件，排除当前事件
                search_query = {
                    '_id': {'$ne': current_event['_id']},
                    '$or': [
                        {'Event': {'$in': keywords}},
                        {'Content': {'$in': keywords}}
                    ]
                }
                
                # 执行查询
                events, total = self.search_events(
                    search_query,
                    page=1,
                    page_size=limit,
                    sort_by='Time',
                    sort_order=-1
                )
                
                return {'events': events, 'total': total}
            
            elif query_type == 'searchEvents':
                # 高级搜索事件
                keywords = params.get('keywords', [])
                date_range = params.get('date_range', {})
                sources = params.get('sources', [])
                categories = params.get('categories', [])
                limit = params.get('limit', 10)
                offset = params.get('offset', 0)
                
                # 计算页码
                page = 1
                if offset > 0 and limit > 0:
                    page = (offset // limit) + 1
                
                # 构建查询条件
                search_query = {}
                conditions = []
                
                # 处理关键词
                if keywords:
                    keyword_conditions = []
                    for keyword in keywords:
                        keyword_conditions.append({
                            '$or': [
                                {'Event': {'$regex': keyword, '$options': 'i'}},
                                {'Content': {'$regex': keyword, '$options': 'i'}}
                            ]
                        })
                    if len(keyword_conditions) > 1:
                        conditions.append({'$and': keyword_conditions})
                    elif keyword_conditions:
                        conditions.append(keyword_conditions[0])
                
                # 处理日期范围
                if date_range.get('start'):
                    conditions.append({'Time': {'$gte': date_range['start']}})
                if date_range.get('end'):
                    conditions.append({'Time': {'$lte': date_range['end']}})
                
                # 处理来源
                if sources:
                    conditions.append({'Source': {'$in': sources}})
                
                # 处理分类
                if categories:
                    conditions.append({'Category': {'$in': categories}})
                
                # 组合查询条件
                if len(conditions) > 1:
                    search_query = {'$and': conditions}
                elif conditions:
                    search_query = conditions[0]
                
                # 执行查询
                events, total = self.search_events(
                    search_query,
                    page=page,
                    page_size=limit,
                    sort_by='Time',
                    sort_order=-1
                )
                
                return {'events': events, 'total': total}
            
            elif query_type.startswith('custom:'):
                # 自定义查询，这里是一个示例，实际应用可能需要更复杂的处理
                custom_query = params.get('query', {})
                limit = params.get('limit', 10)
                offset = params.get('offset', 0)
                
                # 计算页码
                page = 1
                if offset > 0 and limit > 0:
                    page = (offset // limit) + 1
                
                results, total = self.search_events(
                    custom_query,
                    page=page,
                    page_size=limit
                )
                
                return {'items': results, 'total': total}
            
            else:
                # 默认查询，直接传递给search_events方法
                results, total = self.search_events(query_type)
                
                return results
        
        except Exception as e:
            logging.error(f"MongoDB查询错误: {str(e)}")
            return {'error': str(e)}