# /unified_service/routes.py

import os
import time
import json
import datetime
import calendar
from flask import Blueprint, request, jsonify, current_app, g, make_response
from werkzeug.utils import secure_filename
from services import search_service
import utils

# 导入查询优化器
import logging
try:
    from optimize_query_without_index import (
        optimize_get_all_events_params,
        build_optimized_get_all_events_query,
        get_query_suggestions
    )
    QUERY_OPTIMIZER_AVAILABLE = True
except ImportError as e:
    logging.warning(f"无法导入查询优化器: {e}")
    QUERY_OPTIMIZER_AVAILABLE = False

# 添加isRisk字段索引创建提示
def suggest_index_creation():
    """生成索引创建建议"""
    return {
        "建议": "为了获得最佳性能，建议创建以下索引",
        "推荐索引": [
            "isRisk字段索引 - 优化风险事件过滤",
            "platform字段索引 - 优化平台筛选（已创建）",
            "Event字段索引 - 优化事件名称搜索（已创建）",
            "Time字段索引 - 优化排序和时间范围查询（已创建）"
        ],
        "创建方法": "运行 python create_indexes.py 或 python create_optimized_indexes.py"
    }

# 创建一个Blueprint
api = Blueprint('api', __name__)

# --- 数据库相关 API Routes --- (适配MongoDB和原有数据库)

# 获取指定的数据库服务，如果未指定则使用默认服务
def get_db_service(db_type=None):
    """获取指定的数据库服务，如果未指定则使用默认服务"""
    if hasattr(g.db, 'get_service'):
        return g.db.get_service(db_type)
    # 兼容旧版本的数据库适配器
    return g.db

# 标准化平台名称
def standardize_platform(platform):
    """标准化平台名称，特别是对微博数据进行统一处理"""
    if not platform or not isinstance(platform, str):
        return platform
    
    # 去除空格和特殊字符
    platform = platform.strip()
    
    # 统一微博平台名称
    if '微博' in platform:
        return '微博'
    
    return platform

# 预处理事件数据，确保数据格式符合前端期望
def preprocess_events(events):
    """预处理事件数据，确保数据格式符合前端期望"""
    import math
    processed_events = []
    for event in events:
        # 转换isRisk字段从字符串到布尔值
        if 'isRisk' in event and isinstance(event['isRisk'], str):
            event['isRisk'] = event['isRisk'].lower() == 'true'
        
        # 确保所有必需字段都存在
        required_fields = ['Event', 'account', 'Time', 'platform', '_id']
        for field in required_fields:
            if field not in event:
                event[field] = ''  # 提供默认值
        
        # 确保platform字段的一致性，使用标准化函数
        if 'platform' in event:
            event['platform'] = standardize_platform(event['platform'])
        
        # 处理NaN值，将其替换为合适的默认值
        for key, value in event.items():
            # 检查是否是NaN值
            if isinstance(value, float) and math.isnan(value):
                # 根据字段类型设置合适的默认值
                if key in ['Praise', 'Reblog', 'Comment']:
                    event[key] = 0  # 数值字段设置为0
                else:
                    event[key] = ''  # 其他字段设置为空字符串
        
        processed_events.append(event)
    return processed_events

@api.route('/executeCustomQuery', methods=['POST'])
def execute_custom_query():
    query = request.json.get('query')
    db_type = request.json.get('db_type')  # 可选，指定使用哪个数据库
    if not query:
        return jsonify({"error": "缺少必要参数: query"}), 400

    # 获取数据库服务
    db_service = get_db_service(db_type)
    
    # 使用数据库适配器执行查询
    result = db_service.execute_query(query)
    
    if isinstance(result, dict) and "error" in result:
        return jsonify(result), 500
    
    return jsonify(result)

