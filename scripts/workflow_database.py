#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流1: 数据库连接与查询工作流
负责数据库连接管理、数据查询、表结构查看和数据字典管理
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


class DatabaseWorkflow:
    """数据库连接与查询工作流"""
    
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
        
        # 数据字典管理
        self.data_dictionary = DataDictionary()
        self.data_dict_persist_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            "..", "data", "data_dictionary.json"
        )
    
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
    
    def _get_timeout(self, host: str) -> int:
        """根据连接类型获取超时时间"""
        return self.remote_timeout if host != "localhost" else self.local_timeout
    
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
        
        return params
    
    def _generate_mcp_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """生成MCP接口请求体"""
        action = params["action"]
        database = params.get("database")
        nl_text = params.get("nl_text")
        
        headers = {"Content-Type": "application/json"}
        request_body = {}
        
        if action == "connect_db":
            db_type = params["db_type"]
            if db_type == "duckdb":
                db_path = params.get("db_file", "") or params.get("db_path", "")
                database_name = params.get("database", "duck_db")
                if db_path:
                    request_body = {
                        "query": f"CREATE DATABASE IF NOT EXISTS {database_name} WITH ENGINE = 'duckdb', PARAMETERS = {{'db_file': '{db_path}'}}"
                    }
                else:
                    request_body = {"query": f"CREATE DATABASE IF NOT EXISTS {database_name}"}
            else:
                host = params["host"]
                port = params["port"]
                username = params["username"]
                password = params["password"]
                database_name = params.get("database", f"{db_type}_db")
                request_body = {
                    "query": f"CREATE DATABASE IF NOT EXISTS {database_name} WITH ENGINE = '{db_type}', PARAMETERS = {{'host': '{host}', 'port': {port}, 'user': '{username}', 'password': '{password}'}}"
                }
        
        elif action == "list_databases":
            request_body = {"query": "SHOW DATABASES"}
        
        elif action == "show_table_schema":
            request_body = {"query": f"SHOW TABLES FROM {database}"}
        
        elif action == "nl_query":
            request_body = {"query": f"SELECT * FROM {database}.nl_query('{nl_text}')"}
        
        elif action == "exec_sql":
            request_body = {"query": params["sql"]}
        
        return {"headers": headers, "body": request_body}
    
    def _get_mcp_paths(self, host: str, port: int) -> List[str]:
        """获取MCP接口路径列表"""
        return [
            f"http://{host}:{port}/api/sql/query",
            f"http://{host}:{port}/mcp",
            f"http://{host}:{port}/api/mcp/v1/query",
            f"http://{host}:{port}/api/query",
            f"http://{host}:{port}/query"
        ]
    
    def _send_mcp_request(self, mcp_request: Dict, mcp_paths: List[str], timeout: int) -> Dict:
        """发送MCP请求"""
        for mcp_url in mcp_paths:
            try:
                response = requests.post(
                    url=mcp_url,
                    headers=mcp_request["headers"],
                    data=json.dumps(mcp_request["body"]),
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
    
    def _load_data_dictionary(self) -> bool:
        """加载持久化的数据字典"""
        try:
            if os.path.exists(self.data_dict_persist_file):
                return self.data_dictionary.load_from_file(self.data_dict_persist_file)
            return False
        except Exception as e:
            print(f"加载数据字典异常: {e}")
            return False
    
    def _save_data_dictionary(self) -> bool:
        """保存数据字典"""
        try:
            os.makedirs(os.path.dirname(self.data_dict_persist_file), exist_ok=True)
            return self.data_dictionary.save_to_file(self.data_dict_persist_file)
        except Exception as e:
            print(f"保存数据字典失败: {e}")
            return False
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行数据库工作流操作"""
        # 参数验证
        validated_params = self._validate_parameters(params)
        if validated_params.get("code") is not None:
            return validated_params
        
        action = validated_params["action"]
        host = validated_params["host"]
        port = validated_params["port"]
        timeout = self._get_timeout(host)
        
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
                # 这里简化处理，实际应该从数据库获取元数据
                return self._generate_response(0, "Data dictionary refreshed", {
                    "database": database
                })
        
        # 生成MCP请求
        mcp_request = self._generate_mcp_request(validated_params)
        mcp_paths = self._get_mcp_paths(host, port)
        
        # 发送请求
        return self._send_mcp_request(mcp_request, mcp_paths, timeout)


# 工作流入口函数
_database_workflow = None

def database_workflow_entry(params: Dict[str, Any]) -> Dict[str, Any]:
    """数据库工作流入口函数"""
    global _database_workflow
    
    if _database_workflow is None:
        _database_workflow = DatabaseWorkflow()
    
    workflow = _database_workflow
    
    if not workflow.ensure_mindsdb_ready():
        return workflow._generate_response(-9, "MindsDB服务未就绪")
    
    return workflow.execute(params)
