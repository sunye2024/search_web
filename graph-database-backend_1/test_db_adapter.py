#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试数据库适配器和MongoDB服务的功能
"""
import os
import json
from db_adapter import DatabaseAdapter

# 设置环境变量，使用MongoDB或Mock数据库
# 如果要测试Mock数据库，可以设置 DB_TYPE=mock
os.environ.setdefault('DB_TYPE', 'mongodb')

# 创建数据库适配器实例
db = DatabaseAdapter()

print("=== 数据库适配器测试开始 ===")

# 检查数据库适配器状态
if db.error_messages:
    for db_type, error in db.error_messages.items():
        print(f"警告 ({db_type}): {error}")
else:
    print("数据库适配器初始化成功!")

# 获取数据库统计信息
print("\n1. 获取数据库统计信息:")
stats = db.get_statistics()
print(json.dumps(stats, ensure_ascii=False, indent=2))

# 搜索事件
print("\n2. 搜索所有事件:")
events, total = db.search_events()
print(f"找到 {total} 个事件")
if events:
    print("第一个事件:")
    print(json.dumps(events[0], ensure_ascii=False, indent=2))

# 如果有事件，获取第一个事件的ID并测试按ID查询
if events:
    event_id = events[0].get('_id')
    print(f"\n3. 按ID查询事件 (ID: {event_id}):")
    event = db.get_event_by_id(event_id)
    if event:
        print(json.dumps(event, ensure_ascii=False, indent=2))
    else:
        print("未找到该事件")

# 测试关键词搜索
print("\n4. 关键词搜索 (搜索 '任嘉伦'):")
query = {"Event": {"$regex": "任嘉伦", "$options": "i"}}  # 不区分大小写搜索
keyword_events, keyword_total = db.search_events(query)
print(f"找到 {keyword_total} 个相关事件")
if keyword_events:
    print("第一个匹配的事件:")
    print(json.dumps(keyword_events[0], ensure_ascii=False, indent=2))

# 测试分页功能
print("\n5. 测试分页功能 (第1页，每页2个事件):")
paged_events, _ = db.search_events(page=1, page_size=2)
print(f"第1页有 {len(paged_events)} 个事件")

print("\n=== 数据库适配器测试结束 ===")

# 测试完成后关闭数据库连接
db.close()