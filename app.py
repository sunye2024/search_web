from flask import Flask, request, jsonify
from nebula3.gclient.net import ConnectionPool
from nebula3.Config import Config
import logging
from flask_cors import CORS
from datetime import datetime
import sys

app = Flask(__name__)
CORS(app)  # 允许所有域名跨域访问

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]   # 强制写到 stdout，避免 Windows cmd 编码问题
)
logger = logging.getLogger(__name__)

# NebulaGraph配置
config = Config()
config.max_connection_pool_size = 10
connection_pool = ConnectionPool()

# 初始化连接池
if not connection_pool.init([('172.18.112.199', 9669)], config):
    logger.error('连接NebulaGraph失败')
    exit(1)

# 更新属性类型映射，包含新增的结构属性
PROPERTY_TYPES = {
    # Event属性
    'eventstr': 'string',
    
    # Article属性
    'title': 'string',
    'content': 'string',
    'publishtimestamp': 'timestamp',
    'event': 'string',
    'uid': 'string',
    'pics_id': 'string',
    'pics_url': 'string',
    'isrumor': 'bool',
    'rumor_c': 'string',
    'datasource': 'string',
    'eid': 'string',
    
    # Original_Tweet属性
    'forwardcount': 'int',
    
    # Retweet属性
    'reuid': 'string',
    'retext': 'string',
    'republishtime': 'timestamp',
    'rootmid': 'string',
    'parentmid': 'string',
    'name': 'string'
}

# 辅助函数：处理NebulaGraph返回的值
# -*- coding: utf-8 -*-
import ast      # 新增：用于安全地把 \xhh 转义还原成 bytes
import re

def process_value(value, prop_type):
    """彻底还原 UTF-8 字节 -> unicode"""
    if value is None:
        return None

    # 1. 把 Nebula Value 对象转成字符串（含转义）
    raw = str(value)

    # 2. 如果字符串是 b'...' 形式，把它还原成真正的 bytes
    #    例：b'\\xe6\\x80\\xbb' -> b'\xe6\x80\xbb'
    m = re.search(r"b'([^']*)'", raw)
    if m:
        try:
            # ast.literal_eval 会把 \\xhh 还原成对应字节
            raw = ast.literal_eval("b'{}'".format(m.group(1)))
        except Exception:
            pass

    # 3. 现在 raw 可能是 bytes，也可能是普通字符串
    if isinstance(raw, bytes):
        try:
            raw = raw.decode('utf-8')
        except UnicodeDecodeError:
            raw = raw.decode('gb18030', 'ignore')

    # 4. 最后按业务类型转换
    try:
        if prop_type == 'timestamp':
            return datetime.fromtimestamp(int(raw) / 1000).strftime('%Y-%m-%d %H:%M:%S')
        elif prop_type == 'bool':
            return bool(int(raw))
        elif prop_type == 'int':
            return int(raw)
        elif prop_type == 'float':
            return float(raw)
        else:
            return raw
    except Exception:
        return raw
# 辅助函数：执行NebulaGraph查询
def execute_query(query, params=None):
    """执行NebulaGraph查询并返回处理后的结果"""
    try:
        with connection_pool.session_context('root', 'p') as session:
            session.execute('USE Social_Network_1')
            
            # 执行查询 - 兼容旧版本和新版本的NebulaGraph客户端
            if params:
                # 检查是否有execute_parameterized方法
                if hasattr(session, 'execute_parameterized'):
                    result = session.execute_parameterized(query, params)
                else:
                    # 构建带参数的查询字符串
                    formatted_query = query
                    for key, value in params.items():
                        if isinstance(value, str):
                            formatted_query = formatted_query.replace(f"${key}", f"'{value}'")
                        else:
                            formatted_query = formatted_query.replace(f"${key}", str(value))
                    result = session.execute(formatted_query)
            else:
                result = session.execute(query)
            
            # 检查执行是否成功
            if not result.is_succeeded():
                error_msg = result.error_msg()
                logger.error(f"查询执行失败: {error_msg}, 查询: {query}")
                return {"error": error_msg, "query": query}
            
            # 处理结果集
            rows = []
            if result.is_empty():
                return rows
                
            # 获取列名
            col_names = result.keys()
            
            # 处理每一行数据
            for row in result.rows():
                row_data = {}
                for i, col_name in enumerate(col_names):
                    # 提取属性名称（处理不同格式的列名）
                    parts = col_name.split('.')
                    if len(parts) >= 2:
                        prop_name = parts[-1]  # 取最后一部分作为属性名
                    else:
                        prop_name = col_name
                    
                    # 获取属性类型，默认为string
                    prop_type = PROPERTY_TYPES.get(prop_name, 'string')
                    
                    # 处理单元格值
                    value = row.values[i]
                    processed_value = process_value(value, prop_type)
                    row_data[prop_name] = processed_value
                
                rows.append(row_data)
            
            return rows
    
    except Exception as e:
        logger.error(f"执行查询时发生异常: {str(e)}, 查询: {query}")
        return {"error": str(e), "query": query}

# 执行自定义CQL查询
@app.route('/api/executeCustomQuery', methods=['POST'])
def execute_custom_query():
    query = request.json.get('query')
    if not query:
        return jsonify({"error": "缺少必要参数: query"}), 400

    result = execute_query(query)
    if "error" in result:
        return jsonify(result), 500

    return jsonify(result)

# 重建索引部分保持不变
with connection_pool.session_context('root', 'p') as session:
    session.execute('USE Social_Network_1')
    rebuild_index_query = "REBUILD TAG INDEX Article_event"
    rebuild_result = session.execute(rebuild_index_query)
    if not rebuild_result.is_succeeded():
        logger.error(f"重建索引失败: {rebuild_result.error_msg()}")
    else:
        logger.info("索引重建成功")

# 根据事件VID查询相关节点和边（包含新的查询语句）
@app.route('/api/getRelatedByEventVid', methods=['GET'])
def get_related_by_event_vid():
    event_vid = request.args.get('event_vid', '')
    logger.info(u'查询事件VID: {}'.format(event_vid))  # 日志也使用 unicode 字符串
    if not event_vid:
        return jsonify({"error": u"请提供事件VID"}), 400

    query = u"""
    GO FROM $event_vid OVER belong REVERSELY 
    YIELD src(edge)      AS vid, 
           dst(edge)      AS end_vid, 
           $$             AS src_v, 
           edge           AS e, 
           rank(edge)     AS e_rank, 
           type(edge)     AS e_type, 
           src(edge)      AS e_src,  
           dst(edge)      AS e_dst 
    UNION ALL
    GO FROM $event_vid
    OVER belong REVERSELY
    YIELD src(edge) AS vid
    | GO 1 TO 5 STEPS FROM $-.vid
      OVER forwarded REVERSELY
    YIELD
      src(edge)      AS vid,
      dst(edge)      AS end_vid,
      $$             AS src_v, 
      edge           AS e,     
      rank(edge)     AS e_rank, 
      type(edge)     AS e_type, 
      src(edge)      AS e_src,  
      dst(edge)      AS e_dst 
    """
    params = {"event_vid": event_vid}
    result = execute_query(query, params)

    # 关键：ensure_ascii=False 让 JSON 直接返回 UTF-8 中文
    return jsonify({
        "event_vid": event_vid,
        "results": result,
        "count": len(result)
    }), 200, {'Content-Type': 'application/json; charset=utf-8'}



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)