@api.route('/getRelatedByEvent', methods=['GET'])
@api.route('/getEventsByKeyword', methods=['GET'])
def get_events_by_keyword():
    event = request.args.get('event') or request.args.get('keyword')
    db_type = request.args.get('db_type')  # 可选，指定使用哪个数据库
    if not event:
        return jsonify({"error": "请提供事件名称或关键词"}), 400

    current_app.logger.info(f"查询事件: {event}")
    
    # 构建查询条件，在Event字段中搜索关键词
    query = {"Event": {"$regex": event, "$options": "i"}}  # 不区分大小写的正则表达式搜索
    
    # 获取数据库服务
    db_service = get_db_service(db_type)
    
    # 使用数据库适配器搜索事件
    results, total = db_service.search_events(query)

    if isinstance(results, dict) and "error" in results:
        return jsonify(results), 500

    return jsonify({
        "event": event,
        "results": results,
        "count": total
    })
    
@api.route('/getRelatedById', methods=['GET'])
@api.route('/getOriginalTweetById', methods=['GET'])
def get_event_by_id():
    event_id = request.args.get('id')
    db_type = request.args.get('db_type')  # 可选，指定使用哪个数据库
    if not event_id:
        return jsonify({"error": "请提供事件ID"}), 400

    current_app.logger.info(f"查询事件ID: {event_id}")
    
    # 获取数据库服务
    db_service = get_db_service(db_type)
    
    # 使用数据库适配器根据ID获取事件
    result = db_service.get_event_by_id(event_id)

    if isinstance(result, dict) and "error" in result:
        return jsonify(result), 500
    elif result is None:
        return jsonify({"error": "未找到该事件"}), 404

    return jsonify({
        "id": event_id,
        "results": result,
        "count": 1 if result else 0
    })

