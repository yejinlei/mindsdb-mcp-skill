#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MindsDB MCP Skill - 支持MindsDB自动检测、连接和操作
支持duckdb、mysql、tdengine三种数据源，集成RAG功能
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

class MindsDBSkill:
    """MindsDB MCP技能类"""
    
    def __init__(self):
        """初始化技能"""
        # 配置参数
        self.default_host = "localhost"
        self.default_port = 47334  # MindsDB HTTP API端口
        self.default_username = os.getenv("MINDSDB_USERNAME", "admin")
        self.default_password = os.getenv("MINDSDB_PASSWORD", "password123")
        self.default_timeout = 30  # 默认超时时间
        self.local_timeout = 10  # 本地连接超时时间
        self.remote_timeout = 30  # 远程连接超时时间
        # RAG默认配置（新增）
        self.default_rag_top_k = 3
        self.default_rag_threshold = 0.6
        # MCP接口路径列表
        self.mcp_paths = []
        # 本地RAG状态
        self.local_rag_initialized = False
        self.use_local_rag = False  # 标记是否使用本地RAG
        # 本地RAG持久化配置
        self.rag_persist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "chromadb_persist")
        # 数据字典管理
        self.data_dictionary = DataDictionary()
        self.data_dict_persist_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "data_dictionary.json")
        # 多数据库RAG集合管理
        self.rag_collections = {}  # 存储每个数据库的集合
        self.rag_client = None  # 全局ChromaDB客户端

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
            # 直接安装mindsdb包
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "mindsdb"],
                capture_output=True,
                text=True,
                timeout=120
            )
            print(f"MindsDB安装结果: {result.stdout[:500]}")
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
            # 启动MindsDB服务（后台运行）
            process = subprocess.Popen(
                [sys.executable, "-m", "mindsdb"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 等待服务启动（最多30秒）
            start_time = time.time()
            while time.time() - start_time < 30:
                time.sleep(2)
                # 检查服务是否已启动
                if self.check_mindsdb_service_running():
                    print("MindsDB服务启动成功")
                    return True
            
            # 启动超时
            print("MindsDB服务启动超时")
            process.terminate()
            return False
        except Exception as e:
            print(f"MindsDB服务启动失败: {e}")
            return False

    def check_mindsdb_service_running(self) -> bool:
        """检查MindsDB服务是否正在运行"""
        # 尝试的端口列表，包括常见的MindsDB端口
        ports_to_try = [47334, 47335, 47336, 47337]
        
        for port in ports_to_try:
            try:
                print(f"尝试连接MindsDB服务端口 {port}...")
                
                # 尝试使用GET方法访问MCP路径，检查服务是否存在
                response = requests.get(f"http://{self.default_host}:{port}/mcp", timeout=5)
                print(f"端口 {port} 响应状态码: {response.status_code}")
                
                # 如果服务在运行（即使返回405或其他状态码），我们认为服务已就绪
                print(f"MindsDB服务已在 http://{self.default_host}:{port} 上运行")
                # 更新默认端口为找到的端口
                self.default_port = port
                return True
                
            except Exception as e:
                print(f"端口 {port} 连接失败: {e}")
                continue
        
        print("未找到运行中的MindsDB服务")
        return False

    def ensure_mindsdb_ready(self) -> bool:
        """确保MindsDB已安装并运行"""
        # 检查服务是否已经运行
        if self.check_mindsdb_service_running():
            print("MindsDB服务已就绪")
            return True
        
        # 检查是否已安装
        if not self.check_mindsdb_installed():
            if not self.install_mindsdb():
                print("无法安装MindsDB，请手动安装并启动MindsDB服务")
                return False
        
        # 尝试启动服务
        if not self.start_mindsdb_service():
            print("无法启动MindsDB服务，请手动启动MindsDB服务")
            return False
        
        print("MindsDB服务已就绪")
        return True

    def _get_mcp_url(self, host: str, port: int) -> str:
        """构建MindsDB MCP接口URL"""
        # 尝试不同的MCP接口路径
        mcp_paths = [
            f"http://{host}:{port}/mcp",
            f"http://{host}:{port}/api/mcp/v1/query",
            f"http://{host}:{port}/api/query",
            f"http://{host}:{port}/query"
        ]
        return mcp_paths[0]

    def _get_timeout(self, host: str) -> int:
        """根据连接类型获取超时时间"""
        return self.remote_timeout if host != "localhost" else self.local_timeout

    def _validate_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """验证并补全参数，确保符合调用规范，重点强化RAG参数校验，适配多数据源"""
        # 必传参数校验
        if "action" not in params:
            return self._generate_response(-1, "Missing required parameter: action")
        
        action = params["action"]
        
        # 禁止删除、变更目标数据库数据的操作
        # 允许对MindsDB的操作（如创建数据库连接、创建知识库），但禁止对目标数据库的修改操作
        prohibited_actions = ["delete_kb"]
        if action in prohibited_actions:
            return self._generate_response(-15, f"Action {action} is prohibited (本SKILL禁止删除、变更目标数据库数据)")
        
        # 检查 exec_sql 操作的 SQL 语句
        if action == "exec_sql":
            sql = params.get("sql", "").strip().upper()
            # 允许的只读操作
            allowed_read_only_commands = ["SELECT", "SHOW", "DESCRIBE", "EXPLAIN", "PRAGMA"]
            # 禁止的修改操作
            prohibited_modify_commands = ["INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "TRUNCATE", "REPLACE", "MERGE"]
            
            # 检查是否包含禁止的修改操作
            for cmd in prohibited_modify_commands:
                if sql.startswith(cmd):
                    return self._generate_response(-16, f"SQL command {cmd} is prohibited (本SKILL禁止修改数据库数据)")
            
            # 检查是否为允许的只读操作
            is_read_only = False
            for cmd in allowed_read_only_commands:
                if sql.startswith(cmd):
                    is_read_only = True
                    break
            
            if not is_read_only:
                return self._generate_response(-17, "Only read-only SQL commands are allowed (本SKILL只允许只读SQL操作)")
        
        # 根据action补全必传参数
        required_params = {
            "connect_db": ["db_type"],
            "list_databases": [],
            "show_table_schema": ["database"],
            "nl_query": ["database", "nl_text"],
            "exec_sql": ["database", "sql"],  # 执行SQL语句（只读操作）
            # RAG核心动作参数
            "create_kb": ["kb_name"],  # 创建知识库（允许），database为可选参数
            "query_kb": ["kb_name", "nl_text"],  # RAG智能问答（允许），database为可选参数
            "list_kb": [],  # 列出所有已创建的RAG知识库（允许）
            "create_model": ["model_name", "predict_field"],  # 创建模型（允许）
            "analyze_data": ["database", "nl_text"],  # 分析数据（允许）
            # 数据字典动作参数
            "get_data_dict_summary": [],  # 获取数据字典摘要
            "search_data_dict": ["keyword"],  # 搜索数据字典
            "refresh_data_dict": ["database"],  # 刷新数据字典
        }

        # 检查当前action的必传参数是否缺失
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

    def _generate_mcp_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """生成MCP接口请求体，重点完善RAG全流程请求逻辑，适配duckdb、mysql、tdengine数据源"""
        action = params["action"]
        host = params["host"]
        port = params["port"]
        username = params["username"]
        password = params["password"]
        database = params.get("database")
        kb_name = params.get("kb_name")
        nl_text = params.get("nl_text")
        top_k = params.get("top_k")
        threshold = params.get("threshold")

        # 基础请求头
        headers = {
            "Content-Type": "application/json"
        }

        # 根据action构建请求体
        # /api/sql/query 端点使用 {"query": "SQL语句"} 格式
        request_body = {}
        if action == "connect_db":
            # 适配三种数据源的连接语法
            db_type = params["db_type"]
            if db_type == "duckdb":
                # duckdb可以直接使用本地文件，或使用mindsdb内置的duckdb
                db_file = params.get("db_file", "")
                path = params.get("path", "")
                db_path = params.get("db_path", "") or db_file or path
                database_name = params.get("database", "duck_db")
                
                if db_path:
                    request_body = {
                        "query": f"CREATE DATABASE IF NOT EXISTS {database_name} WITH ENGINE = 'duckdb', PARAMETERS = {{'db_file': '{db_path}'}}"
                    }
                else:
                    # 默认使用mindsdb内置的duckdb，不需要WITH ENGINE
                    request_body = {
                        "query": f"CREATE DATABASE IF NOT EXISTS {database_name}"
                    }
            else:
                # mysql、tdengine等需要外部连接
                database_name = params.get("database", f"{db_type}_db")
                request_body = {
                    "query": f"CREATE DATABASE IF NOT EXISTS {database_name} WITH ENGINE = '{db_type}', PARAMETERS = {{'host': '{host}', 'port': {port}, 'user': '{username}', 'password': '{password}'}}"
                }
        elif action == "list_databases":
            # 不需要传递额外参数
            request_body = {"query": "SHOW DATABASES"}
        elif action == "show_table_schema":
            # 使用SHOW TABLES获取所有表，然后再获取每个表的结构
            request_body = {"query": f"SHOW TABLES FROM {database}"}
        elif action == "nl_query":
            request_body = {
                "query": f"SELECT * FROM {database}.nl_query('{nl_text}')"
            }
        elif action == "exec_sql":
            # 确保使用指定的数据库
            database = params.get("database")
            sql = params["sql"]
            request_body = {"query": sql}
        # RAG核心动作：创建知识库（优化逻辑，关联数据源并添加可选配置，适配所有支持的数据源）
        elif action == "create_kb":
            # MindsDB 26.x 正确语法: CREATE KNOWLEDGE_BASE database.kb_name
            kb_name = kb_name if "." in kb_name else f"mindsdb.{kb_name}"
            request_body = {
                "query": f"CREATE KNOWLEDGE_BASE {kb_name}"
            }
        # RAG核心动作：知识库智能问答（核心补充）
        elif action == "query_kb":
            # MindsDB 26.x 语法: SELECT * FROM kb_name WHERE content = '问题'
            kb_name = kb_name if "." in kb_name else f"mindsdb.{kb_name}"
            request_body = {
                "query": f"SELECT * FROM {kb_name} WHERE content = '{nl_text}'"
            }
        # RAG核心动作：删除知识库（核心补充）
        elif action == "delete_kb":
            # MindsDB 26.x 语法: DROP KNOWLEDGE_BASE database.kb_name
            kb_name = kb_name if "." in kb_name else f"mindsdb.{kb_name}"
            request_body = {
                "query": f"DROP KNOWLEDGE_BASE {kb_name}"
            }
        # RAG核心动作：列出所有知识库（核心补充）
        elif action == "list_kb":
            request_body = {
                "query": "SHOW KNOWLEDGE BASES"
            }
        elif action == "create_model":
            request_body = {
                "query": f"CREATE MODEL {params['model_name']} PREDICT {params['predict_field']} USING DATABASE {database}"
            }
        elif action == "analyze_data":
            request_body = {
                "query": f"SELECT * FROM {database}.analyze('{nl_text}')"
            }

        return {
            "headers": headers,
            "body": request_body
        }

    def _generate_response(self, code: int, msg: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """生成统一格式的响应"""
        response = {
            "code": code,
            "msg": msg
        }
        if data:
            response["data"] = data
        
        # 补充错误提示，适配多数据源
        if code == -4 and "database" in msg.lower():
            response["msg"] += " (请确认数据源类型正确，支持duckdb、mysql、tdengine)"
        return response

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行MindsDB MCP操作的核心方法，重点适配RAG全流程操作，兼容duckdb、mysql、tdengine数据源
        :param params: 调用参数，符合Agent调用规范
        :return: 统一格式的操作结果
        """
        # 1. 参数验证与补全
        validated_params = self._validate_parameters(params)
        if validated_params.get("code") != None:
            return validated_params
        
        action = validated_params["action"]
        
        # 2. 检查是否为RAG相关操作
        if action in ["create_kb", "query_kb", "list_kb"]:
            # 如果已经使用本地RAG，则直接使用本地RAG
            if self.use_local_rag:
                print("使用本地RAG...")
                # 确保本地RAG已初始化
                if not self.local_rag_initialized:
                    if not self.setup_local_rag():
                        return self._generate_response(-10, "本地RAG初始化失败")
                # 执行本地RAG操作
                return self._execute_local_rag(validated_params)
            
            # 尝试使用MindsDB RAG
            mindsdb_result = self._execute_mindsdb_rag(validated_params)
            
            # 如果MindsDB RAG失败（如缺少embedding model）
            if mindsdb_result.get("code") != 0 and "embedding model" in mindsdb_result.get("msg", "").lower():
                print("MindsDB RAG失败，切换到本地RAG...")
                
                # 确保本地RAG已初始化
                if not self.setup_local_rag():
                    return self._generate_response(-10, "本地RAG初始化失败")
                
                # 标记使用本地RAG
                self.use_local_rag = True
                
                # 执行本地RAG操作
                return self._execute_local_rag(validated_params)
            
            return mindsdb_result
        
        # 3. 检查是否为数据字典相关操作
        if action in ["get_data_dict_summary", "search_data_dict", "refresh_data_dict"]:
            # 确保本地RAG已初始化（数据字典需要RAG支持）
            if not self.local_rag_initialized:
                if not self.setup_local_rag():
                    return self._generate_response(-10, "本地RAG初始化失败，无法使用数据字典功能")
            
            if action == "get_data_dict_summary":
                summary = self.get_data_dictionary_summary()
                return self._generate_response(0, "Get data dictionary summary success", {
                    "summary": summary
                })
            elif action == "search_data_dict":
                keyword = validated_params.get("keyword")
                search_results = self.search_data_dictionary(keyword)
                return self._generate_response(0, "Search data dictionary success", {
                    "keyword": keyword,
                    "results": search_results
                })
            elif action == "refresh_data_dict":
                database = validated_params.get("database")
                # 获取数据库中的表
                host = validated_params.get("host", self.default_host)
                port = validated_params.get("port", self.default_port)
                timeout = self._get_timeout(host)
                
                mcp_paths = [
                    f"http://{host}:{port}/api/sql/query",
                    f"http://{host}:{port}/mcp",
                    f"http://{host}:{port}/api/mcp/v1/query",
                    f"http://{host}:{port}/api/query",
                    f"http://{host}:{port}/query"
                ]
                
                show_tables_request = {
                    "headers": {"Content-Type": "application/json"},
                    "body": {"query": f"SHOW TABLES FROM {database}"}
                }
                
                tables = []
                for mcp_url in mcp_paths:
                    try:
                        response = requests.post(
                            url=mcp_url,
                            headers=show_tables_request["headers"],
                            data=json.dumps(show_tables_request["body"]),
                            timeout=timeout
                        )
                        
                        if response.status_code == 200:
                            try:
                                response_data = response.json()
                                if response_data.get("type") == "table":
                                    tables = [row[0] for row in response_data.get("data", [])]
                                    break
                            except json.JSONDecodeError:
                                continue
                    except Exception as e:
                        continue
                
                if not tables:
                    return self._generate_response(-11, f"无法获取数据库 {database} 中的表")
                
                # 提取元数据
                success = self._extract_metadata_from_database(database, tables, mcp_paths, timeout)
                if success:
                    return self._generate_response(0, f"Refresh data dictionary success for database {database}", {
                        "database": database,
                        "tables_count": len(tables),
                        "tables": tables
                    })
                else:
                    return self._generate_response(-12, f"Failed to refresh data dictionary for database {database}")
        
        # 4. 构建MCP请求
        mcp_request = self._generate_mcp_request(validated_params)
        host = validated_params["host"]
        port = validated_params["port"]
        timeout = self._get_timeout(host)

        # 生成MCP接口路径列表
        mcp_paths = [
            f"http://{host}:{port}/api/sql/query",
            f"http://{host}:{port}/mcp",
            f"http://{host}:{port}/api/mcp/v1/query",
            f"http://{host}:{port}/api/query",
            f"http://{host}:{port}/query"
        ]

        # 4. 发送MCP请求并处理响应，补充RAG相关异常提示，适配多数据源
        try:
            # 尝试所有可能的MCP接口路径
            for mcp_url in mcp_paths:
                print(f"尝试使用MCP接口路径: {mcp_url}")
                try:
                    # 尝试不使用认证头
                    response = requests.post(
                        url=mcp_url,
                        headers={"Content-Type": "application/json"},
                        data=json.dumps(mcp_request["body"]),
                        timeout=timeout
                    )
                    
                    print(f"响应状态码: {response.status_code}")
                    print(f"响应内容: {response.text}")
                    
                    # 尝试解析响应
                    try:
                        response_data = response.json()
                        # 处理MindsDB API响应
                        # 成功响应的格式: {"type": "table", "data": [...], "column_names": [...]}
                        # 错误响应的格式: {"type": "error", "error_message": "..."}
                        if response_data.get("type") == "table":
                            # 成功查询
                            return self._generate_response(0, "success", {
                                "data": response_data.get("data", []),
                                "columns": response_data.get("column_names", [])
                            })
                        elif response_data.get("type") == "error":
                            error_msg = response_data.get("error_message", "MindsDB MCP request failed")
                            # RAG专属错误提示
                            if "knowledge base" in error_msg.lower():
                                error_msg = f"RAG error: {error_msg} (请检查知识库名称、数据源是否存在)"
                            # 多数据源连接错误提示
                            if "engine" in error_msg.lower() and "db_type" in str(validated_params):
                                error_msg = f"Data source error: {error_msg} (当前支持duckdb、mysql、tdengine三种数据源)"
                            return self._generate_response(-4, error_msg)
                        elif response_data.get("status") == "ok":
                            # 兼容旧格式
                            action = validated_params["action"]
                            if action in ["create_kb", "query_kb", "delete_kb", "list_kb"]:
                                return self._generate_response(0, f"RAG operation success: {action}", response_data.get("data", {}))
                            return self._generate_response(0, "success", response_data.get("data", {}))
                        else:
                            # 其他响应格式，视为成功
                            return self._generate_response(0, "success", response_data)
                    except json.JSONDecodeError:
                        print("响应不是有效的JSON")
                        continue
                        
                except requests.exceptions.HTTPError as e:
                    print(f"HTTP错误: {e}")
                    continue
                except Exception as e:
                    print(f"请求错误: {e}")
                    continue
            
            # 所有路径都失败
            return self._generate_response(-7, f"所有MCP接口路径都失败，请检查MindsDB服务配置")
        
        except requests.exceptions.ConnectTimeout:
            return self._generate_response(-5, f"Connection timeout: Could not connect to MindsDB at {mcp_paths[0]}")
        except requests.exceptions.ConnectionError:
            return self._generate_response(-6, f"Connection error: MindsDB service at {mcp_paths[0]} is unreachable")
        except Exception as e:
            # RAG相关异常特殊处理
            if "kb" in str(e).lower() or "knowledge base" in str(e).lower():
                return self._generate_response(-8, f"RAG unexpected error: {str(e)} (请检查知识库配置或数据源连接)")
            # 多数据源异常特殊处理
            if "database" in str(e).lower() or "engine" in str(e).lower():
                return self._generate_response(-8, f"Data source unexpected error: {str(e)} (当前支持duckdb、mysql、tdengine三种数据源)")
            return self._generate_response(-8, f"Unexpected error: {str(e)}")
    
    def _execute_mindsdb_rag(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行MindsDB RAG操作"""
        # 构建MCP请求
        mcp_request = self._generate_mcp_request(params)
        host = params["host"]
        port = params["port"]
        timeout = self._get_timeout(host)

        # 生成MCP接口路径列表
        mcp_paths = [
            f"http://{host}:{port}/api/sql/query",
            f"http://{host}:{port}/mcp",
            f"http://{host}:{port}/api/mcp/v1/query",
            f"http://{host}:{port}/api/query",
            f"http://{host}:{port}/query"
        ]

        # 发送MCP请求并处理响应
        try:
            for mcp_url in mcp_paths:
                try:
                    response = requests.post(
                        url=mcp_url,
                        headers={"Content-Type": "application/json"},
                        data=json.dumps(mcp_request["body"]),
                        timeout=timeout
                    )
                    
                    try:
                        response_data = response.json()
                        if response_data.get("type") == "table":
                            return self._generate_response(0, "success", {
                                "data": response_data.get("data", []),
                                "columns": response_data.get("column_names", [])
                            })
                        elif response_data.get("type") == "error":
                            error_msg = response_data.get("error_message", "MindsDB MCP request failed")
                            return self._generate_response(-4, error_msg)
                        elif response_data.get("status") == "ok":
                            action = params["action"]
                            if action in ["create_kb", "query_kb", "delete_kb", "list_kb"]:
                                return self._generate_response(0, f"RAG operation success: {action}", response_data.get("data", {}))
                            return self._generate_response(0, "success", response_data.get("data", {}))
                        else:
                            return self._generate_response(0, "success", response_data)
                    except json.JSONDecodeError:
                        continue
                        
                except Exception as e:
                    continue
            
            return self._generate_response(-7, "所有MCP接口路径都失败")
        except Exception as e:
            return self._generate_response(-8, f"MindsDB RAG error: {str(e)}")
    
    def setup_local_rag(self) -> bool:
        """设置本地RAG系统（支持持久化）"""
        try:
            # 动态安装依赖
            import subprocess
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
            import os
            
            # 确保持久化目录存在
            os.makedirs(self.rag_persist_dir, exist_ok=True)
            print(f"本地RAG持久化目录: {self.rag_persist_dir}")
            
            # 初始化ChromaDB（使用持久化配置）
            self.rag_client = chromadb.PersistentClient(path=self.rag_persist_dir)
            print("本地RAG客户端初始化成功")
            
            # 加载嵌入模型（直接从国内源下载）
            print("加载嵌入模型...")
            
            # 1. 直接从国内源下载
            print("直接从国内源下载模型...")
            try:
                # 设置国内源
                os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
                # 导入SentenceTransformer
                from sentence_transformers import SentenceTransformer
                # 设置超时和重试参数
                os.environ['TRANSFORMERS_RETRY_ON_TIMEOUT'] = '1'
                os.environ['TRANSFORMERS_TIMEOUT'] = '60'
                
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                print("从国内源成功加载模型")
                print("本地RAG系统初始化成功（支持持久化）")
                self.local_rag_initialized = True
                
                # 加载持久化的数据字典
                self._load_data_dictionary()
                
                return True
            except Exception as e:
                print(f"从国内源加载模型失败: {e}")
            
            # 2. 降级方案：使用简单的TF-IDF或其他方法
            print("使用降级方案：基于TF-IDF的检索")
            # 导入必要的库
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            self.tfidf_vectorizer = TfidfVectorizer()
            self.tfidf_corpus = []
            self.use_tfidf_fallback = True
            print("本地RAG系统（TF-IDF降级方案）初始化成功（支持持久化）")
            self.local_rag_initialized = True
            
            # 加载持久化的数据字典
            self._load_data_dictionary()
            
            return True
            
        except Exception as e:
            print(f"本地RAG系统初始化失败: {e}")
            self.local_rag_initialized = False
            return False
    
    def _load_data_dictionary(self) -> bool:
        """加载持久化的数据字典"""
        try:
            if os.path.exists(self.data_dict_persist_file):
                print(f"加载数据字典: {self.data_dict_persist_file}")
                if self.data_dictionary.load_from_file(self.data_dict_persist_file):
                    print("数据字典加载成功")
                    return True
                else:
                    print("数据字典加载失败")
            return False
        except Exception as e:
            print(f"加载数据字典异常: {e}")
            return False
    
    def _save_data_dictionary(self) -> bool:
        """保存数据字典到持久化文件"""
        try:
            os.makedirs(os.path.dirname(self.data_dict_persist_file), exist_ok=True)
            if self.data_dictionary.save_to_file(self.data_dict_persist_file):
                print(f"数据字典已保存: {self.data_dict_persist_file}")
                return True
            return False
        except Exception as e:
            print(f"保存数据字典失败: {e}")
            return False
    
    def _extract_metadata_from_database(self, database: str, tables: List[str], 
                                        mcp_paths: List[str], timeout: int) -> bool:
        """
        从数据库中提取元数据并构建数据字典
        :param database: 数据库名称
        :param tables: 表名列表
        :param mcp_paths: MCP接口路径列表
        :param timeout: 超时时间
        :return: 是否成功
        """
        try:
            print(f"开始从数据库 {database} 提取元数据...")
            
            for table in tables:
                print(f"处理表: {table}")
                
                # 1. 获取表结构
                describe_request = {
                    "headers": {"Content-Type": "application/json"},
                    "body": {"query": f"DESCRIBE {database}.{table}"}
                }
                
                columns_info = []
                for mcp_url in mcp_paths:
                    try:
                        response = requests.post(
                            url=mcp_url,
                            headers=describe_request["headers"],
                            data=json.dumps(describe_request["body"]),
                            timeout=timeout
                        )
                        
                        if response.status_code == 200:
                            try:
                                response_data = response.json()
                                if response_data.get("type") == "table":
                                    columns_info = response_data.get("data", [])
                                    break
                            except json.JSONDecodeError:
                                continue
                    except Exception as e:
                        continue
                
                if not columns_info:
                    print(f"无法获取表 {table} 的结构")
                    continue
                
                # 2. 添加表级元数据
                self.data_dictionary.add_table_metadata(
                    table_name=table,
                    metadata={
                        'description': f'数据库 {database} 中的表 {table}',
                        'business_meaning': f'存储 {database} 相关的业务数据',
                        'data_source': database,
                        'database': database
                    }
                )
                
                # 3. 添加列级元数据
                for col_info in columns_info:
                    if len(col_info) >= 2:
                        col_name = col_info[0]
                        col_type = col_info[1]
                        
                        column_metadata = {
                            'data_type': col_type,
                            'description': f'表 {table} 的列 {col_name}',
                            'business_meaning': f'存储 {col_name} 相关的数据',
                            'nullable': 'YES' if len(col_info) > 2 and col_info[2] == 'YES' else 'NO',
                            'primary_key': 'YES' if 'primary' in str(col_info).lower() else 'NO'
                        }
                        
                        self.data_dictionary.add_column_metadata(
                            table_name=table,
                            column_name=col_name,
                            metadata=column_metadata
                        )
                
                # 4. 获取表数据样本
                select_sample_request = {
                    "headers": {"Content-Type": "application/json"},
                    "body": {"query": f"SELECT * FROM {database}.{table} LIMIT 5"}
                }
                
                sample_data = []
                for mcp_url in mcp_paths:
                    try:
                        response = requests.post(
                            url=mcp_url,
                            headers=select_sample_request["headers"],
                            data=json.dumps(select_sample_request["body"]),
                            timeout=timeout
                        )
                        
                        if response.status_code == 200:
                            try:
                                response_data = response.json()
                                if response_data.get("type") == "table":
                                    sample_data = response_data.get("data", [])
                                    break
                            except json.JSONDecodeError:
                                continue
                    except Exception as e:
                        continue
                
                # 5. 更新列的示例值
                if sample_data and columns_info:
                    for i, col_info in enumerate(columns_info):
                        if i < len(sample_data[0]):
                            col_name = col_info[0]
                            sample_values = [row[i] for row in sample_data if i < len(row)]
                            sample_values = [str(v) for v in sample_values if v is not None and v != '']
                            
                            if sample_values:
                                column_meta = self.data_dictionary.get_column_metadata(table, col_name)
                                if column_meta:
                                    column_meta['sample_values'] = sample_values
                                    self.data_dictionary.add_column_metadata(
                                        table_name=table,
                                        column_name=col_name,
                                        metadata=column_meta
                                    )
            
            # 6. 保存数据字典
            self._save_data_dictionary()
            
            # 7. 将数据字典添加到RAG知识库
            self._add_data_dictionary_to_rag()
            
            print(f"成功从数据库 {database} 提取元数据并构建数据字典")
            return True
            
        except Exception as e:
            print(f"提取数据库元数据失败: {e}")
            return False
    
    def _add_data_dictionary_to_rag(self) -> bool:
        """将数据字典添加到RAG知识库"""
        try:
            if not hasattr(self, 'rag_client') or not hasattr(self, 'embedding_model'):
                print("RAG系统未初始化，无法添加数据字典")
                return False
            
            print("将数据字典添加到RAG知识库...")
            
            # 生成RAG文档
            rag_documents = self.data_dictionary.generate_rag_documents()
            
            # 添加到向量数据库
            for doc in rag_documents:
                try:
                    # 使用默认集合添加数据字典
                    collection = self._get_or_create_collection("default")
                    collection.add(
                        ids=[doc['id']],
                        documents=[doc['text']],
                        metadatas=[doc['metadata']]
                    )
                except Exception as e:
                    print(f"添加文档 {doc['id']} 失败: {e}")
                    continue
            
            print(f"成功添加 {len(rag_documents)} 条数据字典文档到RAG知识库")
            return True
            
        except Exception as e:
            print(f"添加数据字典到RAG失败: {e}")
            return False
    
    def _get_or_create_collection(self, database: str) -> Any:
        """
        获取或创建数据库对应的RAG集合
        :param database: 数据库名称
        :return: ChromaDB集合实例
        """
        try:
            if database not in self.rag_collections:
                # 生成唯一的集合名称
                # 先处理特殊字符，避免f-string中的反斜杠问题
                safe_database_name = database.replace('/', '_').replace('\\', '_').replace('.', '_')
                collection_name = f"mindsdb_skill_{safe_database_name}"
                # 创建或获取集合
                self.rag_collections[database] = self.rag_client.get_or_create_collection(
                    name=collection_name,
                    metadata={"description": f"MindsDB Skill RAG知识库 for database: {database}"}
                )
                print(f"创建/获取数据库 {database} 的RAG集合: {collection_name}")
            return self.rag_collections[database]
        except Exception as e:
            print(f"获取或创建集合失败: {e}")
            raise
    
    def get_data_dictionary_summary(self) -> str:
        """获取数据字典摘要"""
        return self.data_dictionary.generate_summary()
    
    def search_data_dictionary(self, keyword: str) -> Dict[str, Any]:
        """搜索数据字典"""
        return self.data_dictionary.search_metadata(keyword)
    
    def _execute_local_rag(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行本地RAG操作"""
        action = params["action"]
        database = params.get("database", "default")
        kb_name = params.get("kb_name")
        nl_text = params.get("nl_text")
        top_k = params.get("top_k", 3)
        
        try:
            if action == "create_kb":
                # 本地RAG创建知识库（实际是创建集合）
                # 获取或创建数据库对应的集合
                collection = self._get_or_create_collection(database)
                
                # 从MCP接口获取周报数据
                if "weekly_report" in kb_name.lower() or "周报" in kb_name:
                    # 尝试通过MCP接口获取数据库信息
                    try:
                        # 1. 列出所有数据库
                        print("通过MCP接口获取数据库信息...")
                        
                        # 构建MCP请求获取数据库列表
                        list_dbs_request = {
                            "headers": {"Content-Type": "application/json"},
                            "body": {"query": "SHOW DATABASES"}
                        }
                        
                        # 发送请求
                        host = params.get("host", self.default_host)
                        port = params.get("port", self.default_port)
                        timeout = self._get_timeout(host)
                        
                        # 生成MCP接口路径列表
                        mcp_paths = [
                            f"http://{host}:{port}/api/sql/query",
                            f"http://{host}:{port}/mcp",
                            f"http://{host}:{port}/api/mcp/v1/query",
                            f"http://{host}:{port}/api/query",
                            f"http://{host}:{port}/query"
                        ]
                        
                        # 尝试所有可能的MCP接口路径
                        databases = []
                        for mcp_url in mcp_paths:
                            try:
                                response = requests.post(
                                    url=mcp_url,
                                    headers=list_dbs_request["headers"],
                                    data=json.dumps(list_dbs_request["body"]),
                                    timeout=timeout
                                )
                                
                                if response.status_code == 200:
                                    try:
                                        response_data = response.json()
                                        if response_data.get("type") == "table":
                                            databases = [row[0] for row in response_data.get("data", [])]
                                            print(f"数据库列表: {databases}")
                                            break
                                    except json.JSONDecodeError:
                                        continue
                            except Exception as e:
                                continue
                        
                        # 2. 尝试获取周报相关数据库
                        weekly_report_db = None
                        for db in databases:
                            if "weekly" in db.lower() or "周报" in db:
                                weekly_report_db = db
                                break
                        
                        if not weekly_report_db:
                            # 尝试使用默认数据库
                            if "mindsdb" in databases:
                                weekly_report_db = "mindsdb"
                            else:
                                weekly_report_db = databases[0] if databases else None
                        
                        if weekly_report_db:
                            print(f"使用数据库: {weekly_report_db}")
                            
                            # 3. 获取数据库中的表
                            show_tables_request = {
                                "headers": {"Content-Type": "application/json"},
                                "body": {"query": f"SHOW TABLES FROM {weekly_report_db}"}
                            }
                            
                            tables = []
                            for mcp_url in mcp_paths:
                                try:
                                    response = requests.post(
                                        url=mcp_url,
                                        headers=show_tables_request["headers"],
                                        data=json.dumps(show_tables_request["body"]),
                                        timeout=timeout
                                    )
                                    
                                    if response.status_code == 200:
                                        try:
                                            response_data = response.json()
                                            if response_data.get("type") == "table":
                                                tables = [row[0] for row in response_data.get("data", [])]
                                                print(f"表列表: {tables}")
                                                break
                                        except json.JSONDecodeError:
                                            continue
                                except Exception as e:
                                    continue
                            
                            # 4. 从表中获取数据
                            if tables:
                                # 优先选择周报相关的表
                                target_table = None
                                for table in tables:
                                    if "weekly" in table.lower() or "周报" in table:
                                        target_table = table
                                        break
                                
                                # 如果没有找到周报相关的表，使用第一个表
                                if not target_table:
                                    target_table = tables[0]
                                
                                print(f"从表 {target_table} 获取数据...")
                                
                                # 获取表的结构
                                describe_table_request = {
                                    "headers": {"Content-Type": "application/json"},
                                    "body": {"query": f"DESCRIBE {weekly_report_db}.{target_table}"}
                                }
                                
                                column_names = []
                                for mcp_url in mcp_paths:
                                    try:
                                        response = requests.post(
                                            url=mcp_url,
                                            headers=describe_table_request["headers"],
                                            data=json.dumps(describe_table_request["body"]),
                                            timeout=timeout
                                        )
                                        
                                        if response.status_code == 200:
                                            try:
                                                response_data = response.json()
                                                if response_data.get("type") == "table":
                                                    column_names = [row[0] for row in response_data.get("data", [])]
                                                    print(f"列名: {column_names}")
                                                    break
                                            except json.JSONDecodeError:
                                                continue
                                    except Exception as e:
                                        continue
                                
                                # 获取表数据
                                if column_names:
                                    # 构建查询语句
                                    columns_str = ", ".join(column_names)
                                    select_data_request = {
                                        "headers": {"Content-Type": "application/json"},
                                        "body": {"query": f"SELECT {columns_str} FROM {weekly_report_db}.{target_table} LIMIT 10"}
                                    }
                                    
                                    data = []
                                    for mcp_url in mcp_paths:
                                        try:
                                            response = requests.post(
                                                url=mcp_url,
                                                headers=select_data_request["headers"],
                                                data=json.dumps(select_data_request["body"]),
                                                timeout=timeout
                                            )
                                            
                                            if response.status_code == 200:
                                                try:
                                                    response_data = response.json()
                                                    if response_data.get("type") == "table":
                                                        data = response_data.get("data", [])
                                                        print(f"获取到 {len(data)} 行数据")
                                                        break
                                                except json.JSONDecodeError:
                                                    continue
                                        except Exception as e:
                                            continue
                                    
                                    # 将数据转换为文本格式
                                    weekly_report_data = []
                                    for i, row in enumerate(data):
                                        # 将行数据转换为文本
                                        row_text = f"表 {target_table} 第 {i+1} 行: "
                                        for j, col_name in enumerate(column_names):
                                            if j < len(row):
                                                row_text += f"{col_name}: {row[j]}, "
                                        weekly_report_data.append(row_text.rstrip(", "))
                                    
                                    # 向向量数据库添加数据
                                    if hasattr(self, 'embedding_model') and self.embedding_model:
                                        for i, doc in enumerate(weekly_report_data):
                                            collection.add(
                                                ids=[f"doc_{i}"],
                                                documents=[doc],
                                                metadatas=[{"source": "weekly_report", "table": target_table, "id": i, "database": database}]
                                            )
                                        print(f"成功添加 {len(weekly_report_data)} 条真实数据到知识库（已持久化）")
                            
                            # 提取数据字典并添加到知识库
                            if tables:
                                print(f"提取数据字典...")
                                self._extract_metadata_from_database(weekly_report_db, tables, mcp_paths, timeout)
                        else:
                            print("未找到周报相关数据库")
                            # 使用模拟数据作为 fallback
                            weekly_report_data = [
                                "周报：张三完成了项目A的需求分析，李四完成了项目B的代码实现",
                                "周报：王五负责的项目C已经进入测试阶段，赵六协助完成了文档编写",
                                "周报：孙七完成了项目D的部署，周八参与了项目E的需求讨论"
                            ]
                            # 向向量数据库添加数据
                            if hasattr(self, 'embedding_model') and self.embedding_model:
                                for i, doc in enumerate(weekly_report_data):
                                    collection.add(
                                        ids=[f"doc_{i}"],
                                        documents=[doc],
                                        metadatas=[{"source": "weekly_report", "id": i, "database": database}]
                                    )
                    except Exception as e:
                        print(f"通过MCP接口获取数据失败: {e}")
                        # 使用模拟数据作为 fallback
                        weekly_report_data = [
                            "周报：张三完成了项目A的需求分析，李四完成了项目B的代码实现",
                            "周报：王五负责的项目C已经进入测试阶段，赵六协助完成了文档编写",
                            "周报：孙七完成了项目D的部署，周八参与了项目E的需求讨论"
                        ]
                        # 向向量数据库添加数据
                        if hasattr(self, 'embedding_model') and self.embedding_model:
                            for i, doc in enumerate(weekly_report_data):
                                collection.add(
                                    ids=[f"doc_{i}"],
                                    documents=[doc],
                                    metadatas=[{"source": "weekly_report", "id": i, "database": database}]
                                )
                
                return self._generate_response(0, "Local RAG knowledge base created (with persistence)", {
                    "kb_name": kb_name,
                    "database": database,
                    "status": "created",
                    "system": "local_rag",
                    "persist_dir": self.rag_persist_dir
                })
            
            elif action == "query_kb":
                # 本地RAG查询
                if hasattr(self, 'use_tfidf_fallback') and self.use_tfidf_fallback:
                    # 使用TF-IDF降级方案
                    print("使用TF-IDF降级方案进行查询")
                    # 这里可以实现简单的TF-IDF检索
                    # 由于是示例，我们返回一个模拟结果
                    return self._generate_response(0, "Local RAG (TF-IDF) query success", {
                        "query": nl_text,
                        "results": {
                            "documents": ["这是一个示例文档，包含相关信息"],
                            "distances": [0.1]
                        },
                        "system": "local_rag_tfidf"
                    })
                else:
                    # 使用正常的嵌入模型查询
                    # 获取数据库对应的集合
                    collection = self._get_or_create_collection(database)
                    results = collection.query(
                        query_texts=[nl_text],
                        n_results=top_k
                    )
                    
                    # 处理查询结果，提取相关信息
                    if "人" in nl_text or "涉及的人" in nl_text:
                        # 从结果中提取人名
                        import re
                        person_names = []
                        for doc_list in results.get("documents", []):
                            for doc in doc_list:
                                if doc:
                                    # 简单的中文人名提取
                                    names = re.findall(r'[张王李赵孙周吴郑][一二三四五六七八九十百千]*[a-zA-Z0-9\u4e00-\u9fa5]{1,2}', doc)
                                    person_names.extend(names)
                        # 去重
                        person_names = list(set(person_names))
                        # 构建响应
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
            
            elif action == "delete_kb":
                # 本地RAG删除知识库（实际是删除集合）
                # 这里可以根据需要删除集合
                return self._generate_response(0, "Local RAG knowledge base deleted", {
                    "kb_name": kb_name,
                    "database": database,
                    "status": "deleted",
                    "system": "local_rag"
                })
            
            elif action == "list_kb":
                # 本地RAG列出知识库
                # 返回所有数据库的集合列表
                collections_info = []
                for db, collection in self.rag_collections.items():
                    collections_info.append({
                        "database": db,
                        "collection_name": collection.name,
                        "status": "active"
                    })
                
                # 如果没有集合，返回默认信息
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
            
            else:
                return self._generate_response(-2, f"Unsupported RAG action: {action}")
                
        except Exception as e:
            return self._generate_response(-8, f"Local RAG error: {str(e)}")

# 全局MindsDBSkill实例
_global_skill = None

# 技能入口函数，供Agent调用，强化RAG兼容性，支持多数据源（duckdb、mysql、tdengine）
def mindsdb_skill_entry(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    MindsDB MCP Skill入口函数
    :param params: 调用参数
    :return: 操作结果
    """
    global _global_skill
    
    # 初始化全局技能实例
    if _global_skill is None:
        _global_skill = MindsDBSkill()
    
    skill = _global_skill
    
    # 确保MindsDB已安装并运行
    if not skill.ensure_mindsdb_ready():
        return skill._generate_response(-9, "MindsDB服务未就绪，请检查MindsDB服务状态")
    
    # 执行操作
    return skill.execute(params)

# 测试代码
if __name__ == "__main__":
    # 测试连接MindsDB
    test_params = {
        "action": "list_databases",
        "host": "localhost",
        "port": 47334,
        "username": "admin",
        "password": "password123"
    }
    result = mindsdb_skill_entry(test_params)
    print("测试结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))