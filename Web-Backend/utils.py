# /unified_service/utils.py

import base64
from flask import current_app

def to_base64(file_path):
    """将文件转换为Base64编码的字符串"""
    try:
        with open(file_path, "rb") as file:
            return base64.b64encode(file.read()).decode("utf-8")
    except FileNotFoundError:
        current_app.logger.warning(f"文件未找到: {file_path}")
        return None

def is_video_file_allowed(filename):
    """检查视频文件扩展名是否合法"""
    # return filename.rsplit('.', 1)[1].lower()
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['VIDEO_ALLOWED_EXTENSIONS']

def is_picture_file_allowed(filename):
    """检查图片文件扩展名是否合法"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['PICTURE_ALLOWED_EXTENSIONS']