# 添加新的API路由来支持更多MongoDB功能
@api.route('/getAllEvents', methods=['GET'])
def get_all_events():
    """获取所有事件，支持分页、排序和按平台、region、Time和关键字过滤"""
    print("收到getAllEvents请求")
    print(f"请求参数: {request.args}")
    try:
        # 准备原始参数
        params = {
            'page': request.args.get('page', 1),
            'page_size': request.args.get('page_size', 10),
            'sort_by': request.args.get('sort_by', 'Time'),
            'sort_order': request.args.get('sort_order', -1),
            'platform': request.args.get('platform', ''),
            'region': request.args.get('region', ''),
            'start_time': request.args.get('start_time', ''),
            'end_time': request.args.get('end_time', ''),
            'keyword': request.args.get('keyword', ''),
            'db_type': request.args.get('db_type')  # 可选，指定使用哪个数据库
        }
        
        # 解析数据库类型，使用get方法避免KeyError
        db_type = params.get('db_type')
        
        # 使用查询优化器优化参数和构建查询条件
        if QUERY_OPTIMIZER_AVAILABLE:
            print("使用查询优化器优化查询...")
            # 优化参数
            optimized_params = optimize_get_all_events_params(params)
            
            # 构建优化的查询条件
            query = build_optimized_get_all_events_query(optimized_params)
            
            # 提取优化后的参数
            page = optimized_params['page']
            page_size = optimized_params['page_size']
            sort_by = optimized_params['sort_by']
            sort_order = optimized_params['sort_order']
        else:
            # 回退到原始的参数解析逻辑
            print("查询优化器不可用，使用原始查询逻辑...")
            try:
                page = int(params.get('page', 1))
                page_size = int(params.get('page_size', 10))
                sort_by = params.get('sort_by', 'Time')
                sort_order = int(params.get('sort_order', -1))
            except ValueError:
                return jsonify({"error": "分页和排序参数格式错误"}), 400
            
            # 构建查询条件
            query = {}
            conditions = []
            
            # 如果提供了平台参数，标准化后添加到查询条件中
            if params.get('platform'):
                standardized_platform = standardize_platform(params['platform'])
                # 使用$regex进行模糊匹配，因为数据库中可能有不同格式的平台名称
                conditions.append({"platform": {"$regex": standardized_platform, "$options": "i"}})
            
            # 如果提供了region参数，添加到查询条件中
            if params.get('region'):
                conditions.append({"region": params['region']})
            
            # 处理时间范围查询，支持按年月筛选 (格式：YYYY-MM)
            if params.get('start_time'):
                if len(params['start_time']) == 7 and params['start_time'][4] == '-':  # 检查是否是年月格式 (YYYY-MM)
                    # 年月格式，设置为当月第一天
                    conditions.append({"Time": {"$gte": f"{params['start_time']}-01 00:00"}})
                else:
                    conditions.append({"Time": {"$gte": params['start_time']}})
            if params.get('end_time'):
                if len(params['end_time']) == 7 and params['end_time'][4] == '-':  # 检查是否是年月格式 (YYYY-MM)
                    # 年月格式，设置为当月最后一天
                    # 解析年月
                    year, month = map(int, params['end_time'].split('-'))
                    # 计算当月最后一天
                    if month == 12:
                        last_day = 31
                    else:
                        last_day = (datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)).day
                    conditions.append({"Time": {"$lte": f"{params['end_time']}-{last_day} 23:59"}})
                else:
                    conditions.append({"Time": {"$lte": params['end_time']}})
            
            # 如果提供了关键词参数，添加到查询条件中
            if params.get('keyword'):
                # 记录关键词搜索日志
                current_app.logger.info(f"进行关键词搜索: {params['keyword']}")
                
                # 在没有索引的情况下，减少搜索范围以提高性能
                if len(params['keyword']) <= 2:
                    # 关键词较短，只搜索Event字段以提高性能
                    print("关键词较短，只搜索Event字段以提高性能")
                    conditions.append({"Event": {"$regex": params['keyword'], "$options": "i"}})
                else:
                    # 完整搜索，但添加注释说明性能影响
                    conditions.append({
                        "$or": [
                            {"Event": {"$regex": params['keyword'], "$options": "i"}},
                            {"Content": {"$regex": params['keyword'], "$options": "i"}}
                        ]
                    })
            
            # 组合查询条件
            if len(conditions) > 0:
                if len(conditions) > 1:
                    query = {"$and": conditions}
                else:
                    query = conditions[0]
        
        # 获取数据库服务
        db_service = get_db_service(db_type)
        
        # 记录查询条件和数据库类型
        print(f"执行查询 - 数据库类型: {db_type}, 查询条件: {query}")
        
        events, total = db_service.search_events(query, page, page_size, sort_by, sort_order)
        
        # 记录查询结果
        print(f"查询结果 - 找到{total}条记录，返回{len(events)}条记录")
        
        if isinstance(events, dict) and "error" in events:
            return jsonify(events), 500
        
        # 预处理事件数据
        events = preprocess_events(events)
        
        return jsonify({
            "results": events,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size
        })
    except Exception as e:
        current_app.logger.error(f"获取事件列表时出错: {str(e)}")
        return jsonify({"error": f"获取事件列表时出错: {str(e)}"}), 500

