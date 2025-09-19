#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库配置文件
用于配置和管理多个数据库连接
"""

import os

class DatabaseConfig:
    """数据库配置类，用于存储和管理所有数据库的配置信息"""
    
    # MongoDB 配置
    MONGODB_CONFIG = {
        'host': os.environ.get('MONGODB_HOST', 'localhost'),
        'port': int(os.environ.get('MONGODB_PORT', 27017)),
        'username': os.environ.get('MONGODB_USERNAME', ''),
        'password': os.environ.get('MONGODB_PASSWORD', ''),
        'db_name': os.environ.get('MONGODB_DB', 'admin'),  # 确保默认使用admin数据库
        'collection_name': os.environ.get('MONGODB_COLLECTION', 'event')  # 确保使用event集合
    }
    
    # 其他数据库配置（可以根据需要添加）
    # 例如 NebulaGraph 配置
    NEBULA_CONFIG = {
        'host': os.environ.get('NEBULA_HOST', 'localhost'),
        'port': int(os.environ.get('NEBULA_PORT', 9669)),
        'username': os.environ.get('NEBULA_USERNAME', 'root'),
        'password': os.environ.get('NEBULA_PASSWORD', 'nebula'),
        'space': os.environ.get('NEBULA_SPACE', 'test')
    }
    
    # 可以添加更多数据库配置...
    
    @classmethod
    def get_database_config(cls, db_type):
        """根据数据库类型获取对应的配置"""
        config_mapping = {
            'mongodb': cls.MONGODB_CONFIG,
            'nebula': cls.NEBULA_CONFIG
            # 添加更多数据库类型和对应的配置
        }
        
        return config_mapping.get(db_type.lower())

    @classmethod
    def set_database_config(cls, db_type, config):
        """动态设置数据库配置"""
        if db_type.lower() == 'mongodb':
            cls.MONGODB_CONFIG.update(config)
        elif db_type.lower() == 'nebula':
            cls.NEBULA_CONFIG.update(config)
        # 处理更多数据库类型

    @classmethod
    def get_all_database_types(cls):
        """获取所有支持的数据库类型"""
        return ['mongodb', 'nebula']  # 根据实际支持的数据库类型返回

# 默认数据库配置实例
DB_CONFIG = DatabaseConfig()