# /unified_service/routes.py

import os
import time
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from services import nebula_service, search_service
import utils

# 创建一个Blueprint
api = Blueprint('api', __name__)

# --- NebulaGraph API Routes ---

@api.route('/executeCustomQuery', methods=['POST'])
def execute_custom_query():
    query = request.json.get('query')
    if not query:
        return jsonify({"error": "缺少必要参数: query"}), 400

    space_name = current_app.config['NEBULA_SPACE']
    result = nebula_service.execute_query(query, space_name=space_name)
    
    if isinstance(result, dict) and "error" in result:
        return jsonify(result), 500
    
    return jsonify(result)

@api.route('/getRelatedByEvent', methods=['GET'])
def get_related_by_event():
    event = request.args.get('event')
    if not event:
        return jsonify({"error": "请提供事件名称"}), 400

    current_app.logger.info(f"查询事件: {event}")
    space_name = current_app.config['NEBULA_SPACE']
    result = nebula_service.get_graph_data_by_event(event, space_name)

    if isinstance(result, dict) and "error" in result:
        return jsonify(result), 500

    return jsonify({
        "event": event,
        "results": result,
        "count": len(result) if isinstance(result, list) else 0
    })
    
@api.route('/getRelatedById', methods=['GET'])
def get_related_by_id():
    id = request.args.get('id')
    if not id:
        return jsonify({"error": "请提供微博推文ID"}), 400

    current_app.logger.info(f"查询微博推文ID: {id}")
    space_name = current_app.config['NEBULA_SPACE']
    result = nebula_service.get_graph_data_by_id(id, space_name)

    if isinstance(result, dict) and "error" in result:
        return jsonify(result), 500

    return jsonify({
        "id": id,
        "results": result,
        "count": len(result) if isinstance(result, list) else 0
    })
    
@api.route('/getOriginalTweetById', methods=['GET'])
def get_Original_Tweet_by_id():
    id = request.args.get('id')
    if not id:
        return jsonify({"error": "请提供微博推文ID"}), 400

    current_app.logger.info(f"查询微博推文ID: {id}")
    space_name = current_app.config['NEBULA_SPACE']
    result = nebula_service.get_Original_Tweet_by_id(id, space_name)

    if isinstance(result, dict) and "error" in result:
        return jsonify(result), 500

    return jsonify({
        "id": id,
        "results": result,
        "count": len(result) if isinstance(result, list) else 0
    })

# --- Search API Routes ---
# 测试:curl -X POST "http://127.0.0.1:5001/api/search/text"   -H "Content-Type: application/x-www-form-urlencoded"   -d "queryContent=BGM一响，浓浓的归意再也掩饰不住了，2025年的春运已经开始了，希望每一个人都能快快乐 乐，平平安安的到家和家人团聚。&score=0.5"
# 5192635628653361
#武大男生被诬告性骚扰#现在看，武汉大学给的处分，草率了。所以说，高校处置舆情，一定要在事实的基础上，坚守原则，不要被“舆论”裹挟，而后退，更不要和稀泥。在这方面，武大应该向大连工业大学学习。

@api.route('/search/text', methods=['POST'])
def search_text_route():
    query_content = request.form.get('queryContent','减重版司美格鲁正式在中国上市')
    score = 0.3

    if not query_content:
        return jsonify({"error": "缺少 'queryContent' 参数"}), 400
    
    # try:
    #     score = float(score_str)
    # except ValueError:
    #     return jsonify({"error": "'score' 参数必须是浮点数"}), 400

    start_time = time.time()
    results = search_service.search_text(query_content, score, current_app.config)
    print(results)
    duration = time.time() - start_time
    current_app.logger.info(f"文本 '{query_content}' 搜索耗时: {duration:.2f}s")
    
    if isinstance(results, dict) and "error" in results:
        return jsonify(results), 500

    return jsonify({"search_results": results})


def _handle_file_upload(file_key, allowed_checker):
    """处理文件上传的通用逻辑"""
    if file_key not in request.files:
        return None, jsonify({"error": f"请求中缺少 '{file_key}'"}), 400

    file = request.files[file_key]
    # print(file.filename)
    if file.filename == '':
        return None, jsonify({"error": "未选择文件"}), 400
    # print(allowed_checker)
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

# 测试:curl -X POST "http://127.0.0.1:5000/api/search/picture" -F "file=@/data/storage/8888/xyt/work/milvus_dataset/Image/250116/watermark_image/Fake_raw_00_00_00_1.jpg"
@api.route('/search/picture', methods=['POST'])
def search_picture_route():
    filepath, error_response, status_code = _handle_file_upload('file', utils.is_picture_file_allowed)
    if error_response:
        return error_response, status_code
        
    # try:
    #     top_k = int(top_k_str)
    # except ValueError:
    #     return jsonify({"error": "'topk' 参数必须是整数"}), 400

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
    # print(results_event)

    # return jsonify({"message": "图片上传成功", "image_base64_list": image_base64_list, "search_results": results_event})
    # 展平列表
    results_event = [item for sublist in results_event for item in sublist]
    return jsonify({"search_results": results_event})

# 测试:curl -X POST "http://127.0.0.1:5001/api/search/video" -F "file=@/data/storage/8888/xyt/work/milvus_dataset/video/raw_video/douyin_raw_1.mp4" -F "topk=5"
@api.route('/search/video', methods=['POST'])
def search_video_route():
    filepath, error_response, status_code = _handle_file_upload('file', utils.is_video_file_allowed)
    if error_response:
        return error_response, status_code
        
    score = 1
    print(score)
    # try:
    #     top_k = int(top_k_str)
    # except ValueError:
    #     return jsonify({"error": "'topk' 参数必须是整数"}), 400
        
    results = search_service.search_video(filepath, score, current_app.config)

    if isinstance(results, dict) and "error" in results:
        return jsonify(results), 500

    video_base64_list = []
    if results and isinstance(results, list):
        for video_path in results:
             # 假设 search_service 返回的路径是可以直接访问的完整路径
            print(video_path)
            video_base64 = utils.to_base64(video_path)
            if video_base64:
                video_type = "video/mp4"
                data_url = f"data:{video_type};base64,{video_base64}"
                video_base64_list.append(data_url)

    return jsonify({"message": "视频上传成功", "video_base64_list": video_base64_list})

# --- General File Upload API ---
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