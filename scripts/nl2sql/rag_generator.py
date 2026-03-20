#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG 检索增强生成模块 - Vanna 风格
基于训练数据检索，生成 SQL 查询
支持 Agent LLM SQL 生成
支持意图识别增强
"""

import os
import sys
import re
from typing import Dict, Any, List, Optional, Tuple

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from training_data import TrainingDataCollector, get_training_data_collector
from intent_recognizer import IntentRecognizer, get_intent_recognizer, Intent, IntentType


class RAGSQLGenerator:
    """RAG 检索增强 SQL 生成器 - Vanna 风格"""
    
    SQL_PROMPT_TEMPLATE = """你是一个 SQL 专家。根据以下信息生成 SQL 查询。

## 数据库信息
数据库名: {database}

## 相关表结构 (DDL)
{ddl_section}

## 相似 SQL 示例
{sql_examples_section}

## 相关文档
{docs_section}

## 用户问题
{question}

## 要求
1. 只生成 SELECT 查询语句，不要生成 INSERT、UPDATE、DELETE 等修改语句
2. 使用标准 SQL 语法
3. 如果无法确定表名或字段，使用最接近的猜测
4. 只返回 SQL 语句，不要包含解释

## SQL
```sql
"""

    def __init__(self, rag_workflow=None, training_collector: TrainingDataCollector = None,
                 intent_recognizer: IntentRecognizer = None):
        """初始化生成器
        
        Args:
            rag_workflow: RAG 工作流实例
            training_collector: 训练数据收集器
            intent_recognizer: 意图识别器
        """
        self.rag_workflow = rag_workflow
        self.training_collector = training_collector or get_training_data_collector(rag_workflow)
        self.intent_recognizer = intent_recognizer or get_intent_recognizer()
        
        self.similarity_threshold = 0.3
        self.use_intent_recognition = True
    
    def generate_sql_with_rag(self, nl_text: str, database: str,
                               schema_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """使用 RAG 增强 SQL 生成
        
        Args:
            nl_text: 自然语言查询
            database: 数据库名
            schema_info: schema 信息（可选）
        
        Returns:
            生成结果，包含 SQL、上下文、相似度等信息
        """
        result = {
            "nl_text": nl_text,
            "database": database,
            "sql": None,
            "context": {
                "similar_sql": [],
                "relevant_ddl": [],
                "relevant_docs": [],
                "intent": None
            },
            "method": None,
            "confidence": 0.0
        }
        
        intent = None
        if self.use_intent_recognition:
            intent = self.intent_recognizer.recognize(nl_text)
            result["context"]["intent"] = {
                "type": intent.intent_type.value,
                "target": intent.target,
                "action": intent.action,
                "entities": intent.entities,
                "confidence": intent.confidence
            }
        
        enhanced_text = intent.enhanced_text if intent else nl_text
        
        similar_sql = self._find_similar_sql(database, enhanced_text)
        
        if intent:
            intent_tags = self._get_intent_tags(intent)
            similar_sql = self._filter_by_intent_tags(similar_sql, intent_tags)
        
        result["context"]["similar_sql"] = similar_sql
        
        if similar_sql and similar_sql[0].get("distance", 1) < 0.2:
            best_match = similar_sql[0]
            sql = self._adapt_sql(best_match.get("metadata", {}).get("sql", ""),
                                  nl_text, schema_info, intent)
            result["sql"] = sql
            result["method"] = "similar_sql_adaptation"
            result["confidence"] = 1.0 - best_match.get("distance", 0.5)
            return result
        
        relevant_ddl = self._find_relevant_ddl(database, enhanced_text)
        if intent:
            suggested_tables = self.intent_recognizer.get_table_suggestions(intent)
            relevant_ddl = self._merge_ddl_with_suggestions(relevant_ddl, suggested_tables, database)
        result["context"]["relevant_ddl"] = relevant_ddl
        
        relevant_docs = self._find_relevant_docs(database, enhanced_text)
        if intent:
            intent_tags = self._get_intent_tags(intent)
            relevant_docs = self._filter_by_intent_tags(relevant_docs, intent_tags)
        result["context"]["relevant_docs"] = relevant_docs
        
        if relevant_ddl or relevant_docs:
            sql = self._generate_sql_from_context(nl_text, relevant_ddl, relevant_docs, schema_info, intent)
            result["sql"] = sql
            result["method"] = "rag_enhanced_generation"
            result["confidence"] = self._calculate_confidence(relevant_ddl, relevant_docs, similar_sql, intent)
            return result
        
        if schema_info:
            sql = self._generate_sql_from_schema(nl_text, schema_info, database, intent)
            result["sql"] = sql
            result["method"] = "schema_based_generation"
            result["confidence"] = 0.5
            return result
        
        result["sql"] = "SELECT 1"
        result["method"] = "fallback"
        result["confidence"] = 0.0
        return result
    
    def generate_sql_prompt(self, nl_text: str, database: str,
                            schema_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """生成供 Agent LLM 使用的 SQL 生成 prompt
        
        这是 Vanna 风格的核心方法：
        1. 检索相关的 DDL、SQL 示例、文档
        2. 构建完整的 prompt
        3. 返回给 Agent，由 Agent 的 LLM 生成 SQL
        
        Args:
            nl_text: 自然语言查询
            database: 数据库名
            schema_info: schema 信息（可选）
        
        Returns:
            包含 prompt 和上下文的字典
        """
        similar_sql = self._find_similar_sql(database, nl_text, top_k=3)
        relevant_ddl = self._find_relevant_ddl(database, nl_text, top_k=5)
        relevant_docs = self._find_relevant_docs(database, nl_text, top_k=3)
        
        if not relevant_ddl and schema_info:
            relevant_ddl = self._build_ddl_from_schema(schema_info)
        
        ddl_section = self._format_ddl_section(relevant_ddl)
        sql_examples_section = self._format_sql_examples_section(similar_sql)
        docs_section = self._format_docs_section(relevant_docs)
        
        prompt = self.SQL_PROMPT_TEMPLATE.format(
            database=database,
            ddl_section=ddl_section,
            sql_examples_section=sql_examples_section,
            docs_section=docs_section,
            question=nl_text
        )
        
        return {
            "prompt": prompt,
            "context": {
                "similar_sql": similar_sql,
                "relevant_ddl": relevant_ddl,
                "relevant_docs": relevant_docs
            },
            "database": database,
            "nl_text": nl_text,
            "instruction": "请根据以上 prompt 生成 SQL 查询语句，只返回 SQL，不要包含其他内容。"
        }
    
    def _format_ddl_section(self, relevant_ddl: List[Dict[str, Any]]) -> str:
        """格式化 DDL 部分"""
        if not relevant_ddl:
            return "（无相关表结构信息）"
        
        sections = []
        for ddl in relevant_ddl[:5]:
            content = ddl.get("content", "")
            metadata = ddl.get("metadata", {})
            table = metadata.get("table", "")
            if table:
                sections.append(f"### 表: {table}\n{content}")
            else:
                sections.append(content)
        
        return "\n\n".join(sections)
    
    def _format_sql_examples_section(self, similar_sql: List[Dict[str, Any]]) -> str:
        """格式化 SQL 示例部分"""
        if not similar_sql:
            return "（无相似 SQL 示例）"
        
        sections = []
        for i, sql_item in enumerate(similar_sql[:3], 1):
            metadata = sql_item.get("metadata", {})
            question = metadata.get("question", "未知问题")
            sql = metadata.get("sql", "")
            sections.append(f"### 示例 {i}\n问题: {question}\nSQL: {sql}")
        
        return "\n\n".join(sections)
    
    def _format_docs_section(self, relevant_docs: List[Dict[str, Any]]) -> str:
        """格式化文档部分"""
        if not relevant_docs:
            return "（无相关文档）"
        
        sections = []
        for doc in relevant_docs[:3]:
            content = doc.get("content", "")
            sections.append(content)
        
        return "\n\n".join(sections)
    
    def _build_ddl_from_schema(self, schema_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从 schema 信息构建 DDL 格式"""
        ddl_list = []
        for table_name, columns in schema_info.get("tables", {}).items():
            col_defs = []
            for col in columns:
                col_name = col.get("name", "")
                col_type = col.get("type", "VARCHAR")
                col_defs.append(f"    {col_name} {col_type}")
            
            ddl = f"CREATE TABLE {table_name} (\n" + ",\n".join(col_defs) + "\n)"
            
            ddl_list.append({
                "content": ddl,
                "metadata": {"table": table_name}
            })
        
        return ddl_list
    
    def _find_similar_sql(self, database: str, nl_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """查找相似的 SQL 示例"""
        return self.training_collector.search_similar(
            database=database,
            query=nl_text,
            top_k=top_k,
            data_type=TrainingDataCollector.DATA_TYPE_SQL
        )
    
    def _find_relevant_ddl(self, database: str, nl_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """查找相关的 DDL"""
        return self.training_collector.search_similar(
            database=database,
            query=nl_text,
            top_k=top_k,
            data_type=TrainingDataCollector.DATA_TYPE_DDL
        )
    
    def _find_relevant_docs(self, database: str, nl_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """查找相关的文档"""
        return self.training_collector.search_similar(
            database=database,
            query=nl_text,
            top_k=top_k,
            data_type=TrainingDataCollector.DATA_TYPE_DOC
        )
    
    def _get_intent_tags(self, intent: Intent) -> List[str]:
        """从意图中提取标签"""
        tags = []
        
        tags.append(intent.intent_type.value)
        
        if intent.target:
            tags.append(intent.target)
        
        for entity_name in intent.entities.keys():
            tags.append(entity_name)
        
        return list(set(tags))
    
    def _filter_by_intent_tags(self, items: List[Dict[str, Any]], 
                                intent_tags: List[str]) -> List[Dict[str, Any]]:
        """根据意图标签过滤和排序结果"""
        if not intent_tags or not items:
            return items
        
        scored_items = []
        for item in items:
            score = item.get("distance", 0.5)
            item_tags = item.get("metadata", {}).get("intent_tags", [])
            
            if item_tags:
                tag_match_count = len(set(intent_tags) & set(item_tags))
                if tag_match_count > 0:
                    score -= tag_match_count * 0.1
            
            scored_items.append((score, item))
        
        scored_items.sort(key=lambda x: x[0])
        
        return [item for score, item in scored_items]
    
    def _adapt_sql(self, template_sql: str, nl_text: str,
                   schema_info: Dict[str, Any] = None,
                   intent: Intent = None) -> str:
        """适配 SQL 模板"""
        if not template_sql:
            return "SELECT 1"
        
        sql = template_sql
        
        if intent:
            if intent.intent_type == IntentType.COUNT and "COUNT" not in sql.upper():
                sql = re.sub(r"SELECT\s+.*?\s+FROM", "SELECT COUNT(*) FROM", sql, flags=re.IGNORECASE)
            elif intent.intent_type == IntentType.AGGREGATE and "SUM" not in sql.upper() and "AVG" not in sql.upper():
                sql = re.sub(r"SELECT\s+.*?\s+FROM", "SELECT SUM(*) FROM", sql, flags=re.IGNORECASE)
        
        conditions = self._extract_conditions_from_nl(nl_text)
        if conditions:
            if "WHERE" in sql.upper():
                sql = re.sub(r"WHERE.*?(?=ORDER|GROUP|LIMIT|$)", 
                            f"WHERE {' AND '.join(conditions)} ", sql, flags=re.IGNORECASE)
            else:
                limit_match = re.search(r"LIMIT\s+\d+", sql, re.IGNORECASE)
                if limit_match:
                    sql = sql[:limit_match.start()] + f"WHERE {' AND '.join(conditions)} " + sql[limit_match.start():]
                else:
                    sql += f" WHERE {' AND '.join(conditions)}"
        
        return sql
    
    def _extract_conditions_from_nl(self, nl_text: str) -> List[str]:
        """从自然语言中提取条件"""
        conditions = []
        
        value_patterns = [
            r"['\"]([^'\"]+)['\"]",
            r"为\s*(\S+)",
            r"等于\s*(\S+)",
            r"是\s*(\S+)"
        ]
        
        for pattern in value_patterns:
            matches = re.findall(pattern, nl_text)
            for match in matches:
                if len(match) > 0 and len(match) < 50:
                    conditions.append(f"column LIKE '%{match}%'")
        
        return conditions[:3]
    
    def _generate_sql_from_context(self, nl_text: str,
                                    relevant_ddl: List[Dict[str, Any]],
                                    relevant_docs: List[Dict[str, Any]],
                                    schema_info: Dict[str, Any] = None,
                                    intent: Intent = None) -> str:
        """基于上下文生成 SQL"""
        tables = self._extract_tables_from_ddl(relevant_ddl)
        
        if not tables and schema_info:
            tables = list(schema_info.get("tables", {}).keys())
        
        if not tables:
            return "SELECT 1"
        
        target_table = self._select_best_table(nl_text, tables, relevant_ddl, intent)
        
        columns = self._extract_columns_from_ddl(relevant_ddl, target_table)
        if not columns and schema_info:
            columns = [col.get("name") for col in schema_info.get("tables", {}).get(target_table, [])]
        
        select_clause = self._build_select_clause(nl_text, columns, intent)
        from_clause = f"FROM {target_table}"
        
        conditions = self._extract_conditions_from_nl(nl_text)
        if intent and intent.filters:
            for f in intent.filters:
                if f["type"] == "exact":
                    conditions.append(f"column = '{f['value']}'")
                elif f["type"] == "contains":
                    conditions.append(f"column LIKE '%{f['value']}%'")
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        limit_clause = self._build_limit_clause(nl_text, intent)
        
        sql = f"{select_clause} {from_clause} {where_clause} {limit_clause}"
        return sql
    
    def _extract_tables_from_ddl(self, relevant_ddl: List[Dict[str, Any]]) -> List[str]:
        """从 DDL 中提取表名"""
        tables = []
        for ddl_item in relevant_ddl:
            metadata = ddl_item.get("metadata", {})
            table = metadata.get("table")
            if table and table not in tables:
                tables.append(table)
        return tables
    
    def _extract_columns_from_ddl(self, relevant_ddl: List[Dict[str, Any]],
                                   table: str) -> List[str]:
        """从 DDL 中提取列名"""
        columns = []
        for ddl_item in relevant_ddl:
            metadata = ddl_item.get("metadata", {})
            if metadata.get("table") == table:
                content = ddl_item.get("content", "")
                col_matches = re.findall(r"^\s*(\w+)\s+\w+", content, re.MULTILINE)
                columns.extend(col_matches)
        return list(set(columns))
    
    def _select_best_table(self, nl_text: str, tables: List[str],
                           relevant_ddl: List[Dict[str, Any]],
                           intent: Intent = None) -> str:
        """选择最佳表"""
        if intent:
            suggested_tables = self.intent_recognizer.get_table_suggestions(intent)
            for suggested in suggested_tables:
                if suggested in tables:
                    return suggested
        
        if len(tables) == 1:
            return tables[0]
        
        for table in tables:
            if table.lower() in nl_text.lower():
                return table
        
        if relevant_ddl:
            for ddl_item in relevant_ddl:
                metadata = ddl_item.get("metadata", {})
                table = metadata.get("table")
                if table in tables:
                    return table
        
        return tables[0]
    
    def _build_select_clause(self, nl_text: str, columns: List[str],
                             intent: Intent = None) -> str:
        """构建 SELECT 子句"""
        if intent:
            if intent.intent_type == IntentType.COUNT:
                return "SELECT COUNT(*)"
            elif intent.intent_type == IntentType.AGGREGATE:
                if "平均" in nl_text or "avg" in nl_text.lower():
                    return "SELECT AVG(amount)" if "amount" in columns else "SELECT AVG(*)"
                elif "最大" in nl_text or "max" in nl_text.lower():
                    return "SELECT MAX(amount)" if "amount" in columns else "SELECT MAX(*)"
                elif "最小" in nl_text or "min" in nl_text.lower():
                    return "SELECT MIN(amount)" if "amount" in columns else "SELECT MIN(*)"
                else:
                    return "SELECT SUM(amount)" if "amount" in columns else "SELECT SUM(*)"
        
        all_keywords = ["所有", "全部", "all", "*"]
        if any(kw in nl_text.lower() for kw in all_keywords):
            return "SELECT *"
        
        if columns:
            if intent and intent.entities:
                priority_cols = []
                for term, field in intent.entities.items():
                    if field in columns:
                        priority_cols.append(field)
                if priority_cols:
                    other_cols = [c for c in columns[:5] if c not in priority_cols]
                    display_cols = priority_cols + other_cols
                    return f"SELECT {', '.join(display_cols[:5])}"
            
            display_cols = columns[:5] if len(columns) > 5 else columns
            return f"SELECT {', '.join(display_cols)}"
        
        return "SELECT *"
    
    def _build_limit_clause(self, nl_text: str, intent: Intent = None) -> str:
        """构建 LIMIT 子句"""
        if intent and intent.intent_type == IntentType.COUNT:
            return ""
        
        if intent and intent.intent_type == IntentType.AGGREGATE:
            return ""
        
        limit_match = re.search(r"前\s*(\d+)", nl_text)
        if limit_match:
            return f"LIMIT {limit_match.group(1)}"
        
        return "LIMIT 10"
    
    def _merge_ddl_with_suggestions(self, relevant_ddl: List[Dict[str, Any]],
                                     suggested_tables: List[str],
                                     database: str) -> List[Dict[str, Any]]:
        """合并 DDL 和建议表"""
        existing_tables = set()
        for ddl in relevant_ddl:
            metadata = ddl.get("metadata", {})
            table = metadata.get("table")
            if table:
                existing_tables.add(table)
        
        for table in suggested_tables:
            if table not in existing_tables:
                relevant_ddl.append({
                    "content": f"表: {table}",
                    "metadata": {"table": table, "suggested": True}
                })
        
        return relevant_ddl
    
    def _generate_sql_from_schema(self, nl_text: str, schema_info: Dict[str, Any],
                                   database: str, intent: Intent = None) -> str:
        """基于 schema 生成 SQL（降级方案）"""
        tables = list(schema_info.get("tables", {}).keys())
        if not tables:
            return "SELECT 1"
        
        target_table = self._select_best_table(nl_text, tables, [], intent)
        columns = [col.get("name") for col in schema_info.get("tables", {}).get(target_table, [])]
        
        select_clause = self._build_select_clause(nl_text, columns, intent)
        conditions = self._extract_conditions_from_nl(nl_text)
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        limit_clause = self._build_limit_clause(nl_text, intent)
        
        return f"{select_clause} FROM {target_table} {where_clause} {limit_clause}"
    
    def _calculate_confidence(self, relevant_ddl: List[Dict[str, Any]],
                               relevant_docs: List[Dict[str, Any]],
                               similar_sql: List[Dict[str, Any]],
                               intent: Intent = None) -> float:
        """计算置信度"""
        confidence = 0.0
        
        if intent:
            confidence += intent.confidence * 0.2
        
        if similar_sql:
            best_distance = similar_sql[0].get("distance", 1)
            confidence += (1.0 - best_distance) * 0.4
        
        if relevant_ddl:
            avg_ddl_distance = sum(d.get("distance", 0.5) for d in relevant_ddl) / len(relevant_ddl)
            confidence += (1.0 - avg_ddl_distance) * 0.3
        
        if relevant_docs:
            avg_doc_distance = sum(d.get("distance", 0.5) for d in relevant_docs) / len(relevant_docs)
            confidence += (1.0 - avg_doc_distance) * 0.2
        
        return min(confidence, 1.0)
    
    def get_prompt_context(self, nl_text: str, database: str) -> str:
        """获取用于 LLM 的上下文提示"""
        similar_sql = self._find_similar_sql(database, nl_text, top_k=2)
        relevant_ddl = self._find_relevant_ddl(database, nl_text, top_k=3)
        relevant_docs = self._find_relevant_docs(database, nl_text, top_k=2)
        
        context_parts = []
        
        if relevant_ddl:
            context_parts.append("### 相关表结构:")
            for ddl in relevant_ddl[:3]:
                context_parts.append(f"```sql\n{ddl.get('content', '')}\n```")
        
        if similar_sql:
            context_parts.append("\n### 相似 SQL 示例:")
            for sql in similar_sql[:2]:
                metadata = sql.get("metadata", {})
                context_parts.append(f"问题: {metadata.get('question', '')}")
                context_parts.append(f"SQL: ```sql\n{metadata.get('sql', '')}\n```")
        
        if relevant_docs:
            context_parts.append("\n### 相关文档:")
            for doc in relevant_docs[:2]:
                context_parts.append(doc.get("content", ""))
        
        return "\n".join(context_parts)


def get_rag_sql_generator(rag_workflow=None, training_collector=None, 
                          intent_recognizer=None) -> RAGSQLGenerator:
    """获取 RAG SQL 生成器实例"""
    return RAGSQLGenerator(rag_workflow, training_collector, intent_recognizer)
