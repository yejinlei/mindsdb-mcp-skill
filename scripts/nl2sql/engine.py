#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NL2SQL 核心模块 - Vanna 风格
负责将自然语言转换为 SQL 查询，结合本地 RAG 提高准确性
支持训练数据收集、向量检索增强生成
"""

import os
import sys
import re
from typing import Dict, Any, List, Optional

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from db_connector import get_db_connector
from training_data import get_training_data_collector, TrainingDataCollector
from rag_generator import get_rag_sql_generator, RAGSQLGenerator


class NL2SQLEngine:
    """NL2SQL 核心引擎 - Vanna 风格"""
    
    def __init__(self, rag_workflow):
        """初始化 NL2SQL 引擎"""
        self.rag_workflow = rag_workflow
        self.db_connector = get_db_connector()
        self.schema_cache = {}
        
        self.default_limit = 10
        self.default_column_count = 5
        
        self.training_collector = get_training_data_collector(rag_workflow)
        self.rag_generator = get_rag_sql_generator(rag_workflow, self.training_collector)
        
        self._initialized_from_schema = {}
    
    def extract_schema_info(self, database: str) -> Dict[str, Any]:
        """提取数据库模式信息"""
        if database in self.schema_cache:
            return self.schema_cache[database]
        
        schema_info = {
            "tables": {},
            "relationships": []
        }
        
        try:
            if hasattr(self.db_connector, 'conn') and self.db_connector.conn is not None:
                conn = self.db_connector.conn
                
                tables = conn.execute("SHOW TABLES").fetchall()
                table_names = [table[0] for table in tables]
                
                for table in table_names:
                    schema = conn.execute(f"DESCRIBE {table}").fetchall()
                    columns = []
                    for col_info in schema:
                        columns.append({
                            "name": col_info[0],
                            "type": col_info[1]
                        })
                    schema_info["tables"][table] = columns
            else:
                show_tables_result = self.db_connector.show_tables(database)
                if show_tables_result.get('code') == 0:
                    tables_data = show_tables_result.get('data', {})
                    if 'data' in tables_data:
                        table_names = [row[0] for row in tables_data['data'] if row]
                        
                        for table in table_names:
                            describe_result = self.db_connector.describe_table(database, table)
                            if describe_result.get('code') == 0:
                                schema_data = describe_result.get('data', {})
                                if 'data' in schema_data and 'columns' in schema_data:
                                    columns = []
                                    for row in schema_data['data']:
                                        if row:
                                            columns.append({
                                                "name": row[0],
                                                "type": row[1] if len(row) > 1 else ""
                                            })
                                    schema_info["tables"][table] = columns
        except Exception as e:
            print(f"提取模式信息失败: {e}")
        
        self.schema_cache[database] = schema_info
        return schema_info
    
    def initialize_from_schema(self, database: str, auto_add_ddl: bool = True) -> Dict[str, Any]:
        """从 schema 初始化训练数据
        
        Args:
            database: 数据库名
            auto_add_ddl: 是否自动添加 DDL 训练数据
        
        Returns:
            初始化结果
        """
        if database in self._initialized_from_schema:
            return {
                "status": "already_initialized",
                "database": database
            }
        
        schema_info = self.extract_schema_info(database)
        
        results = {
            "database": database,
            "ddl_added": 0,
            "tables": list(schema_info.get("tables", {}).keys())
        }
        
        if auto_add_ddl:
            ddl_results = self.training_collector.add_ddl_from_schema(database, schema_info)
            results["ddl_added"] = len(ddl_results)
        
        self._initialized_from_schema[database] = True
        
        return results
    
    def add_training_sql(self, database: str, sql: str, question: str,
                         tables: List[str] = None) -> Dict[str, Any]:
        """添加 SQL 训练数据
        
        Args:
            database: 数据库名
            sql: SQL 语句
            question: 对应的自然语言问题
            tables: 涉及的表名列表
        
        Returns:
            添加结果
        """
        return self.training_collector.add_sql(database, sql, question, tables)
    
    def add_training_documentation(self, database: str, content: str,
                                    title: str = None, source: str = None) -> Dict[str, Any]:
        """添加文档训练数据
        
        Args:
            database: 数据库名
            content: 文档内容
            title: 文档标题
            source: 文档来源
        
        Returns:
            添加结果
        """
        return self.training_collector.add_documentation(database, content, title, source)
    
    def get_training_stats(self, database: str) -> Dict[str, Any]:
        """获取训练数据统计
        
        Args:
            database: 数据库名
        
        Returns:
            统计信息
        """
        return self.training_collector.get_training_stats(database)
    
    def generate_sql(self, nl_text: str, database: str, use_rag: bool = True) -> str:
        """生成 SQL 查询
        
        Args:
            nl_text: 自然语言查询
            database: 数据库名
            use_rag: 是否使用 RAG 增强
        
        Returns:
            SQL 语句
        """
        schema_info = self.extract_schema_info(database)
        
        if use_rag:
            rag_result = self.rag_generator.generate_sql_with_rag(
                nl_text=nl_text,
                database=database,
                schema_info=schema_info
            )
            return rag_result.get("sql", "SELECT 1")
        else:
            return self._build_sql_simple(nl_text, schema_info, database)
    
    def generate_sql_with_context(self, nl_text: str, database: str) -> Dict[str, Any]:
        """生成 SQL 查询并返回完整上下文
        
        Args:
            nl_text: 自然语言查询
            database: 数据库名
        
        Returns:
            包含 SQL、上下文、置信度的完整结果
        """
        schema_info = self.extract_schema_info(database)
        
        rag_result = self.rag_generator.generate_sql_with_rag(
            nl_text=nl_text,
            database=database,
            schema_info=schema_info
        )
        
        return rag_result
    
    def generate_sql_prompt_for_agent(self, nl_text: str, database: str) -> Dict[str, Any]:
        """生成供 Agent LLM 使用的 SQL 生成 prompt
        
        这是 Vanna 风格的核心方法：
        1. 检索相关的 DDL、SQL 示例、文档
        2. 构建完整的 prompt
        3. 返回给 Agent，由 Agent 的 LLM 生成 SQL
        
        Args:
            nl_text: 自然语言查询
            database: 数据库名
        
        Returns:
            包含 prompt 和上下文的字典，供 Agent LLM 使用
        """
        schema_info = self.extract_schema_info(database)
        
        prompt_result = self.rag_generator.generate_sql_prompt(
            nl_text=nl_text,
            database=database,
            schema_info=schema_info
        )
        
        prompt_result["schema_info"] = schema_info
        prompt_result["action"] = "generate_sql"
        prompt_result["instruction_for_agent"] = (
            "请根据以上 prompt 和上下文信息生成 SQL 查询语句。\n"
            "要求：\n"
            "1. 只返回 SQL 语句，不要包含解释\n"
            "2. 使用标准 SQL 语法\n"
            "3. 只生成 SELECT 查询语句\n"
            "4. 生成 SQL 后，请使用 exec_sql action 执行查询"
        )
        
        return prompt_result
    
    def validate_and_fix_sql(self, sql: str, database: str) -> Dict[str, Any]:
        """验证并修复 SQL 语句
        
        Args:
            sql: SQL 语句
            database: 数据库名
        
        Returns:
            验证结果，包含是否有效、修复后的 SQL、错误信息等
        """
        schema_info = self.extract_schema_info(database)
        tables = list(schema_info.get("tables", {}).keys())
        
        result = {
            "original_sql": sql,
            "fixed_sql": sql,
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        if not sql or not sql.strip():
            result["is_valid"] = False
            result["errors"].append("SQL 语句为空")
            return result
        
        sql_upper = sql.upper().strip()
        
        dangerous_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER", "CREATE"]
        for keyword in dangerous_keywords:
            if sql_upper.startswith(keyword):
                result["is_valid"] = False
                result["errors"].append(f"不允许执行 {keyword} 操作")
                return result
        
        from_match = re.search(r'\bFROM\s+(\w+)', sql, re.IGNORECASE)
        if from_match:
            table_name = from_match.group(1)
            if table_name not in tables:
                similar_tables = [t for t in tables if table_name.lower() in t.lower()]
                if similar_tables:
                    result["warnings"].append(f"表 '{table_name}' 不存在，可能是指 '{similar_tables[0]}'")
                    result["fixed_sql"] = re.sub(
                        rf'\bFROM\s+{table_name}\b',
                        f'FROM {similar_tables[0]}',
                        sql,
                        flags=re.IGNORECASE
                    )
                else:
                    result["warnings"].append(f"表 '{table_name}' 不存在于数据库中")
        
        if "LIMIT" not in sql_upper:
            result["fixed_sql"] = result["fixed_sql"].rstrip(";") + " LIMIT 100"
            result["warnings"].append("已添加 LIMIT 100 限制")
        
        return result
    
    def _build_sql_simple(self, nl_text: str, schema_info: Dict[str, Any], 
                          database: str = "default") -> str:
        """构建 SQL 查询 - 简单版本（不使用 RAG）"""
        tables = list(schema_info["tables"].keys())
        if not tables:
            return "SELECT 1"
        
        target_table = self._select_target_table(nl_text, tables, database)
        if not target_table:
            return "SELECT 1"
        
        columns = schema_info["tables"][target_table]
        column_names = [col["name"] for col in columns]
        
        select_clause = self._build_select_clause(nl_text, column_names)
        from_clause = f"FROM {target_table}"
        
        conditions = self._extract_conditions(nl_text, column_names)
        where_clause = f"WHERE {' OR '.join(conditions)}" if conditions else ""
        
        sql = f"{select_clause} {from_clause} {where_clause} LIMIT {self.default_limit}"
        return sql
    
    def _build_select_clause(self, nl_text: str, column_names: List[str]) -> str:
        """构建 SELECT 子句"""
        all_field_keywords = ["所有", "全部", "all", "*", "everything"]
        if any(keyword in nl_text.lower() for keyword in all_field_keywords):
            return "SELECT *"
        
        text_columns = column_names[:self.default_column_count] if len(column_names) > self.default_column_count else column_names
        return f"SELECT {', '.join(text_columns)}"
    
    def _select_target_table(self, nl_text: str, tables: List[str], 
                              database: str = "default") -> str:
        """智能选择目标表"""
        if not tables:
            return None
        
        if len(tables) == 1:
            return tables[0]
        
        for table in tables:
            table_lower = table.lower()
            if table_lower in nl_text.lower():
                return table
            table_simple = table_lower.replace('_', '').replace('-', '')
            if table_simple in nl_text.lower().replace('_', '').replace('-', ''):
                return table
            table_parts = table_lower.split('_')
            for part in table_parts:
                if part in nl_text.lower():
                    return table
        
        try:
            table_descriptions = []
            for table in tables:
                schema = self.schema_cache.get(database, {}).get("tables", {}).get(table, [])
                if schema:
                    columns = [col["name"] for col in schema]
                    desc = f"表 {table} 包含字段: {', '.join(columns)}"
                    table_descriptions.append((table, desc))
                else:
                    table_descriptions.append((table, f"表 {table}"))
            
            if self.rag_workflow.embedding_model:
                import numpy as np
                
                query_embedding = self.rag_workflow.embedding_model.encode([nl_text])
                descriptions = [desc for _, desc in table_descriptions]
                desc_embeddings = self.rag_workflow.embedding_model.encode(descriptions)
                
                similarities = []
                for desc_embedding in desc_embeddings:
                    similarity = np.dot(query_embedding[0], desc_embedding) / (
                        np.linalg.norm(query_embedding[0]) * np.linalg.norm(desc_embedding)
                    )
                    similarities.append(similarity)
                
                if similarities:
                    best_index = np.argmax(similarities)
                    return table_descriptions[best_index][0]
        except Exception:
            pass
        
        return tables[0]
    
    def _extract_conditions(self, nl_text: str, column_names: List[str]) -> List[str]:
        """提取查询条件"""
        conditions = []
        
        for col in column_names:
            if col.lower() in nl_text.lower():
                value_match = re.search(rf"{col}['\"]([^'\"]+)['\"]", nl_text)
                if value_match:
                    value = value_match.group(1)
                    conditions.append(f"{col} = '{value}'")
                    continue
                
                contain_keywords = ["包含", "include", "has", "contain"]
                if any(keyword in nl_text.lower() for keyword in contain_keywords):
                    contain_match = re.search(r"包含['\"]([^'\"]+)['\"]", nl_text)
                    if contain_match:
                        value = contain_match.group(1)
                        conditions.append(f"{col} LIKE '%{value}%'")
                        continue
        
        search_keywords = ["搜索", "查找", "search", "find", "look for"]
        if any(keyword in nl_text.lower() for keyword in search_keywords):
            search_match = re.search(r"[搜索查找searchfind]['\"]([^'\"]+)['\"]", nl_text)
            if search_match:
                value = search_match.group(1)
                for col in column_names:
                    conditions.append(f"{col} LIKE '%{value}%'")
        
        return conditions
    
    def execute_sql(self, sql: str, database: str) -> Dict[str, Any]:
        """执行 SQL 查询"""
        try:
            if hasattr(self.db_connector, 'conn') and self.db_connector.conn is not None:
                conn = self.db_connector.conn
                result = conn.execute(sql).fetchall()
                columns = [desc[0] for desc in conn.execute(sql).description]
                
                return {
                    "columns": columns,
                    "rows": result,
                    "count": len(result)
                }
            else:
                execute_result = self.db_connector.execute_sql(sql)
                if execute_result.get('code') == 0:
                    result_data = execute_result.get('data', {})
                    return {
                        "columns": result_data.get('columns', []),
                        "rows": result_data.get('data', []),
                        "count": len(result_data.get('data', []))
                    }
                else:
                    return {"error": execute_result.get('msg', '执行失败')}
        except Exception as e:
            return {"error": str(e)}
    
    def process_result(self, result: Dict[str, Any], nl_text: str) -> Dict[str, Any]:
        """处理查询结果"""
        if "error" in result:
            return {
                "summary": f"查询失败: {result['error']}",
                "data": [],
                "visualization": None
            }
        
        count = result.get('count', 0)
        columns = result.get('columns', [])
        rows = result.get('rows', [])
        
        summary = f"找到 {count} 条记录"
        if rows:
            summary += f"，前 {min(5, count)} 条记录如下："
        
        visualization = {
            "type": "table",
            "columns": columns,
            "rows": rows[:5]
        }
        
        return {
            "summary": summary,
            "data": rows,
            "visualization": visualization
        }
    
    def get_prompt_context(self, nl_text: str, database: str) -> str:
        """获取用于 LLM 的上下文提示
        
        可以传递给外部 LLM 进行更准确的 SQL 生成
        
        Args:
            nl_text: 自然语言查询
            database: 数据库名
        
        Returns:
            上下文提示字符串
        """
        return self.rag_generator.get_prompt_context(nl_text, database)


def get_nl2sql_engine(rag_workflow):
    """获取 NL2SQL 引擎实例"""
    return NL2SQLEngine(rag_workflow)
