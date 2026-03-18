#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流2: 基于RAG的NLP2SQL和数据分析
负责利用RAG进行自然语言处理、NLP2SQL转换、智能数据分析和知识库问答
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

from db_connector import get_db_connector


class RAGAnalysisWorkflow:
    """基于RAG的NLP2SQL和数据分析工作流"""
    
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
        
        # 本地RAG状态
        self.local_rag_initialized = False
        self.use_local_rag = False
        
        # 本地RAG持久化配置
        self.rag_persist_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            "..", "data", "chromadb_persist"
        )
        
        # 多数据库RAG集合管理
        self.rag_collections = {}
        self.rag_client = None
        self.embedding_model = None
        
        # 数据库连接器
        self.db_connector = get_db_connector()
    
    def check_mindsdb_installed(self) -> bool:
        """检查MindsDB是否已安装"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return "mindsdb" in result.stdout.lower()
        except Exception as e:
            print(f"检查MindsDB安装状态失败: {e}")
            return False
    
    def install_mindsdb(self) -> bool:
        """安装MindsDB"""
        try:
            print("开始安装MindsDB...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "mindsdb"],
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode != 0:
                print(f"MindsDB安装失败: {result.stderr[:500]}")
                return False
            print("MindsDB安装成功")
            return True
        except Exception as e:
            print(f"MindsDB安装失败: {e}")
            return False
    
    def start_mindsdb_service(self) -> bool:
        """启动MindsDB服务"""
        try:
            print("开始启动MindsDB服务...")
            process = subprocess.Popen(
                [sys.executable, "-m", "mindsdb"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            start_time = time.time()
            while time.time() - start_time < 30:
                time.sleep(2)
                if self.check_mindsdb_service_running():
                    print("MindsDB服务启动成功")
                    return True
            
            print("MindsDB服务启动超时")
            process.terminate()
            return False
        except Exception as e:
            print(f"MindsDB服务启动失败: {e}")
            return False
    
    def check_mindsdb_service_running(self) -> bool:
        """检查MindsDB服务是否正在运行"""
        ports_to_try = [47334, 47335, 47336, 47337]
        
        for port in ports_to_try:
            try:
                response = requests.get(
                    f"http://{self.default_host}:{port}/mcp", 
                    timeout=5
                )
                if response.status_code in [200, 405]:
                    self.default_port = port
                    return True
            except:
                continue
        
        return False
    
    def ensure_mindsdb_ready(self) -> bool:
        """确保MindsDB已安装并运行"""
        if self.check_mindsdb_service_running():
            return True
        
        if not self.check_mindsdb_installed():
            if not self.install_mindsdb():
                return False
        
        return self.start_mindsdb_service()
    
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
        
        # 检查 exec_sql 操作的 SQL 语句
        if action == "exec_sql":
            sql = params.get("sql", "").strip().upper()
            allowed_read_only_commands = ["SELECT", "SHOW", "DESCRIBE", "EXPLAIN", "PRAGMA"]
            prohibited_modify_commands = ["INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "TRUNCATE"]
            
            for cmd in prohibited_modify_commands:
                if sql.startswith(cmd):
                    return self._generate_response(-16, f"SQL command {cmd} is prohibited")
            
            is_read_only = any(sql.startswith(cmd) for cmd in allowed_read_only_commands)
            if not is_read_only:
                return self._generate_response(-17, "Only read-only SQL commands are allowed")
        
        # 定义必需参数
        required_params = {
            "connect_db": ["db_type"],
            "list_databases": [],
            "show_table_schema": ["database"],
            "nl_query": ["database", "nl_text"],
            "exec_sql": ["database", "sql"],
            "analyze_data": ["database", "nl_text"],
            "query_kb": ["kb_name", "nl_text"],
            "create_model": ["model_name", "predict_field"],
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
        
        return params
    
    def _get_mcp_paths(self, host: str, port: int) -> List[str]:
        """获取MCP接口路径列表"""
        return [
            f"http://{host}:{port}/api/sql/query",
            f"http://{host}:{port}/mcp",
            f"http://{host}:{port}/api/mcp/v1/query",
            f"http://{host}:{port}/api/query",
            f"http://{host}:{port}/query"
        ]
    
    def _send_mcp_request(self, request_body: Dict, mcp_paths: List[str], timeout: int) -> Dict:
        """发送MCP请求"""
        headers = {"Content-Type": "application/json"}
        
        for mcp_url in mcp_paths:
            try:
                response = requests.post(
                    url=mcp_url,
                    headers=headers,
                    data=json.dumps(request_body),
                    timeout=timeout
                )
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        if response_data.get("type") == "table":
                            return self._generate_response(0, "success", {
                                "data": response_data.get("data", []),
                                "columns": response_data.get("column_names", [])
                            })
                        elif response_data.get("type") == "error":
                            return self._generate_response(-4, response_data.get("error_message", "Request failed"))
                        else:
                            return self._generate_response(0, "success", response_data)
                    except json.JSONDecodeError:
                        continue
            except Exception:
                continue
        
        return self._generate_response(-7, "All MCP paths failed")
    
    def _get_timeout(self, host: str) -> int:
        """根据连接类型获取超时时间"""
        return self.remote_timeout if host != "localhost" else self.local_timeout
    
    def _setup_local_rag(self) -> bool:
        """设置本地RAG系统"""
        try:
            # 安装依赖
            import subprocess
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "chromadb", "sentence-transformers"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                return False
            
            # 导入依赖
            import chromadb
            
            # 初始化ChromaDB
            self.rag_client = chromadb.PersistentClient(path=self.rag_persist_dir)
            
            # 加载嵌入模型
            os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
            from sentence_transformers import SentenceTransformer
            
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            self.local_rag_initialized = True
            
            return True
        except Exception:
            self.local_rag_initialized = False
            return False
    
    def _get_or_create_collection(self, database: str) -> Any:
        """获取或创建集合"""
        try:
            if database not in self.rag_collections:
                safe_database_name = database.replace('/', '_').replace('\\', '_').replace('.', '_')
                collection_name = f"mindsdb_skill_{safe_database_name}"
                self.rag_collections[database] = self.rag_client.get_or_create_collection(
                    name=collection_name
                )
            return self.rag_collections[database]
        except Exception:
            raise
    
    def _execute_local_rag_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行本地RAG查询"""
        nl_text = params.get("nl_text")
        database = params.get("database", "default")
        top_k = params.get("top_k", 3)
        
        if not self.local_rag_initialized:
            if not self._setup_local_rag():
                return self._generate_response(-10, "本地RAG初始化失败")
        
        try:
            collection = self._get_or_create_collection(database)
            results = collection.query(
                query_texts=[nl_text],
                n_results=top_k
            )
            
            # 处理查询结果
            if "人" in nl_text or "涉及的人" in nl_text:
                import re
                person_names = []
                for doc_list in results.get("documents", []):
                    for doc in doc_list:
                        if doc:
                            names = re.findall(r'[张王李赵孙周吴郑][一二三四五六七八九十百千]*[a-zA-Z0-9\u4e00-\u9fa5]{1,2}', doc)
                            person_names.extend(names)
                person_names = list(set(person_names))
                
                if person_names:
                    return self._generate_response(0, "Local RAG query success", {
                        "query": nl_text,
                        "results": {
                            "people": person_names,
                            "system": "local_rag"
                        }
                    })
            
            return self._generate_response(0, "Local RAG query success", {
                "query": nl_text,
                "results": results,
                "system": "local_rag",
                "database": database
            })
        except Exception as e:
            return self._generate_response(-8, f"Local RAG error: {str(e)}")
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行RAG分析工作流操作"""
        # 参数验证
        validated_params = self._validate_parameters(params)
        if validated_params.get("code") is not None:
            return validated_params
        
        action = validated_params["action"]
        host = validated_params["host"]
        port = validated_params["port"]
        timeout = self._get_timeout(host)
        mcp_paths = self._get_mcp_paths(host, port)
        
        # 数据库连接和管理 - 使用公共连接器
        if action == "connect_db":
            db_type = params["db_type"]
            db_path = params.get("db_file", "") or params.get("db_path", "")
            database_name = params.get("database", f"{db_type}_db")
            
            result = self.db_connector.connect_database(
                db_type=db_type,
                db_path=db_path,
                database=database_name,
                host=host,
                port=port,
                username=params.get("username", self.default_username),
                password=params.get("password", self.default_password)
            )
            return result
        
        elif action == "list_databases":
            return self.db_connector.list_databases(host, port)
        
        elif action == "show_table_schema":
            database = params["database"]
            return self.db_connector.show_tables(database, host, port)
        
        # NLP2SQL和数据分析
        elif action == "nl_query":
            database = params["database"]
            nl_text = params["nl_text"]
            query = f"SELECT * FROM {database}.nl_query('{nl_text}')"
            return self.db_connector.execute_sql(query, host, port)
        
        elif action == "exec_sql":
            return self.db_connector.execute_sql(params["sql"], host, port)
        
        elif action == "analyze_data":
            database = params["database"]
            nl_text = params["nl_text"]
            query = f"SELECT * FROM {database}.analyze('{nl_text}')"
            return self.db_connector.execute_sql(query, host, port)
        
        elif action == "create_model":
            model_name = params["model_name"]
            predict_field = params["predict_field"]
            database = params.get("database")
            if database:
                query = f"CREATE MODEL {model_name} PREDICT {predict_field} USING DATABASE {database}"
            else:
                query = f"CREATE MODEL {model_name} PREDICT {predict_field}"
            return self.db_connector.execute_sql(query, host, port)
        
        # 知识库查询
        elif action == "query_kb":
            # 尝试使用本地RAG
            return self._execute_local_rag_query(validated_params)
        
        return self._generate_response(-2, f"Unsupported action: {action}")


# 工作流入口函数
_rag_analysis_workflow = None

def rag_analysis_workflow_entry(params: Dict[str, Any]) -> Dict[str, Any]:
    """RAG分析工作流入口函数"""
    global _rag_analysis_workflow
    
    if _rag_analysis_workflow is None:
        _rag_analysis_workflow = RAGAnalysisWorkflow()
    
    workflow = _rag_analysis_workflow
    
    if not workflow.ensure_mindsdb_ready():
        return workflow._generate_response(-9, "MindsDB服务未就绪")
    
    return workflow.execute(params)