@api.route('/getRiskEvents', methods=['GET'])
def get_risk_events():
    """获取所有isRisk=true的风险事件，支持分页、排序和按region、Time和关键字过滤"""
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 10))
        sort_by = request.args.get('sort_by', 'Time')
        sort_order = int(request.args.get('sort_order', -1))
        region = request.args.get('region', '')
        start_time = request.args.get('start_time', '')
        end_time = request.args.get('end_time', '')
        keyword = request.args.get('keyword', '')
        db_type = request.args.get('db_type')  # 可选，指定使用哪个数据库
    except ValueError:
        return jsonify({"error": "分页和排序参数格式错误"}), 400
    
    # 记录详细的查询参数日志
    current_app.logger.info(f"getRiskEvents请求参数: page={page}, page_size={page_size}, sort_by={sort_by}, sort_order={sort_order}, region={region}, start_time={start_time}, end_time={end_time}, keyword={keyword}, db_type={db_type}")
    
    # 构建查询条件，只获取isRisk=true的事件（true是以字符串形式存储）
    query = {"isRisk": "true"}
    conditions = [{"isRisk": "true"}]
    
    # 如果提供了platform参数，添加到查询条件中
    platform = request.args.get('platform', '')
    if platform:
        conditions.append({"platform": platform})
    
    # 如果提供了region参数，添加到查询条件中
    if region:
        conditions.append({"region": region})
    
    # 处理时间范围查询，支持按年月筛选 (格式：YYYY-MM)
    # 建议添加时间范围限制以提高性能
    if start_time:
        if len(start_time) == 7 and start_time[4] == '-':  # 检查是否是年月格式 (YYYY-MM)
            # 年月格式，设置为当月第一天
            conditions.append({"Time": {"$gte": f"{start_time}-01 00:00"}})
        else:
            conditions.append({"Time": {"$gte": start_time}})
    if end_time:
        if len(end_time) == 7 and end_time[4] == '-':  # 检查是否是年月格式 (YYYY-MM)
            # 年月格式，设置为当月最后一天
            # 解析年月
            year, month = map(int, end_time.split('-'))
            # 计算当月最后一天
            if month == 12:
                last_day = 31
            else:
                last_day = (datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)).day
            conditions.append({"Time": {"$lte": f"{end_time}-{last_day} 23:59"}})
        else:
            conditions.append({"Time": {"$lte": end_time}})
    
    # 如果提供了关键词参数，添加到查询条件中（不区分大小写）
    if keyword:
        # 基于性能测试结果的优化：
        # 1. 对于Content字段的查询结果为0，说明Content字段可能为空或不存在
        # 2. 只在Event字段上进行搜索可显著提升性能
        print(f"关键词搜索优化：只在Event字段搜索 '{keyword}'，跳过Content字段")
        conditions.append({"Event": {"$regex": keyword, "$options": "i"}})
    
    # 组合查询条件
    if len(conditions) > 1:
        query = {"$and": conditions}
    
    # 记录查询条件日志
    current_app.logger.info(f"getRiskEvents查询条件: {query}")
    
    # 获取数据库服务
    db_service = get_db_service(db_type)
    
    events, total = db_service.search_events(query, page, page_size, sort_by, sort_order)
    
    # 记录查询结果日志
    current_app.logger.info(f"getRiskEvents查询结果: 找到{total}条记录，返回{len(events) if events else 0}条记录")
    
    if isinstance(events, dict) and "error" in events:
        return jsonify(events), 500
    
    # 预处理事件数据
    events = preprocess_events(events)
    
    return jsonify({
        "results": events,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size
    })

@api.route('/getDatabaseStats', methods=['GET'])
def get_database_stats():
    """获取数据库统计信息"""
    db_type = request.args.get('db_type')  # 可选，指定使用哪个数据库
    
    # 获取数据库服务
    db_service = get_db_service(db_type)
    
    stats = db_service.get_statistics()
    
    if isinstance(stats, dict) and "error" in stats:
        return jsonify(stats), 500
    
    return jsonify(stats)

