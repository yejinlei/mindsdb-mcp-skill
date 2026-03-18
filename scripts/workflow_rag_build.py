#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流1: 本地RAG构建与管理
负责RAG系统初始化、知识库管理、数据字典管理和向量数据库操作
"""

import os
import json
import requests
import time
import subprocess
import sys
from typing import Dict, Any, Optional, List

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from data_dictionary import DataDictionary
from db_connector import get_db_connector


class RAGBuildWorkflow:
    """本地RAG构建与管理工作流"""
    
    def __init__(self):
        """初始化工作流"""
        # 配置参数
        self.default_host = "localhost"
        self.default_port = 47334
        self.default_username = os.getenv("MINDSDB_USERNAME", "admin")
        self.default_password = os.getenv("MINDSDB_PASSWORD", "password123")
        self.default_timeout = 30
        self.local_timeout = 10
        self.remote_timeout = 30
        
        # RAG默认配置
        self.default_rag_top_k = 3
        self.default_rag_threshold = 0.6
        
        # 本地RAG状态
        self.local_rag_initialized = False
        self.use_local_rag = False
        
        # 本地RAG持久化配置
        self.rag_persist_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            "..", "data", "chromadb_persist"
        )
        
        # 数据字典管理
        self.data_dictionary = DataDictionary()
        self.data_dict_persist_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            "..", "data", "data_dictionary.json"
        )
        
        # 多数据库RAG集合管理
        self.rag_collections = {}
        self.rag_client = None
        
        # 数据库连接器
        self.db_connector = get_db_connector()
    
    def _generate_response(self, code: int, msg: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """生成统一格式的响应"""
        response = {"code": code, "msg": msg}
        if data:
            response["data"] = data
        return response
    
    def _validate_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """验证参数"""
        if "action" not in params:
            return self._generate_response(-1, "Missing required parameter: action")
        
        action = params["action"]
        
        # 定义必需参数
        required_params = {
            "create_kb": ["kb_name"],
            "list_kb": [],
            "delete_kb": ["kb_name"],
            "get_data_dict_summary": [],
            "search_data_dict": ["keyword"],
            "refresh_data_dict": ["database"],
        }
        
        if action not in required_params:
            return self._generate_response(-2, f"Unsupported action: {action}")
        
        for req_param in required_params[action]:
            if req_param not in params or not params[req_param]:
                return self._generate_response(-3, f"Missing required parameter: {req_param}")
        
        # 补全可选参数
        params.setdefault("host", self.default_host)
        params.setdefault("port", self.default_port)
        params.setdefault("username", self.default_username)
        params.setdefault("password", self.default_password)
        params.setdefault("top_k", self.default_rag_top_k)
        params.setdefault("threshold", self.default_rag_threshold)
        
        return params
    
    def setup_local_rag(self) -> bool:
        """设置本地RAG系统"""
        try:
            # 安装依赖
            print("安装本地RAG依赖...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "chromadb", "sentence-transformers"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                print(f"本地RAG依赖安装失败: {result.stderr[:500]}")
                return False
            
            # 导入依赖
            import chromadb
            
            # 确保持久化目录存在
            os.makedirs(self.rag_persist_dir, exist_ok=True)
            print(f"本地RAG持久化目录: {self.rag_persist_dir}")
            
            # 初始化ChromaDB
            self.rag_client = chromadb.PersistentClient(path=self.rag_persist_dir)
            print("本地RAG客户端初始化成功")
            
            # 加载嵌入模型
            print("加载嵌入模型...")
            
            # 设置国内源
            os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
            from sentence_transformers import SentenceTransformer
            
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("从国内源成功加载模型")
            
            # 标记初始化成功
            self.local_rag_initialized = True
            
            # 加载数据字典
            self._load_data_dictionary()
            
            return True
            
        except Exception as e:
            print(f"本地RAG系统初始化失败: {e}")
            self.local_rag_initialized = False
            return False
    
    def _load_data_dictionary(self) -> bool:
        """加载数据字典"""
        try:
            if os.path.exists(self.data_dict_persist_file):
                print(f"加载数据字典: {self.data_dict_persist_file}")
                if self.data_dictionary.load_from_file(self.data_dict_persist_file):
                    print("数据字典加载成功")
                    return True
            return False
        except Exception as e:
            print(f"加载数据字典异常: {e}")
            return False
    
    def _save_data_dictionary(self) -> bool:
        """保存数据字典"""
        try:
            os.makedirs(os.path.dirname(self.data_dict_persist_file), exist_ok=True)
            if self.data_dictionary.save_to_file(self.data_dict_persist_file):
                print(f"数据字典已保存: {self.data_dict_persist_file}")
                return True
            return False
        except Exception as e:
            print(f"保存数据字典失败: {e}")
            return False
    
    def _get_or_create_collection(self, database: str) -> Any:
        """获取或创建集合"""
        try:
            if database not in self.rag_collections:
                safe_database_name = database.replace('/', '_').replace('\\', '_').replace('.', '_')
                collection_name = f"mindsdb_skill_{safe_database_name}"
                self.rag_collections[database] = self.rag_client.get_or_create_collection(
                    name=collection_name,
                    metadata={"description": f"MindsDB Skill RAG知识库 for database: {database}"}
                )
            return self.rag_collections[database]
        except Exception as e:
            print(f"获取或创建集合失败: {e}")
            raise
    
    def _add_data_dictionary_to_rag(self) -> bool:
        """将数据字典添加到RAG"""
        try:
            if not self.rag_client or not hasattr(self, 'embedding_model'):
                return False
            
            print("将数据字典添加到RAG知识库...")
            
            rag_documents = self.data_dictionary.generate_rag_documents()
            
            for doc in rag_documents:
                try:
                    collection = self._get_or_create_collection("default")
                    collection.add(
                        ids=[doc['id']],
                        documents=[doc['text']],
                        metadatas=[doc['metadata']]
                    )
                except Exception as e:
                    print(f"添加文档 {doc['id']} 失败: {e}")
                    continue
            
            return True
        except Exception as e:
            print(f"添加数据字典到RAG失败: {e}")
            return False
    
    def _execute_local_rag(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行本地RAG操作"""
        action = params["action"]
        kb_name = params.get("kb_name")
        database = params.get("database", "default")
        
        if action == "create_kb":
            # 创建本地RAG知识库
            collection = self._get_or_create_collection(database)
            
            # 尝试从数据库获取数据
            host = params["host"]
            port = params["port"]
            timeout = self.local_timeout
            
            mcp_paths = [
                f"http://{host}:{port}/api/sql/query",
                f"http://{host}:{port}/mcp",
                f"http://{host}:{port}/api/mcp/v1/query",
                f"http://{host}:{port}/api/query",
                f"http://{host}:{port}/query"
            ]
            
            # 使用公共连接器获取数据库列表
            db_list_result = self.db_connector.list_databases(host, port)
            if db_list_result.get("code") == 0:
                databases = [row[0] for row in db_list_result.get("data", {}).get("data", [])]
            
            # 尝试获取周报相关数据
            if databases:
                weekly_report_db = None
                for db in databases:
                    if "weekly" in db.lower() or "周报" in db:
                        weekly_report_db = db
                        break
                
                if not weekly_report_db and databases:
                    weekly_report_db = databases[0]
                
                if weekly_report_db:
                    # 使用公共连接器获取表列表
                    tables_result = self.db_connector.show_tables(weekly_report_db, host, port)
                    tables = []
                    if tables_result.get("code") == 0:
                        tables = [row[0] for row in tables_result.get("data", {}).get("data", [])]
                    
                    # 提取数据并添加到RAG
                    if tables:
                        for table in tables:
                            # 使用公共连接器获取表结构
                            columns = []
                            describe_result = self.db_connector.describe_table(weekly_report_db, table, host, port)
                            if describe_result.get("code") == 0:
                                columns = [row[0] for row in describe_result.get("data", {}).get("data", [])]
                            
                            # 使用公共连接器获取表数据
                            if columns:
                                data_result = self.db_connector.execute_sql(
                                    f"SELECT * FROM {weekly_report_db}.{table} LIMIT 10",
                                    host, port
                                )
                                data = []
                                if data_result.get("code") == 0:
                                    data = data_result.get("data", {}).get("data", [])
                                
                                # 添加数据到RAG
                                for i, row in enumerate(data):
                                    doc = f"表 {table} 第 {i+1} 行: "
                                    for j, col_name in enumerate(columns):
                                        if j < len(row):
                                            doc += f"{col_name}: {row[j]}, "
                                    doc = doc.rstrip(", ")
                                    
                                    try:
                                        collection.add(
                                            ids=[f"{table}_{i}"],
                                            documents=[doc],
                                            metadatas=[{"source": "database", "table": table, "database": weekly_report_db}]
                                        )
                                    except Exception as e:
                                        print(f"添加数据失败: {e}")
            
            # 提取数据字典
            self._add_data_dictionary_to_rag()
            
            return self._generate_response(0, "Local RAG knowledge base created", {
                "kb_name": kb_name,
                "database": database,
                "status": "created",
                "system": "local_rag",
                "persist_dir": self.rag_persist_dir
            })
        
        elif action == "list_kb":
            # 列出知识库
            collections_info = []
            for db, collection in self.rag_collections.items():
                collections_info.append({
                    "database": db,
                    "collection_name": collection.name,
                    "status": "active"
                })
            
            if not collections_info:
                collections_info = [{
                    "database": "default",
                    "collection_name": "mindsdb_skill_default",
                    "status": "not_created"
                }]
            
            return self._generate_response(0, "Local RAG knowledge bases listed", {
                "knowledge_bases": collections_info,
                "system": "local_rag",
                "persist_dir": self.rag_persist_dir
            })
        
        elif action == "delete_kb":
            # 删除知识库
            if database in self.rag_collections:
                del self.rag_collections[database]
            
            return self._generate_response(0, "Local RAG knowledge base deleted", {
                "kb_name": kb_name,
                "database": database,
                "status": "deleted",
                "system": "local_rag"
            })
        
        else:
            return self._generate_response(-2, f"Unsupported RAG action: {action}")
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行RAG构建工作流操作"""
        # 参数验证
        validated_params = self._validate_parameters(params)
        if validated_params.get("code") is not None:
            return validated_params
        
        action = validated_params["action"]
        
        # 数据字典操作
        if action in ["get_data_dict_summary", "search_data_dict", "refresh_data_dict"]:
            self._load_data_dictionary()
            
            if action == "get_data_dict_summary":
                return self._generate_response(0, "Get data dictionary summary success", {
                    "summary": self.data_dictionary.generate_summary()
                })
            
            elif action == "search_data_dict":
                keyword = validated_params.get("keyword")
                results = self.data_dictionary.search_metadata(keyword)
                return self._generate_response(0, "Search data dictionary success", {
                    "keyword": keyword,
                    "results": results
                })
            
            elif action == "refresh_data_dict":
                database = validated_params.get("database")
                # 这里可以实现从数据库刷新数据字典的逻辑
                self._save_data_dictionary()
                return self._generate_response(0, "Data dictionary refreshed", {
                    "database": database
                })
        
        # RAG操作
        if action in ["create_kb", "list_kb", "delete_kb"]:
            # 确保本地RAG已初始化
            if not self.local_rag_initialized:
                if not self.setup_local_rag():
                    return self._generate_response(-10, "本地RAG初始化失败")
            
            # 执行本地RAG操作
            return self._execute_local_rag(validated_params)
        
        return self._generate_response(-2, f"Unsupported action: {action}")


# 工作流入口函数
_rag_build_workflow = None

def rag_build_workflow_entry(params: Dict[str, Any]) -> Dict[str, Any]:
    """RAG构建工作流入口函数"""
    global _rag_build_workflow
    
    if _rag_build_workflow is None:
        _rag_build_workflow = RAGBuildWorkflow()
    
    return _rag_build_workflow.execute(params)
