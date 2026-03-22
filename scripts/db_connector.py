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
    
    def connect_database(self, db_type: str, **kwargs) -> Dict[str, Any]:
        """连接数据库"""
        host = kwargs.get("host", self.default_host)
        port = kwargs.get("port", self.default_port)
        username = kwargs.get("username", self.default_username)
        password = kwargs.get("password", self.default_password)
        database_name = kwargs.get("database", f"{db_type}_db")
        
        if db_type == "duckdb":
            db_path = kwargs.get("db_path", "") or kwargs.get("db_file", "")
            if db_path:
                # 尝试不同的参数名
                query = f"CREATE DATABASE IF NOT EXISTS {database_name} WITH ENGINE = 'duckdb', PARAMETERS = {{'database': '{db_path}'}}"
            else:
                query = f"CREATE DATABASE IF NOT EXISTS {database_name}"
        else:
            query = f"CREATE DATABASE IF NOT EXISTS {database_name} WITH ENGINE = '{db_type}', PARAMETERS = {{'host': '{host}', 'port': {port}, 'user': '{username}', 'password': '{password}'}}"
        
        result = self.send_mcp_request(query, host, port)
        
        if result.get("code") == 0:
            # 缓存连接信息
            self.connected_databases[database_name] = {
                "db_type": db_type,
                "host": host,
                "port": port,
                "connected_at": time.time()
            }
        
        return result
    
    def list_databases(self, host: str = None, port: int = None) -> Dict[str, Any]:
        """列出所有数据库"""
        return self.send_mcp_request("SHOW DATABASES", host, port)
    
    def show_tables(self, database: str, host: str = None, port: int = None) -> Dict[str, Any]:
        """显示指定数据库的表"""
        return self.send_mcp_request(f"SHOW TABLES FROM {database}", host, port)
    
    def describe_table(self, database: str, table: str, host: str = None, port: int = None) -> Dict[str, Any]:
        """描述表结构"""
        # TDengine 使用 SHOW COLUMNS FROM 而不是 DESCRIBE
        return self.send_mcp_request(f"SHOW COLUMNS FROM {database}.{table}", host, port)
    
    def execute_sql(self, sql: str, host: str = None, port: int = None) -> Dict[str, Any]:
        """执行SQL查询"""
        return self.send_mcp_request(sql, host, port)


# 全局连接器实例
_db_connector = None

def get_db_connector() -> DBConnector:
    """获取数据库连接器实例"""
    global _db_connector
    if _db_connector is None:
        _db_connector = DBConnector()
    return _db_connector
