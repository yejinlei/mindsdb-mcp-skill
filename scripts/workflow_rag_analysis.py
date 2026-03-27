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
from nl2sql.engine import get_nl2sql_engine


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
        
        # NL2SQL 引擎
        self.nl2sql_engine = get_nl2sql_engine(self)
        
        # MindsDB AI 能力状态缓存
        self._mindsdb_ai_available = None
        
        # Schema 提取器
        self._schema_extractor = None
    
    def _auto_extract_schema(self, db_type: str, db_path: str, database: str):
        """自动提取 Schema 并注册业务术语
        
        Args:
            db_type: 数据库类型
            db_path: 数据库路径
            database: 数据库名
        """
        try:
            from nl2sql.schema_extractor import get_schema_extractor
            from nl2sql.training_data import get_training_data_collector
            from nl2sql.intent_recognizer import get_intent_recognizer
            
            if self._schema_extractor is None:
                training_collector = get_training_data_collector(self)
                intent_recognizer = get_intent_recognizer()
                self._schema_extractor = get_schema_extractor(
                    training_collector, intent_recognizer
                )
            
            if db_type.lower() == "duckdb":
                result = self._schema_extractor.extract_from_duckdb(db_path, database)
            elif db_type.lower() == "sqlite":
                result = self._schema_extractor.extract_from_sqlite(db_path, database)
            elif db_type.lower() == "tdengine":
                # TDengine 通过 MCP API 提取 Schema
                tables = []
                inferred_terms = {}
                
                try:
                    # 查询所有表
                    show_tables_query = f"SHOW TABLES FROM {database}"
                    tables_result = self.db_connector.execute_sql(show_tables_query)
                    
                    if tables_result.get("code") == 0:
                        table_data = tables_result.get("data", {}).get("data", [])
                        
                        for row in table_data:
                            table_name = row[0]
                            
                            # 查询表结构
                            describe_query = f"DESCRIBE {database}.{table_name}"
                            describe_result = self.db_connector.execute_sql(describe_query)
                            
                            if describe_result.get("code") == 0:
                                columns_data = describe_result.get("data", {}).get("data", [])
                                columns = []
                                
                                for col_row in columns_data:
                                    columns.append({
                                        "name": col_row[0],
                                        "type": col_row[1]
                                    })
                                
                                tables.append({
                                    "name": table_name,
                                    "columns": columns
                                })
                                
                                # 简单的术语推断
                                if "time" in table_name.lower():
                                    inferred_terms["时间"] = [table_name]
                                elif "data" in table_name.lower():
                                    inferred_terms["数据"] = [table_name]
                                elif "record" in table_name.lower():
                                    inferred_terms["记录"] = [table_name]
                
                except Exception as e:
                    print(f"[Schema 自动提取] TDengine 提取失败: {e}")
                
                result = {
                    "status": "success",
                    "tables": tables,
                    "inferred_terms": inferred_terms
                }
            else:
                return
            
            if result.get("status") == "success":
                print(f"[Schema 自动提取] 数据库: {database}")
                print(f"  表数量: {len(result.get('tables', []))}")
                print(f"  推断术语: {len(result.get('inferred_terms', {}))} 个")
                
                for term, fields in result.get("inferred_terms", {}).items():
                    print(f"    '{term}' → {fields}")
        
        except Exception as e:
            print(f"[Schema 自动提取] 失败: {e}")
    
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
            "nl2sql": ["database", "nl_text"],
            "smart_query": ["database", "nl_text"],
            "generate_sql_prompt": ["database", "nl_text"],
            "validate_sql": ["database", "sql"],
            "init_training": ["database"],
            "add_training_sql": ["database", "sql", "question"],
            "add_training_doc": ["database", "content"],
            "get_training_stats": ["database"]
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

    def _execute_database_query(self, database: str, nl_text: str) -> Dict[str, Any]:
        """执行数据库查询以补充RAG结果 - 通用版本"""
        try:
            results = {}
            
            # 检查是否有直接的数据库连接
            if hasattr(self.db_connector, 'conn') and self.db_connector.conn is not None:
                # 使用直接的数据库连接
                conn = self.db_connector.conn
                
                # 获取数据库中的所有表
                tables = conn.execute("SHOW TABLES").fetchall()
                table_names = [table[0] for table in tables]
                
                # 对每个表进行搜索
                for table in table_names:
                    # 获取表结构
                    schema = conn.execute(f"DESCRIBE {table}").fetchall()
                    
                    # 分析每个字段，确定搜索策略
                    searchable_columns = []
                    for col_info in schema:
                        col_name = col_info[0]
                        col_type = col_info[1]
                        
                        # 简化字段类型检查，包含所有可能的文本类型
                        if 'VARCHAR' in col_type.upper() or 'TEXT' in col_type.upper() or 'CHAR' in col_type.upper():
                            searchable_columns.append(col_name)
                    
                    if not searchable_columns:
                        continue
                    
                    # 构建搜索SQL - 搜索所有文本字段
                    where_conditions = []
                    for col in searchable_columns:
                        where_conditions.append(f"{col} LIKE '%{nl_text}%'")
                    
                    # 限制结果数量，避免返回过多数据
                    sql = f"SELECT {', '.join(searchable_columns)} FROM {table} WHERE {' OR '.join(where_conditions)} LIMIT 10"
                    
                    try:
                        table_result = conn.execute(sql).fetchall()
                        if table_result:
                            # 使用表名作为结果的key
                            results[table] = {
                                "columns": searchable_columns,
                                "rows": table_result,
                                "count": len(table_result)
                            }
                    except Exception as e:
                        # 如果某个表查询失败，继续查询其他表
                        continue
            else:
                # 使用MCP协议进行查询
                # 获取数据库中的所有表
                show_tables_result = self.db_connector.show_tables(database)
                if show_tables_result.get('code') != 0:
                    return {"error": f"Failed to get tables: {show_tables_result.get('msg')}"}
                
                tables_data = show_tables_result.get('data', {})
                table_names = []
                if 'data' in tables_data:
                    # 提取表名
                    for row in tables_data['data']:
                        if row:
                            table_names.append(row[0])
                
                # 对每个表进行搜索
                for table in table_names:
                    # 获取表结构
                    describe_result = self.db_connector.describe_table(database, table)
                    if describe_result.get('code') != 0:
                        continue
                    
                    schema_data = describe_result.get('data', {})
                    searchable_columns = []
                    if 'data' in schema_data and 'columns' in schema_data:
                        columns = schema_data['columns']
                        rows = schema_data['data']
                        # 分析每个字段，确定搜索策略
                        for i, row in enumerate(rows):
                            if i < len(columns):
                                col_name = row[0] if row else ''
                                # 假设类型在第二列
                                col_type = row[1] if len(row) > 1 else ''
                                
                                # 简化字段类型检查
                                if 'VARCHAR' in col_type.upper() or 'TEXT' in col_type.upper() or 'CHAR' in col_type.upper():
                                    searchable_columns.append(col_name)
                    
                    if not searchable_columns:
                        continue
                    
                    # 构建搜索SQL - 搜索所有文本字段
                    where_conditions = []
                    for col in searchable_columns:
                        where_conditions.append(f"{col} LIKE '%{nl_text}%'")
                    
                    # 限制结果数量，避免返回过多数据
                    sql = f"SELECT {', '.join(searchable_columns)} FROM {database}.{table} WHERE {' OR '.join(where_conditions)} LIMIT 10"
                    
                    try:
                        table_result = self.db_connector.execute_sql(sql)
                        if table_result.get('code') == 0:
                            result_data = table_result.get('data', {})
                            if 'data' in result_data and 'columns' in result_data:
                                rows = result_data['data']
                                if rows:
                                    # 使用表名作为结果的key
                                    results[table] = {
                                        "columns": result_data['columns'],
                                        "rows": rows,
                                        "count": len(rows)
                                    }
                    except Exception as e:
                        # 如果某个表查询失败，继续查询其他表
                        continue
            
            return results
        except Exception as e:
            return {"error": str(e)}
    
    def _extract_person_name(self, text: str) -> str:
        """从文本中提取人名 - 通用版本"""
        import re
        
        # 查找2-4个汉字的连续组合
        pattern = r'[\u4e00-\u9fa5]{2,4}'
        matches = re.findall(pattern, text)
        
        # 优先返回长度为2-3的匹配结果
        for match in matches:
            if 2 <= len(match) <= 3:
                return match
        
        return text
    
    def _enhanced_query_workflow(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """增强型查询工作流：RAG + 数据库补充 - 通用版本"""
        nl_text = params.get("nl_text")
        database = params.get("database", "default")
        
        # 1. 执行RAG查询
        rag_result = self._execute_local_rag_query(params)
        
        # 2. 评估RAG结果
        rag_has_results = False
        if rag_result.get("code") == 0 and rag_result.get("data"):
            results = rag_result.get("data", {}).get("results", {})
            if isinstance(results, dict) and "documents" in results:
                rag_has_results = any(doc for doc_list in results["documents"] for doc in doc_list)
        
        # 3. 如果RAG结果不充分，补充数据库查询
        if not rag_has_results:
            # 执行数据库补充查询
            db_results = self._execute_database_query(database, nl_text)
            
            # 构建增强型结果
            enhanced_data = {
                "rag_results": rag_result.get("data"),
                "db_results": db_results,
                "system": "enhanced",
                "query": nl_text
            }
            
            # 处理数据库查询结果
            if db_results and "error" not in db_results and isinstance(db_results, dict):
                # 构建人类可读的结果
                readable_results = []
                
                # 遍历所有表的查询结果
                for table_name, table_data in db_results.items():
                    if isinstance(table_data, dict) and "columns" in table_data and "rows" in table_data and "count" in table_data:
                        columns = table_data["columns"]
                        rows = table_data["rows"]
                        count = table_data["count"]
                        
                        readable_results.append(f"\n=== 表: {table_name} (找到 {count} 条记录) ===")
                        
                        # 显示前5条记录
                        for i, row in enumerate(rows[:5]):
                            row_str = "  "
                            for j, value in enumerate(row):
                                if j < len(columns):
                                    col_name = columns[j]
                                    # 截断过长的文本
                                    if isinstance(value, str) and len(value) > 50:
                                        value = value[:50] + "..."
                                    row_str += f"{col_name}={value} | "
                            readable_results.append(row_str)
                        
                        if count > 5:
                            readable_results.append(f"  ... 还有 {count - 5} 条记录")
                
                enhanced_data["readable_results"] = readable_results
            
            return self._generate_response(0, "Enhanced query success", enhanced_data)
        
        return rag_result
    
    def _execute_nl2sql(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行 NL2SQL 操作"""
        nl_text = params.get("nl_text")
        database = params.get("database", "default")
        
        try:
            # 1. 生成 SQL
            sql = self.nl2sql_engine.generate_sql(nl_text, database)
            
            # 2. 执行 SQL
            result = self.nl2sql_engine.execute_sql(sql, database)
            
            # 3. 处理结果
            processed_result = self.nl2sql_engine.process_result(result, nl_text)
            
            # 4. 构建响应
            response_data = {
                "nl_text": nl_text,
                "generated_sql": sql,
                "result": processed_result,
                "system": "nl2sql"
            }
            
            return self._generate_response(0, "NL2SQL execution success", response_data)
        except Exception as e:
            return self._generate_response(-11, f"NL2SQL error: {str(e)}")
    
    def _check_mindsdb_ai_capability(self) -> bool:
        """检查 MindsDB 是否配置了 AI 能力"""
        if self._mindsdb_ai_available is not None:
            return self._mindsdb_ai_available
        
        try:
            # 尝试执行一个简单的 nl_query 测试
            test_result = self.db_connector.execute_sql(
                "SELECT * FROM information_schema.tables LIMIT 1"
            )
            # 如果能执行 SQL，说明 MindsDB 可用
            # 但 nl_query 需要额外配置 embedding model
            # 这里简化处理：如果 MindsDB 服务可用，假设 AI 能力可用
            self._mindsdb_ai_available = test_result.get("code") == 0
            return self._mindsdb_ai_available
        except Exception:
            self._mindsdb_ai_available = False
            return False
    
    def _check_local_rag_available(self) -> bool:
        """检查本地 RAG 是否可用"""
        if self.local_rag_initialized:
            return True
        
        # 尝试初始化本地 RAG
        return self._setup_local_rag()
    
    def _check_kb_exists(self, kb_name: str) -> bool:
        """检查知识库是否存在"""
        try:
            if not self.local_rag_initialized:
                return False
            
            safe_kb_name = kb_name.replace('/', '_').replace('\\', '_').replace('.', '_')
            collection_name = f"mindsdb_skill_{safe_kb_name}"
            
            # 尝试获取集合
            collections = self.rag_client.list_collections()
            return any(c.name == collection_name for c in collections)
        except Exception:
            return False
    
    def _execute_smart_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """智能查询：自动选择最佳查询方式
        
        路由策略：
        1. 如果指定了 kb_name 且知识库存在 -> query_kb
        2. 如果 MindsDB AI 可用 -> nl_query
        3. 如果本地 RAG 可用 -> nl2sql
        4. 降级到 nl2sql（纯规则模式）
        """
        nl_text = params.get("nl_text")
        database = params.get("database", "default")
        kb_name = params.get("kb_name")
        
        route_info = {
            "attempted_methods": [],
            "selected_method": None,
            "reason": None
        }
        
        # 策略1: 如果指定了知识库且存在，优先使用知识库
        if kb_name:
            route_info["attempted_methods"].append("query_kb")
            if self._check_kb_exists(kb_name):
                route_info["selected_method"] = "query_kb"
                route_info["reason"] = "指定的知识库存在"
                kb_params = {
                    "action": "query_kb",
                    "kb_name": kb_name,
                    "nl_text": nl_text
                }
                result = self._enhanced_query_workflow(kb_params)
                # 确保 result 有 data 字段
                if result.get("code") == 0 and "data" in result:
                    result["data"]["route_info"] = route_info
                else:
                    # 如果失败，添加路由信息到错误响应
                    result["route_info"] = route_info
                return result
            else:
                route_info["reason"] = f"知识库 {kb_name} 不存在"
        
        # 策略2: 检查 MindsDB AI 能力
        route_info["attempted_methods"].append("nl_query")
        if self._check_mindsdb_ai_capability():
            route_info["selected_method"] = "nl_query"
            route_info["reason"] = "MindsDB AI 能力可用"
            query = f"SELECT * FROM {database}.nl_query('{nl_text}')"
            result = self.db_connector.execute_sql(query)
            # 确保 result 有 data 字段
            if result.get("code") == 0 and "data" in result:
                result["data"]["route_info"] = route_info
            else:
                # 如果失败，添加路由信息到错误响应
                result["route_info"] = route_info
            return result
        
        # 策略3: 使用本地 NL2SQL 引擎
        route_info["attempted_methods"].append("nl2sql")
        route_info["selected_method"] = "nl2sql"
        
        # 尝试初始化本地 RAG 以增强 NL2SQL
        if self._check_local_rag_available():
            route_info["reason"] = "本地 RAG 可用，使用增强版 NL2SQL"
        else:
            route_info["reason"] = "使用纯规则 NL2SQL（无嵌入模型）"
        
        result = self._execute_nl2sql(params)
        # 确保 result 有 data 字段
        if result.get("code") == 0 and "data" in result:
            result["data"]["route_info"] = route_info
        else:
            # 如果失败，添加路由信息到错误响应
            result["route_info"] = route_info
        return result
    
    def _execute_init_training(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """初始化训练数据"""
        database = params.get("database")
        auto_add_ddl = params.get("auto_add_ddl", True)
        
        try:
            result = self.nl2sql_engine.initialize_from_schema(database, auto_add_ddl)
            return self._generate_response(0, "Training data initialized", result)
        except Exception as e:
            return self._generate_response(-11, f"Init training error: {str(e)}")
    
    def _execute_add_training_sql(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """添加 SQL 训练数据"""
        database = params.get("database")
        sql = params.get("sql")
        question = params.get("question")
        tables = params.get("tables")
        
        try:
            result = self.nl2sql_engine.add_training_sql(database, sql, question, tables)
            return self._generate_response(0, "Training SQL added", result)
        except Exception as e:
            return self._generate_response(-11, f"Add training SQL error: {str(e)}")
    
    def _execute_add_training_doc(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """添加文档训练数据"""
        database = params.get("database")
        content = params.get("content")
        title = params.get("title")
        source = params.get("source")
        
        try:
            result = self.nl2sql_engine.add_training_documentation(database, content, title, source)
            return self._generate_response(0, "Training documentation added", result)
        except Exception as e:
            return self._generate_response(-11, f"Add training doc error: {str(e)}")
    
    def _execute_get_training_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取训练数据统计"""
        database = params.get("database")
        
        try:
            result = self.nl2sql_engine.get_training_stats(database)
            return self._generate_response(0, "Training stats retrieved", result)
        except Exception as e:
            return self._generate_response(-11, f"Get training stats error: {str(e)}")
    
    def _execute_generate_sql_prompt(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """生成供 Agent LLM 使用的 SQL 生成 prompt
        
        这是 Vanna 风格的核心方法，返回 prompt 给 Agent，由 Agent 的 LLM 生成 SQL
        """
        database = params.get("database")
        nl_text = params.get("nl_text")
        
        try:
            result = self.nl2sql_engine.generate_sql_prompt_for_agent(nl_text, database)
            return self._generate_response(0, "SQL prompt generated for Agent LLM", result)
        except Exception as e:
            return self._generate_response(-11, f"Generate SQL prompt error: {str(e)}")
    
    def _execute_validate_sql(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """验证并修复 SQL 语句"""
        database = params.get("database")
        sql = params.get("sql")
        
        try:
            result = self.nl2sql_engine.validate_and_fix_sql(sql, database)
            return self._generate_response(0, "SQL validated", result)
        except Exception as e:
            return self._generate_response(-11, f"Validate SQL error: {str(e)}")

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
            
            if result.get("code") == 0 and db_path:
                self._auto_extract_schema(db_type, db_path, database_name)
            
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
            # 使用增强型查询工作流
            return self._enhanced_query_workflow(validated_params)
        
        # NL2SQL 操作
        elif action == "nl2sql":
            return self._execute_nl2sql(validated_params)
        
        # 智能查询（自动路由）
        elif action == "smart_query":
            return self._execute_smart_query(validated_params)
        
        # 训练数据管理
        elif action == "init_training":
            return self._execute_init_training(validated_params)
        
        elif action == "add_training_sql":
            return self._execute_add_training_sql(validated_params)
        
        elif action == "add_training_doc":
            return self._execute_add_training_doc(validated_params)
        
        elif action == "get_training_stats":
            return self._execute_get_training_stats(validated_params)
        
        elif action == "generate_sql_prompt":
            return self._execute_generate_sql_prompt(validated_params)
        
        elif action == "validate_sql":
            return self._execute_validate_sql(validated_params)
        
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
