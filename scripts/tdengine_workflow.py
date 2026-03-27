#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TDengine 数据库工作流脚本
整合连接、元数据提取、RAG 知识库创建等功能
"""

import json
import sys
import os

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_connector import get_db_connector
from workflow_rag_build import rag_build_workflow_entry
from workflow_rag_analysis import rag_analysis_workflow_entry


def connect_tdengine(host="10.10.10.13", port=6041, username="root", password="taosdata", database="mqttex", **kwargs):
    """连接 TDengine 数据库"""
    print(f"[TDengine] 连接数据库: {database}@{host}:{port}")
    
    db = get_db_connector()
    result = db.connect_database(
        db_type="tdengine",
        host=host,
        port=port,
        username=username,
        password=password,
        database=database
    )
    
    if result.get("code") == 0:
        print("[TDengine] 连接成功！")
        return db
    else:
        print(f"[TDengine] 连接失败: {result.get('msg')}")
        return None


def list_tables(database="mqttex"):
    """列出数据库中的所有表"""
    print(f"[TDengine] 列出表: {database}")
    
    db = get_db_connector()
    result = db.show_tables(database)
    
    if result.get("code") == 0:
        tables = result.get("data", {}).get("data", [])
        print(f"[TDengine] 找到 {len(tables)} 个表:")
        for table in tables:
            print(f"  - {table[0]}")
        return tables
    else:
        print(f"[TDengine] 列出表失败: {result.get('msg')}")
        return []


def describe_table(database="mqttex", table_name=""):
    """查看表结构"""
    if not table_name:
        print("[TDengine] 请指定表名")
        return
    
    print(f"[TDengine] 查看表结构: {database}.{table_name}")
    
    db = get_db_connector()
    result = db.describe_table(database, table_name)
    
    if result.get("code") == 0:
        columns = result.get("data", {}).get("data", [])
        print(f"[TDengine] 表结构:")
        for col in columns:
            print(f"  - {col[0]} ({col[1]})")
        return columns
    else:
        print(f"[TDengine] 查看表结构失败: {result.get('msg')}")
        return []


def create_rag_knowledge_base(kb_name="tdengine_kb", database="mqttex"):
    """创建 RAG 知识库"""
    print(f"[RAG] 创建知识库: {kb_name} (数据库: {database})")
    
    params = {
        "action": "create_kb",
        "kb_name": kb_name,
        "database": database,
        "extract_metadata": True
    }
    
    result = rag_build_workflow_entry(params)
    
    if result.get("code") == 0:
        print("[RAG] 知识库创建成功！")
        return True
    else:
        print(f"[RAG] 知识库创建失败: {result.get('msg')}")
        return False


def query_knowledge_base(kb_name="tdengine_kb", nl_text=""):
    """查询 RAG 知识库"""
    if not nl_text:
        print("[RAG] 请输入查询文本")
        return
    
    print(f"[RAG] 查询知识库: {kb_name}")
    print(f"[RAG] 查询文本: {nl_text}")
    
    params = {
        "action": "query_kb",
        "kb_name": kb_name,
        "nl_text": nl_text
    }
    
    result = rag_analysis_workflow_entry(params)
    
    if result.get("code") == 0:
        print("[RAG] 查询结果:")
        print(json.dumps(result.get("data", {}), ensure_ascii=False, indent=2))
        return result.get("data", {})
    else:
        print(f"[RAG] 查询失败: {result.get('msg')}")
        return {}


def natural_language_query(database="mqttex", nl_text=""):
    """自然语言查询"""
    if not nl_text:
        print("[NL2SQL] 请输入查询文本")
        return
    
    print(f"[NL2SQL] 自然语言查询: {database}")
    print(f"[NL2SQL] 查询文本: {nl_text}")
    
    params = {
        "action": "smart_query",
        "database": database,
        "nl_text": nl_text
    }
    
    result = rag_analysis_workflow_entry(params)
    
    if result.get("code") == 0:
        print("[NL2SQL] 查询结果:")
        print(f"  SQL: {result.get('data', {}).get('sql', '')}")
        print(f"  结果: {result.get('data', {}).get('data', [])}")
        return result.get("data", {})
    else:
        print(f"[NL2SQL] 查询失败: {result.get('msg')}")
        return {}


def get_data_dict_summary():
    """获取数据字典摘要"""
    print("[数据字典] 获取摘要")
    
    params = {
        "action": "get_data_dict_summary"
    }
    
    result = rag_build_workflow_entry(params)
    
    if result.get("code") == 0:
        print("[数据字典] 摘要:")
        print(json.dumps(result.get("data", {}), ensure_ascii=False, indent=2))
        return result.get("data", {})
    else:
        print(f"[数据字典] 获取失败: {result.get('msg')}")
        return {}


def main():
    """主函数"""
    print("=" * 60)
    print("TDengine 数据库工作流")
    print("=" * 60)
    
    # 配置
    config = {
        "host": "10.10.10.13",
        "port": 6041,
        "username": "root",
        "password": "taosdata",
        "database": "mqttex",
        "kb_name": "tdengine_mqttex_kb"
    }
    
    # 1. 连接 TDengine
    db = connect_tdengine(**config)
    if not db:
        return
    
    # 2. 列出表
    tables = list_tables(config["database"])
    
    # 3. 查看第一个表的结构
    if tables:
        first_table = tables[0][0]
        describe_table(config["database"], first_table)
    
    # 4. 创建 RAG 知识库
    create_rag_knowledge_base(config["kb_name"], config["database"])
    
    # 5. 获取数据字典摘要
    get_data_dict_summary()
    
    # 6. 示例查询
    print("\n" + "=" * 60)
    print("示例查询")
    print("=" * 60)
    
    # 自然语言查询
    natural_language_query(
        config["database"],
        "查询所有表"
    )
    
    # 知识库查询
    query_knowledge_base(
        config["kb_name"],
        "数据库中有哪些表"
    )
    
    print("\n" + "=" * 60)
    print("工作流执行完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
