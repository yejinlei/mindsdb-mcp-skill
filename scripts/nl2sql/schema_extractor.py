#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Schema 自动提取模块
连接数据库后自动提取表结构、推断业务术语映射
实现零配置使用
"""

import os
import re
from typing import Dict, Any, List, Optional, Tuple


class SchemaExtractor:
    """Schema 自动提取器"""
    
    FIELD_TERM_PATTERNS = {
        "issues": ["卡点", "问题", "风险"],
        "problem": ["问题", "卡点"],
        "risk": ["风险", "问题"],
        "blocker": ["卡点", "阻碍"],
        "finance_type": ["资金流向", "资金类型"],
        "finance": ["财务", "资金"],
        "income": ["收入"],
        "expense": ["支出"],
        "loan": ["借款"],
        "amount": ["金额", "数额"],
        "money": ["金额", "资金"],
        "department": ["部门"],
        "dept": ["部门"],
        "leader": ["负责人", "领导"],
        "manager": ["负责人", "经理"],
        "project": ["项目"],
        "progress": ["进度"],
        "status": ["状态"],
        "name": ["名称"],
        "title": ["标题", "名称"],
        "date": ["日期"],
        "time": ["时间"],
        "user": ["用户"],
        "person": ["人员"],
        "human": ["人员", "人力"],
        "resource": ["资源"],
        "support": ["支持", "协助"],
        "request": ["请求", "需求"],
        "weekly": ["周报", "每周"],
        "report": ["报告", "报表"],
        "order": ["订单"],
        "customer": ["客户"],
        "product": ["产品", "商品"],
        "item": ["项目", "条目"],
        "type": ["类型"],
        "category": ["分类", "类别"],
        "total": ["合计", "总计"],
        "sum": ["合计", "总和"],
        "count": ["数量", "计数"],
        "id": ["ID", "编号"],
        "description": ["描述", "说明"],
        "content": ["内容"],
        "remark": ["备注", "说明"],
        "comment": ["备注", "评论"],
    }
    
    TABLE_TERM_PATTERNS = {
        "weekly_report": ["周报"],
        "report": ["报表", "报告"],
        "finance": ["财务", "资金"],
        "department": ["部门"],
        "dept": ["部门"],
        "project": ["项目"],
        "human_resource": ["人力资源", "人员"],
        "user": ["用户"],
        "order": ["订单"],
        "customer": ["客户"],
        "product": ["产品"],
        "inventory": ["库存"],
        "transaction": ["交易"],
    }
    
    def __init__(self, training_collector=None, intent_recognizer=None):
        """初始化提取器
        
        Args:
            training_collector: 训练数据收集器
            intent_recognizer: 意图识别器
        """
        self.training_collector = training_collector
        self.intent_recognizer = intent_recognizer
        self._extracted_schemas = {}
    
    def extract_from_duckdb(self, db_path: str, database: str = None) -> Dict[str, Any]:
        """从 DuckDB 数据库提取 Schema
        
        Args:
            db_path: 数据库文件路径
            database: 数据库名（可选）
        
        Returns:
            提取结果
        """
        try:
            import duckdb
        except ImportError:
            return {"status": "error", "message": "duckdb 库未安装"}
        
        if not os.path.exists(db_path):
            return {"status": "error", "message": f"数据库文件不存在: {db_path}"}
        
        database = database or os.path.basename(db_path).replace('.duckdb', '')
        
        conn = duckdb.connect(db_path, read_only=True)
        
        try:
            tables_result = conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
            ).fetchall()
            
            tables = [row[0] for row in tables_result]
            
            schema_info = {"tables": {}}
            all_columns = []
            
            for table in tables:
                columns_result = conn.execute(f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = '{table}'
                    ORDER BY ordinal_position
                """).fetchall()
                
                columns = []
                for col_name, col_type, is_nullable in columns_result:
                    columns.append({
                        "name": col_name,
                        "type": col_type,
                        "nullable": is_nullable == "YES"
                    })
                    all_columns.append((table, col_name, col_type))
                
                schema_info["tables"][table] = columns
            
            self._extracted_schemas[database] = schema_info
            
            result = {
                "status": "success",
                "database": database,
                "tables": tables,
                "schema_info": schema_info,
                "inferred_terms": {}
            }
            
            inferred_terms = self._infer_business_terms(all_columns, tables)
            result["inferred_terms"] = inferred_terms
            
            if self.training_collector:
                self._register_ddl_training_data(database, schema_info)
            
            if self.intent_recognizer and inferred_terms:
                self._register_business_terms(inferred_terms)
            
            return result
            
        finally:
            conn.close()
    
    def extract_from_sqlite(self, db_path: str, database: str = None) -> Dict[str, Any]:
        """从 SQLite 数据库提取 Schema"""
        try:
            import sqlite3
        except ImportError:
            return {"status": "error", "message": "sqlite3 库未安装"}
        
        if not os.path.exists(db_path):
            return {"status": "error", "message": f"数据库文件不存在: {db_path}"}
        
        database = database or os.path.basename(db_path).replace('.db', '').replace('.sqlite', '')
        
        conn = sqlite3.connect(db_path)
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            schema_info = {"tables": {}}
            all_columns = []
            
            for table in tables:
                cursor.execute(f"PRAGMA table_info({table})")
                columns_info = cursor.fetchall()
                
                columns = []
                for col in columns_info:
                    col_name, col_type = col[1], col[2]
                    columns.append({
                        "name": col_name,
                        "type": col_type,
                        "nullable": True
                    })
                    all_columns.append((table, col_name, col_type))
                
                schema_info["tables"][table] = columns
            
            self._extracted_schemas[database] = schema_info
            
            inferred_terms = self._infer_business_terms(all_columns, tables)
            
            if self.training_collector:
                self._register_ddl_training_data(database, schema_info)
            
            if self.intent_recognizer and inferred_terms:
                self._register_business_terms(inferred_terms)
            
            return {
                "status": "success",
                "database": database,
                "tables": tables,
                "schema_info": schema_info,
                "inferred_terms": inferred_terms
            }
            
        finally:
            conn.close()
    
    def extract_from_connection(self, connection, database: str, 
                                 db_type: str = "duckdb") -> Dict[str, Any]:
        """从已有连接提取 Schema
        
        Args:
            connection: 数据库连接对象
            database: 数据库名
            db_type: 数据库类型 (duckdb, sqlite, postgres, mysql)
        
        Returns:
            提取结果
        """
        schema_info = {"tables": {}}
        all_columns = []
        tables = []
        
        if db_type == "duckdb":
            tables_result = connection.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
            ).fetchall()
            tables = [row[0] for row in tables_result]
            
            for table in tables:
                columns_result = connection.execute(f"""
                    SELECT column_name, data_type
                    FROM information_schema.columns 
                    WHERE table_name = '{table}'
                """).fetchall()
                
                columns = []
                for col_name, col_type in columns_result:
                    columns.append({"name": col_name, "type": col_type})
                    all_columns.append((table, col_name, col_type))
                
                schema_info["tables"][table] = columns
        
        elif db_type in ["postgres", "postgresql"]:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
                cursor.execute(f"""
                    SELECT column_name, data_type
                    FROM information_schema.columns 
                    WHERE table_name = '{table}'
                """)
                columns = []
                for col_name, col_type in cursor.fetchall():
                    columns.append({"name": col_name, "type": col_type})
                    all_columns.append((table, col_name, col_type))
                schema_info["tables"][table] = columns
        
        self._extracted_schemas[database] = schema_info
        
        inferred_terms = self._infer_business_terms(all_columns, tables)
        
        if self.training_collector:
            self._register_ddl_training_data(database, schema_info)
        
        if self.intent_recognizer and inferred_terms:
            self._register_business_terms(inferred_terms)
        
        return {
            "status": "success",
            "database": database,
            "tables": tables,
            "schema_info": schema_info,
            "inferred_terms": inferred_terms
        }
    
    def _infer_business_terms(self, columns: List[Tuple[str, str, str]], 
                               tables: List[str]) -> Dict[str, List[str]]:
        """从字段名和表名推断业务术语映射
        
        Args:
            columns: [(table, column_name, column_type), ...]
            tables: 表名列表
        
        Returns:
            推断的业务术语映射
        """
        inferred = {}
        
        for table, col_name, col_type in columns:
            col_lower = col_name.lower()
            
            for pattern, terms in self.FIELD_TERM_PATTERNS.items():
                if pattern in col_lower:
                    for term in terms:
                        if term not in inferred:
                            inferred[term] = []
                        if col_name not in inferred[term]:
                            inferred[term].append(col_name)
        
        for table in tables:
            table_lower = table.lower()
            
            for pattern, terms in self.TABLE_TERM_PATTERNS.items():
                if pattern in table_lower:
                    for term in terms:
                        if term not in inferred:
                            inferred[term] = []
                        if table not in inferred[term]:
                            inferred[term].append(table)
        
        return inferred
    
    def _register_ddl_training_data(self, database: str, schema_info: Dict[str, Any]):
        """注册 DDL 训练数据"""
        for table_name, columns in schema_info.get("tables", {}).items():
            ddl = self._generate_ddl(table_name, columns)
            
            self.training_collector.add_ddl(
                database=database,
                table=table_name,
                ddl=ddl,
                description=f"表 {table_name} 包含 {len(columns)} 个字段"
            )
    
    def _register_business_terms(self, terms: Dict[str, List[str]]):
        """注册业务术语到意图识别器"""
        if self.intent_recognizer:
            self.intent_recognizer.add_business_terms(terms)
    
    def _generate_ddl(self, table_name: str, columns: List[Dict[str, Any]]) -> str:
        """生成 DDL 语句"""
        col_defs = []
        for col in columns:
            col_def = f"    {col['name']} {col.get('type', 'VARCHAR')}"
            if not col.get('nullable', True):
                col_def += " NOT NULL"
            col_defs.append(col_def)
        
        return f"CREATE TABLE {table_name} (\n" + ",\n".join(col_defs) + "\n)"
    
    def get_schema(self, database: str) -> Optional[Dict[str, Any]]:
        """获取已提取的 Schema"""
        return self._extracted_schemas.get(database)
    
    def get_all_schemas(self) -> Dict[str, Dict[str, Any]]:
        """获取所有已提取的 Schema"""
        return self._extracted_schemas


_schema_extractor_instance = None


def get_schema_extractor(training_collector=None, intent_recognizer=None) -> SchemaExtractor:
    """获取 Schema 提取器单例"""
    global _schema_extractor_instance
    if _schema_extractor_instance is None:
        _schema_extractor_instance = SchemaExtractor(training_collector, intent_recognizer)
    return _schema_extractor_instance
