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

# 在文件顶部添加导入
from metadata_extractor import MetadataExtractor

# 添加训练数据收集器导入
try:
    from nl2sql.training_data import TrainingDataCollector, get_training_data_collector
    TRAINING_COLLECTOR_AVAILABLE = True
except ImportError:
    TRAINING_COLLECTOR_AVAILABLE = False

# 在 RAGBuildWorkflow 类中添加新方法
def extract_and_index_metadata(self, db_path: str, collection) -> bool:
    """提取元数据并添加到RAG"""
    try:
        extractor = MetadataExtractor()
        data_dict = extractor.extract_from_duckdb(db_path)
        
        # 生成RAG文档并添加
        documents = data_dict.generate_rag_documents()
        for doc in documents:
            collection.add(
                ids=[doc['id']],
                documents=[doc['text']],
                metadatas=[doc['metadata']]
            )
        
        return True
    except Exception as e:
        print(f"元数据提取失败: {e}")
        return False

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
        
        # 训练数据收集器（双存储架构）
        self.training_collector = None
        if TRAINING_COLLECTOR_AVAILABLE:
            try:
                self.training_collector = get_training_data_collector(self, enable_vector_store=True)
                print("训练数据收集器已初始化（双存储模式）")
            except Exception as e:
                print(f"训练数据收集器初始化失败: {e}")
    
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
            
            # 初始化训练数据收集器（双存储）
            if TRAINING_COLLECTOR_AVAILABLE and self.training_collector is None:
                try:
                    self.training_collector = get_training_data_collector(self, enable_vector_store=True)
                    print("训练数据收集器已初始化（双存储模式）")
                except Exception as e:
                    print(f"训练数据收集器初始化失败: {e}")
            
            # 同步现有训练数据到向量数据库
            if self.training_collector and self.training_collector.rag_workflow:
                print("同步训练数据到向量数据库...")
                sync_result = self.training_collector.sync_json_to_vector_store("default")
                print(f"同步结果: {sync_result}")
            
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
    
    def _refresh_data_dict_full(self, database: str) -> Dict[str, Any]:
        """
        全量刷新数据字典
        :param database: 数据库名
        :return: 刷新统计信息
        """
        try:
            from metadata_extractor import MetadataExtractor
            
            # 获取数据库路径（从配置或环境变量）
            db_path = self._get_database_path(database)
            
            # 全量提取元数据
            extractor = MetadataExtractor()
            new_data_dict = extractor.extract_from_duckdb(db_path)
            
            # 完全替换现有数据字典
            self.data_dictionary = new_data_dict
            
            return {
                "tables_extracted": len(new_data_dict.tables),
                "columns_extracted": sum(len(cols) for cols in new_data_dict.columns.values()),
                "relationships_detected": len(new_data_dict.relationships),
                "mode": "full"
            }
        except Exception as e:
            print(f"全量刷新数据字典失败: {e}")
            raise
    
    def _refresh_data_dict_incremental(self, database: str) -> Dict[str, Any]:
        """
        增量刷新数据字典
        :param database: 数据库名
        :return: 刷新统计信息
        """
        try:
            from metadata_extractor import MetadataExtractor
            
            # 获取数据库路径
            db_path = self._get_database_path(database)
            
            # 增量提取元数据（使用现有数据字典）
            extractor = MetadataExtractor()
            new_data_dict = extractor.extract_from_duckdb(
                db_path, 
                existing_data_dict=self.data_dictionary,
                mode='incremental'
            )
            
            # 合并更新
            merge_stats = self.data_dictionary.merge_with_existing(
                new_data_dict, 
                mode='incremental'
            )
            
            return {
                "tables_added": merge_stats.get('tables_added', 0),
                "tables_updated": merge_stats.get('tables_updated', 0),
                "columns_added": merge_stats.get('columns_added', 0),
                "columns_updated": merge_stats.get('columns_updated', 0),
                "relationships_added": merge_stats.get('relationships_added', 0),
                "total_changes": merge_stats.get('total_changes', 0),
                "mode": "incremental"
            }
        except Exception as e:
            print(f"增量刷新数据字典失败: {e}")
            raise
    
    def _update_rag_with_new_metadata(self, database: str) -> bool:
        """
        使用新的元数据更新 RAG 知识库
        :param database: 数据库名
        :return: 是否成功
        """
        try:
            if not self.training_collector:
                return False
            
            # 生成 RAG 文档
            rag_documents = self.data_dictionary.generate_rag_documents()
            
            # 添加到训练数据收集器（会自动双存储）
            for doc in rag_documents:
                try:
                    # 根据文档类型选择添加方法
                    doc_type = doc['metadata'].get('type', '')
                    
                    if doc_type == 'table':
                        # 表级文档：添加为 DDL
                        table_name = doc['metadata'].get('table_name', '')
                        table_meta = self.data_dictionary.get_table_metadata(table_name)
                        if table_meta:
                            # 生成 DDL
                            columns = self.data_dictionary.get_table_columns(table_name)
                            ddl = f"CREATE TABLE {table_name} (\n"
                            ddl += ",\n".join([f"    {col} VARCHAR" for col in columns])
                            ddl += "\n)"
                            
                            self.training_collector.add_ddl(
                                database=database,
                                table=table_name,
                                ddl=ddl,
                                description=table_meta.get('description', '')
                            )
                    
                    elif doc_type == 'column':
                        # 列级文档：添加为文档
                        table_name = doc['metadata'].get('table_name', '')
                        column_name = doc['metadata'].get('column_name', '')
                        column_meta = self.data_dictionary.get_column_metadata(table_name, column_name)
                        if column_meta:
                            content = f"表 {table_name} 的列 {column_name}：\n"
                            content += f"数据类型：{column_meta.get('data_type', '未知')}\n"
                            content += f"描述：{column_meta.get('description', '无')}\n"
                            content += f"业务含义：{column_meta.get('business_meaning', '无')}\n"
                            
                            self.training_collector.add_documentation(
                                database=database,
                                content=content,
                                title=f"{table_name}.{column_name}",
                                source='data_dictionary',
                                intent_tags=['metadata', 'column']
                            )
                    
                    elif doc_type == 'relationship':
                        # 关系文档：添加为文档
                        from_table = doc['metadata'].get('from_table', '')
                        to_table = doc['metadata'].get('to_table', '')
                        content = f"表关系：{from_table} -> {to_table}\n"
                        content += f"关系类型：{doc['metadata'].get('relationship_type', '未知')}\n"
                        
                        self.training_collector.add_documentation(
                            database=database,
                            content=content,
                            title=f"{from_table}->{to_table}",
                            source='data_dictionary',
                            intent_tags=['metadata', 'relationship']
                        )
                    
                    elif doc_type == 'business_domain':
                        # 业务域文档：添加为文档
                        domain_name = doc['metadata'].get('domain_name', '')
                        content = f"业务域：{domain_name}\n"
                        content += f"描述：{doc['metadata'].get('description', '无')}\n"
                        
                        self.training_collector.add_documentation(
                            database=database,
                            content=content,
                            title=domain_name,
                            source='data_dictionary',
                            intent_tags=['metadata', 'business_domain']
                        )
                
                except Exception as e:
                    print(f"添加文档到训练数据失败: {e}")
            
            return True
        except Exception as e:
            print(f"更新 RAG 知识库失败: {e}")
            return False
    
    def _get_database_path(self, database: str) -> str:
        """
        获取数据库路径
        :param database: 数据库名
        :return: 数据库文件路径
        """
        # 尝试从环境变量获取
        db_path = os.getenv(f"{database.upper()}_PATH")
        if db_path and os.path.exists(db_path):
            return db_path
        
        # 尝试从常用位置查找
        common_paths = [
            f"data/{database}.duckdb",
            f"data/{database}.db",
            f"../data/{database}.duckdb",
            f"../data/{database}.db",
            f"../../data/{database}.duckdb",
            f"../../data/{database}.db",
        ]
        
        for path in common_paths:
            full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
            if os.path.exists(full_path):
                return full_path
        
        # 如果都找不到，返回默认路径
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), f"data/{database}.duckdb")
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
                
                # 处理指定的数据库
                if database and database != "default":
                    # 使用公共连接器获取表列表
                    tables_result = self.db_connector.show_tables(database, host, port)
                    tables = []
                    if tables_result.get("code") == 0:
                        tables = [row[0] for row in tables_result.get("data", {}).get("data", [])]
                    
                    # 提取数据并添加到RAG
                    if tables:
                        max_tables = params.get("max_tables", 10)  # 可配置的最大表数，默认10
                        print(f"正在处理数据库 {database} 的 {len(tables)} 个表（限制前 {max_tables} 个）...")
                        for table in tables[:max_tables]:
                            print(f"\n处理表: {table}")
                            # 使用公共连接器获取表结构
                            columns = []
                            describe_result = self.db_connector.describe_table(database, table, host, port)
                            print(f"  describe_table 结果: {describe_result.get('code')}")
                            if describe_result.get("code") == 0:
                                data = describe_result.get("data", {})
                                print(f"  返回数据: {data}")
                                if "data" in data and isinstance(data["data"], list):
                                    columns = [row[0] for row in data["data"] if row]
                                    print(f"  表结构列数: {len(columns)}")
                                elif "columns" in data:
                                    columns = data["columns"]
                                    print(f"  表结构列数: {len(columns)}")
                                else:
                                    print(f"  数据结构: {list(data.keys())}")
                            
                            # 使用公共连接器获取表数据
                            if columns:
                                print(f"  获取表数据...")
                                data_result = self.db_connector.execute_sql(
                                    f"SELECT * FROM {database}.{table} LIMIT 10",
                                    host, port
                                )
                                data = []
                                if data_result.get("code") == 0:
                                    data = data_result.get("data", {}).get("data", [])
                                    print(f"  获取到 {len(data)} 行数据")
                                else:
                                    print(f"  获取表数据失败: {data_result.get('msg')}")
                                
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
                                            metadatas=[{"source": "database", "table": table, "database": database}]
                                        )
                                    except Exception as e:
                                        print(f"添加数据失败: {e}")
                            else:
                                print(f"  跳过表 {table}（没有列信息）")
                            
                            # 添加表结构到RAG
                            if columns:
                                schema_doc = f"表 {table} 结构: " + ", ".join(columns)
                                try:
                                    collection.add(
                                        ids=[f"{table}_schema"],
                                        documents=[schema_doc],
                                        metadatas=[{"source": "schema", "table": table, "database": database}]
                                    )
                                except Exception as e:
                                    print(f"添加表结构失败: {e}")
            
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
                mode = validated_params.get("mode", "incremental")  # 默认增量更新
                force_rebuild = validated_params.get("force_rebuild", False)
                
                try:
                    # 加载现有数据字典
                    self._load_data_dictionary()
                    
                    if force_rebuild:
                        # 强制重建：全量提取
                        print(f"强制重建数据字典: {database}")
                        result = self._refresh_data_dict_full(database)
                    elif mode == "incremental":
                        # 增量更新
                        print(f"增量更新数据字典: {database}")
                        result = self._refresh_data_dict_incremental(database)
                    else:
                        # 全量更新
                        print(f"全量更新数据字典: {database}")
                        result = self._refresh_data_dict_full(database)
                    
                    # 保存更新后的数据字典
                    self._save_data_dictionary()
                    
                    # 更新 RAG 知识库
                    if self.local_rag_initialized and self.training_collector:
                        print("更新 RAG 知识库...")
                        self._update_rag_with_new_metadata(database)
                    
                    return self._generate_response(0, "Data dictionary refreshed", {
                        "database": database,
                        "mode": mode,
                        "force_rebuild": force_rebuild,
                        **result
                    })
                except Exception as e:
                    print(f"刷新数据字典失败: {e}")
                    return self._generate_response(-11, f"Failed to refresh data dictionary: {str(e)}")
        
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
