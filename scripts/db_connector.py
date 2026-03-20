#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公共数据库连接模块
提供统一的数据库连接管理和MCP请求发送功能
"""

import os
import json
import requests
import time
import subprocess
import sys
from typing import Dict, Any, Optional, List


class DBConnector:
    """数据库连接器"""
    
    def __init__(self):
        """初始化连接器"""
        self.default_host = "localhost"
        self.default_port = 47334
        self.default_username = os.getenv("MINDSDB_USERNAME", "admin")
        self.default_password = os.getenv("MINDSDB_PASSWORD", "password123")
        self.default_timeout = 30
        self.local_timeout = 10
        self.remote_timeout = 30
        
        # 已连接的数据库缓存
        self.connected_databases = {}
    
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
    
    def _get_mcp_paths(self, host: str, port: int) -> List[str]:
        """获取MCP接口路径列表"""
        return [
            f"http://{host}:{port}/api/sql/query",
            f"http://{host}:{port}/mcp",
            f"http://{host}:{port}/api/mcp/v1/query",
            f"http://{host}:{port}/api/query",
            f"http://{host}:{port}/query"
        ]
    
    def send_mcp_request(self, query: str, host: str = None, port: int = None) -> Dict[str, Any]:
        """发送MCP请求"""
        host = host or self.default_host
        port = port or self.default_port
        timeout = self._get_timeout(host)
        mcp_paths = self._get_mcp_paths(host, port)
        
        headers = {"Content-Type": "application/json"}
        request_body = {"query": query}
        
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
                            return {
                                "code": 0,
                                "msg": "success",
                                "data": {
                                    "data": response_data.get("data", []),
                                    "columns": response_data.get("column_names", [])
                                }
                            }
                        elif response_data.get("type") == "error":
                            return {
                                "code": -4,
                                "msg": response_data.get("error_message", "Request failed")
                            }
                        else:
                            return {
                                "code": 0,
                                "msg": "success",
                                "data": response_data
                            }
                    except json.JSONDecodeError:
                        continue
            except Exception:
                continue
        
        return {"code": -7, "msg": "All MCP paths failed"}
    
    def send_http_api_request(self, query: str, host: str = None, port: int = None) -> Dict[str, Any]:
        """发送HTTP API请求"""
        host = host or self.default_host
        port = port or self.default_port
        timeout = self._get_timeout(host)
        
        # MindsDB HTTP API端点
        api_url = f"http://{host}:{port}/api/sql/query"
        
        headers = {"Content-Type": "application/json"}
        request_body = {"query": query}
        
        try:
            response = requests.post(
                url=api_url,
                headers=headers,
                json=request_body,
                timeout=timeout
            )
            
            print(f"HTTP API请求: {api_url}")
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.text[:500]}...")
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    if response_data.get("type") == "table":
                        return {
                            "code": 0,
                            "msg": "success",
                            "data": {
                                "data": response_data.get("data", []),
                                "columns": response_data.get("column_names", [])
                            }
                        }
                    elif response_data.get("type") == "error":
                        return {
                            "code": -4,
                            "msg": response_data.get("error_message", "Request failed")
                        }
                    else:
                        return {
                            "code": 0,
                            "msg": "success",
                            "data": response_data
                        }
                except json.JSONDecodeError:
                    return {"code": -5, "msg": "Invalid JSON response"}
            else:
                return {"code": -6, "msg": f"HTTP error: {response.status_code} - {response.text}"}
        except Exception as e:
            return {"code": -7, "msg": f"Request failed: {str(e)}"}
    
    def connect_database(self, db_type: str, **kwargs) -> Dict[str, Any]:
        """连接数据库"""
        # MindsDB服务器信息
        mindsdb_host = kwargs.get("mindsdb_host", self.default_host)
        mindsdb_port = kwargs.get("mindsdb_port", self.default_port)
        
        # 数据库连接信息
        db_host = kwargs.get("host", "localhost")
        db_port = kwargs.get("port", 3306)  # 默认端口设置为通用数据库端口
        username = kwargs.get("username", self.default_username)
        password = kwargs.get("password", self.default_password)
        database_name = kwargs.get("database_name", f"{db_type}_db")
        
        # 构建CREATE DATABASE语句
        if db_type == "duckdb":
            # DuckDB特殊处理
            db_path = kwargs.get("db_path", "") or kwargs.get("db_file", "")
            if db_path:
                query = f"CREATE DATABASE IF NOT EXISTS {database_name} WITH ENGINE = 'duckdb', PARAMETERS = {{'database': '{db_path}'}}"
            else:
                query = f"CREATE DATABASE IF NOT EXISTS {database_name}"
        elif db_type == "tdengine":
            # TDengine特殊处理
            url = kwargs.get("url", f"{db_host}:{db_port}")
            token = kwargs.get("token", "")
            td_database = kwargs.get("database", "")
            query = f"CREATE DATABASE IF NOT EXISTS {database_name} WITH ENGINE = 'tdengine', PARAMETERS = {{'url': '{url}', 'token': '{token}', 'database': '{td_database}', 'user': '{username}', 'password': '{password}'}}"
        elif db_type == "mysql":
            # MySQL特殊处理
            mysql_db = kwargs.get("database", "")
            query = f"CREATE DATABASE IF NOT EXISTS {database_name} WITH ENGINE = 'mysql', PARAMETERS = {{'host': '{db_host}', 'port': {db_port}, 'user': '{username}', 'password': '{password}', 'database': '{mysql_db}'}}"
        elif db_type == "postgres":
            # PostgreSQL特殊处理
            pg_db = kwargs.get("database", "")
            query = f"CREATE DATABASE IF NOT EXISTS {database_name} WITH ENGINE = 'postgres', PARAMETERS = {{'host': '{db_host}', 'port': {db_port}, 'user': '{username}', 'password': '{password}', 'database': '{pg_db}'}}"
        elif db_type == "mongodb":
            # MongoDB特殊处理
            connection_string = kwargs.get("connection_string", f"mongodb://{username}:{password}@{db_host}:{db_port}")
            query = f"CREATE DATABASE IF NOT EXISTS {database_name} WITH ENGINE = 'mongodb', PARAMETERS = {{'connection_string': '{connection_string}'}}"
        elif db_type == "clickhouse":
            # ClickHouse特殊处理
            clickhouse_db = kwargs.get("database", "default")
            query = f"CREATE DATABASE IF NOT EXISTS {database_name} WITH ENGINE = 'clickhouse', PARAMETERS = {{'host': '{db_host}', 'port': {db_port}, 'user': '{username}', 'password': '{password}', 'database': '{clickhouse_db}'}}"
        elif db_type == "snowflake":
            # Snowflake特殊处理
            account = kwargs.get("account", "")
            warehouse = kwargs.get("warehouse", "")
            snowflake_db = kwargs.get("database", "")
            schema = kwargs.get("schema", "")
            query = f"CREATE DATABASE IF NOT EXISTS {database_name} WITH ENGINE = 'snowflake', PARAMETERS = {{'account': '{account}', 'user': '{username}', 'password': '{password}', 'warehouse': '{warehouse}', 'database': '{snowflake_db}', 'schema': '{schema}'}}"
        else:
            # 通用数据库 - 支持任意MindsDB兼容的数据库引擎
            # 构建通用参数字典
            params = {
                'host': db_host,
                'port': db_port,
                'user': username,
                'password': password
            }
            
            # 添加数据库名称（如果提供）
            if kwargs.get("database"):
                params['database'] = kwargs.get("database")
            
            # 添加其他自定义参数
            custom_params = kwargs.get("params", {})
            if isinstance(custom_params, dict):
                params.update(custom_params)
            
            # 构建参数字符串
            params_str = ', '.join([f"'{k}': '{v}'" for k, v in params.items()])
            query = f"CREATE DATABASE IF NOT EXISTS {database_name} WITH ENGINE = '{db_type}', PARAMETERS = {{{params_str}}}"
        
        # 发送HTTP API请求到MindsDB服务器
        result = self.send_http_api_request(query, mindsdb_host, mindsdb_port)
        
        if result.get("code") == 0:
            # 缓存连接信息
            self.connected_databases[database_name] = {
                "db_type": db_type,
                "host": db_host,
                "port": db_port,
                "connected_at": time.time(),
                "details": kwargs
            }
            print(f"✓ 成功配置数据源: {database_name} (类型: {db_type})")
        else:
            print(f"✗ 数据源配置失败: {result.get('msg', 'Unknown error')}")
        
        return result
    
    def test_connection(self, database_name: str, host: str = None, port: int = None) -> Dict[str, Any]:
        """测试数据库连接"""
        host = host or self.default_host
        port = port or self.default_port
        
        # 测试查询
        test_sql = f"SELECT 1 FROM {database_name}.information_schema.tables LIMIT 1"
        result = self.execute_sql(test_sql, host, port)
        
        if result.get("code") == 0:
            return {
                "code": 0,
                "msg": "Connection test successful",
                "data": {"status": "connected"}
            }
        else:
            return {
                "code": -1,
                "msg": f"Connection test failed: {result.get('msg', 'Unknown error')}"
            }
    
    def get_datasource_info(self, database_name: str, host: str = None, port: int = None) -> Dict[str, Any]:
        """获取数据源信息"""
        host = host or self.default_host
        port = port or self.default_port
        
        # 查询数据源信息
        sql = f"SHOW CREATE DATABASE {database_name}"
        result = self.send_mcp_request(sql, host, port)
        
        if result.get("code") == 0:
            return result
        else:
            return {
                "code": -1,
                "msg": f"Failed to get datasource info: {result.get('msg', 'Unknown error')}"
            }
    
    def drop_database(self, database_name: str, host: str = None, port: int = None) -> Dict[str, Any]:
        """删除数据库连接"""
        host = host or self.default_host
        port = port or self.default_port
        
        query = f"DROP DATABASE IF EXISTS {database_name}"
        result = self.send_mcp_request(query, host, port)
        
        if result.get("code") == 0:
            # 从缓存中移除
            if database_name in self.connected_databases:
                del self.connected_databases[database_name]
            print(f"✓ 成功删除数据源: {database_name}")
        else:
            print(f"✗ 删除数据源失败: {result.get('msg', 'Unknown error')}")
        
        return result
    
    def list_databases(self, host: str = None, port: int = None) -> Dict[str, Any]:
        """列出所有数据库"""
        return self.send_http_api_request("SHOW DATABASES", host, port)
    
    def show_tables(self, database: str, host: str = None, port: int = None) -> Dict[str, Any]:
        """显示指定数据库的表"""
        return self.send_http_api_request(f"SHOW TABLES FROM {database}", host, port)
    
    def describe_table(self, database: str, table: str, host: str = None, port: int = None) -> Dict[str, Any]:
        """描述表结构"""
        return self.send_http_api_request(f"DESCRIBE {database}.{table}", host, port)
    
    def execute_sql(self, sql: str, host: str = None, port: int = None) -> Dict[str, Any]:
        """执行SQL查询"""
        return self.send_http_api_request(sql, host, port)


# 全局连接器实例
_db_connector = None

def get_db_connector() -> DBConnector:
    """获取数据库连接器实例"""
    global _db_connector
    if _db_connector is None:
        _db_connector = DBConnector()
    return _db_connector