@api.route('/exportEvents', methods=['GET'])
def export_events():
    """导出事件数据，支持按条件筛选"""
    try:
        # 获取查询参数
        keyword = request.args.get('keyword', '')
        region = request.args.get('region', '')
        start_time = request.args.get('start_time', '')
        end_time = request.args.get('end_time', '')
        is_risk = request.args.get('is_risk', '')
        platform = request.args.get('platform', '')
        db_type = request.args.get('db_type')  # 可选，指定使用哪个数据库
        export_format = request.args.get('format', 'json')  # 导出格式：json 或 jsonl
        
        # 构建查询条件
        query = {}
        conditions = []
        
        if keyword:
            conditions.append({
                "$or": [
                    {"Event": {"$regex": keyword, "$options": "i"}},
                    {"Content": {"$regex": keyword, "$options": "i"}}
                ]
            })
        
        if region:
            conditions.append({"region": region})
        
        # 处理时间范围查询，支持按年月筛选 (格式：YYYY-MM)
        if start_time:
            if len(start_time) == 7 and start_time[4] == '-':  # 检查是否是年月格式 (YYYY-MM)
                # 年月格式，设置为当月第一天
                conditions.append({"Time": {"$gte": f"{start_time}-01 00:00"}})
            else:
                conditions.append({"Time": {"$gte": start_time}})
        
        if end_time:
            if len(end_time) == 7 and end_time[4] == '-':  # 检查是否是年月格式 (YYYY-MM)
                # 年月格式，设置为当月最后一天
                year, month = map(int, end_time.split('-'))
                last_day = calendar.monthrange(year, month)[1]
                conditions.append({"Time": {"$lte": f"{year}-{month:02d}-{last_day} 23:59"}})
            else:
                conditions.append({"Time": {"$lte": end_time}})
        
        if is_risk:
            conditions.append({"isRisk": is_risk})
        
        if platform:
            conditions.append({"platform": platform})
        
        # 组合查询条件
        if len(conditions) > 0:
            if len(conditions) > 1:
                query = {"$and": conditions}
            else:
                query = conditions[0]
        
        # 获取数据库服务
        db_service = get_db_service(db_type)
        
        # 导出所有匹配的事件（不分页）
        events, total = db_service.search_events(query, page=1, page_size=100000)
        
        if isinstance(events, dict) and "error" in events:
            return jsonify(events), 500
        
        # 根据导出格式返回不同的响应
        if export_format.lower() == 'jsonl':
            # 生成JSONL格式的响应
            jsonl_content = ''
            for event in events:
                # 确保event是可JSON序列化的
                if isinstance(event, dict):
                    jsonl_content += json.dumps(event, ensure_ascii=False) + '\n'
                else:
                    # 如果event不是dict，尝试转换
                    try:
                        jsonl_content += json.dumps(dict(event), ensure_ascii=False) + '\n'
                    except:
                        # 忽略无法序列化的条目
                        continue
            
            # 创建响应对象，设置适当的头部
            response = make_response(jsonl_content)
            response.headers['Content-Type'] = 'application/jsonl'
            response.headers['Content-Disposition'] = 'attachment; filename="events_export.jsonl"'
            response.headers['X-Total-Records'] = str(total)
            return response
        else:
            # 默认返回JSON格式
            return jsonify({
                "results": events,
                "total": total,
                "export_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        
    except Exception as e:
        current_app.logger.error(f"Export events error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# --- 搜索相关 API Routes --- (保持不变)
@api.route('/search/text', methods=['POST'])
def search_text_route():
    query_content = request.form.get('queryContent','减重版司美格鲁正式在中国上市')
    score = float(request.form.get('threshold', 0.3))

    if not query_content:
        return jsonify({"error": "缺少 'queryContent' 参数"}), 400
    
    start_time = time.time()
    results = search_service.search_text(query_content, score, current_app.config)
    
    duration = time.time() - start_time
    current_app.logger.info(f"文本 '{query_content}' 搜索耗时: {duration:.2f}s")
    
    if isinstance(results, dict) and "error" in results:
        return jsonify(results), 500

    return jsonify({
        "search_results": results
    })

# --- 文件上传和处理相关路由 --- (保持不变)
def _handle_file_upload(file_key, allowed_checker):
    """处理文件上传的通用逻辑"""
    if file_key not in request.files:
        return None, jsonify({"error": f"请求中缺少 '{file_key}'"}), 400

    file = request.files[file_key]
    if file.filename == '':
        return None, jsonify({"error": "未选择文件"}), 400
    
    if file and allowed_checker(file.filename):
        filename = secure_filename(file.filename)
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        current_app.logger.info(f"文件已保存至: {filepath}")
        return filepath, None, None
    else:
        return None, jsonify({"error": "文件类型不允许"}), 400

@api.route('/search/picture', methods=['POST'])
def search_picture_route():
    filepath, error_response, status_code = _handle_file_upload('file', utils.is_picture_file_allowed)
    if error_response:
        return error_response, status_code

    results_path,results_mid = search_service.search_picture(filepath, current_app.config)
    
    if isinstance(results_path, dict) and "error" in results_path:
        return jsonify(results_path), 500
    
    # 将找到的图片路径转换为base64返回
    image_base64_list = []
    # results_path 的结构是 [[path1, path2], ...]
    if results_path and isinstance(results_path[0], list):
        for image_path in results_path[0]: 
            # 注意：这里的路径应该是可访问的绝对路径或相对路径
            # 假设 search_service 返回的路径是需要拼接的
            # full_image_path = os.path.join("/path/to/image/dataset", image_path) 
            # 此处暂时假设返回的是可以直接访问的完整路径
            image_base64 = utils.to_base64(image_path)
            if image_base64:
                image_type = "image/" + image_path.split('.')[-1]
                data_url = f"data:{image_type};base64,{image_base64}"
                image_base64_list.append(data_url)
        
    results_event = []
    if results_mid and isinstance(results_mid[0], list):
        for mid in results_mid[0]: 
            #去es找事件
            event = search_service.search_event_by_mid(mid, current_app.config)
            results_event.append(event)
    
    # 展平列表
    results_event = [item for sublist in results_event for item in sublist]
    
    return jsonify({
        "search_results": results_event,
        "image_base64_list": image_base64_list
    })

@api.route('/search/video', methods=['POST'])
def search_video_route():
    filepath, error_response, status_code = _handle_file_upload('file', utils.is_video_file_allowed)
    if error_response:
        return error_response, status_code
        
    score = float(request.form.get('score', 1))
    
    results = search_service.search_video(filepath, score, current_app.config)

    if isinstance(results, dict) and "error" in results:
        return jsonify(results), 500

    # 处理视频搜索结果格式
    # 假设返回结果是 [[path1, path2], ...]，我们需要将其展平
    flat_results = []
    if results and isinstance(results, list):
        for sublist in results:
            if isinstance(sublist, list):
                flat_results.extend(sublist)
            else:
                flat_results.append(sublist)
    
    # 生成视频base64列表
    video_base64_list = []
    for video_path in flat_results:
        video_base64 = utils.to_base64(video_path)
        if video_base64:
            video_type = "video/mp4"
            data_url = f"data:{video_type};base64,{video_base64}"
            video_base64_list.append(data_url)

    return jsonify({
        "message": "视频上传成功",
        "search_results": flat_results,
        "video_base64_list": video_base64_list
    })

@api.route('/upload', methods=['POST'])
def upload_file():
    """
    通用文件上传接口，用于前端上传图片或视频
    返回文件的访问 URL
    """
    # 支持图片和视频
    def allow_uploaded_file(filename):
        return (utils.is_picture_file_allowed(filename) or 
                utils.is_video_file_allowed(filename))

    filepath, error_response, status_code = _handle_file_upload('file', allow_uploaded_file)
    if error_response:
        return error_response, status_code

    filename = os.path.basename(filepath)
    file_url = f"/uploads/{filename}"  # 前端可通过此 URL 访问文件

    return jsonify({
        "message": "上传成功",
        "filename": filename,
        "url": file_url
    }), 200

@api.route('/getQuerySuggestions', methods=['GET'])
def get_query_suggestions_route():
    """获取查询优化建议，包括索引创建建议"""
    try:
        # 如果查询优化器可用，使用它来获取建议
        if QUERY_OPTIMIZER_AVAILABLE:
            suggestions = get_query_suggestions()
            return jsonify({
                "success": True,
                "suggestions": suggestions
            })
        else:
            # 回退建议
            return jsonify({
                "success": True,
                "suggestions": {
                    "建议": "强烈建议创建索引以获得最佳性能，特别是对于大型数据集",
                    "推荐索引": [
                        "Event字段索引 - 优化事件名称搜索",
                        "Time字段索引 - 优化排序和时间范围查询",
                        "platform字段索引 - 优化平台筛选",
                        "region字段索引 - 优化地区筛选"
                    ],
                    "其他优化建议": [
                        "限制每页返回的结果数量",
                        "添加时间范围限制以减少扫描的数据量",
                        "对于短关键词，只搜索Event字段而不是所有字段"
                    ]
                }
            })
    except Exception as e:
        current_app.logger.error(f"获取查询建议错误: {str(e)}")
        return jsonify({"error": str(e)}), 500

@api.route('/getDashboardMetrics', methods=['GET'])
def get_dashboard_metrics():
    """
    获取仪表盘指标数据
    """
    try:
        db_type = request.args.get('db_type')  # 可选，指定使用哪个数据库
        
        # 获取数据库服务
        db_service = get_db_service(db_type)
        
        if not db_service or not hasattr(db_service, 'collection'):
            return jsonify({"error": "数据库服务不可用"}), 500
        
        db = db_service.db
        collection = db_service.collection
        
        # 构建返回结果
        metrics = {}
        
        # 1. 实时查询结果数量
        real_count = collection.count_documents({})
        metrics['count1'] = real_count
        
        # 2. 风险事件数量
        risk_count = collection.count_documents({"isRisk": "true"})
        metrics['risk_count'] = risk_count
        
        # 3. 平台的所有唯一值和每种平台的数量
        unique_platforms = collection.distinct("platform")
        metrics['platforms'] = unique_platforms
        metrics['platform_count'] = len(unique_platforms)
        
        # 计算每种平台的数量
        platform_counts = {}
        for platform in unique_platforms:
            if platform:
                platform_counts[platform] = collection.count_documents({"platform": platform})
        metrics['platform_counts'] = platform_counts
        
        # 4. 字段列表和总数
        sample_doc = collection.find_one({}, {"_id": 0})  # 排除_id字段
        if sample_doc:
            field_names = list(sample_doc.keys())
            field_count = len(field_names)
            metrics['fields'] = field_names
            metrics['field_count'] = field_count
        
        # 5. 互动总量 (Praise + Reblog + Comment)
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "total_praise": {"$sum": "$Praise"},
                    "total_reblog": {"$sum": "$Reblog"},
                    "total_comment": {"$sum": "$Comment"},
                    "total_interactions": {
                        "$sum": {"$add": ["$Praise", "$Reblog", "$Comment"]}
                    }
                }
            }
        ]
        
        result = list(collection.aggregate(pipeline))
        if result:
            stats = result[0]
            metrics['total_nums'] = stats["total_interactions"]
            metrics['total_praise'] = stats["total_praise"]
            metrics['total_reblog'] = stats["total_reblog"]
            metrics['total_comment'] = stats["total_comment"]
        
        # 6. 语言的所有唯一值和每种语言的数量
        unique_languages = collection.distinct("language")
        metrics['languages'] = unique_languages
        metrics['language_count'] = len(unique_languages)
        
        # 计算每种语言的数量
        language_counts = {}
        for language in unique_languages:
            if language:
                language_counts[language] = collection.count_documents({"language": language})
        metrics['language_counts'] = language_counts
        
        # 添加当前数据库集合信息
        metrics['collections'] = db.list_collection_names()
        
        return jsonify(metrics)
        
    except Exception as e:
        current_app.logger.error(f"获取仪表盘指标错误: {str(e)}")
        return jsonify({"error": str(e)}), 500