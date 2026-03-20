#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练数据收集模块 - Vanna 风格
收集 DDL、SQL 示例、文档，用于 RAG 增强的 NL2SQL
"""

import os
import sys
import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)


class TrainingDataCollector:
    """训练数据收集器 - Vanna 风格"""
    
    DATA_TYPE_DDL = "ddl"
    DATA_TYPE_SQL = "sql"
    DATA_TYPE_DOC = "documentation"
    
    def __init__(self, rag_workflow=None):
        """初始化收集器
        
        Args:
            rag_workflow: RAG 工作流实例，用于向量存储
        """
        self.rag_workflow = rag_workflow
        self.training_data_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "..", "data", "training_data"
        )
        os.makedirs(self.training_data_dir, exist_ok=True)
        
        self._training_data_cache = {}
    
    def _generate_id(self, content: str) -> str:
        """生成唯一 ID"""
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def add_ddl(self, database: str, table: str, ddl: str, 
                description: str = None) -> Dict[str, Any]:
        """添加 DDL 训练数据
        
        Args:
            database: 数据库名
            table: 表名
            ddl: DDL 语句
            description: 表描述
        
        Returns:
            添加结果
        """
        content = f"数据库: {database}\n表: {table}\nDDL:\n{ddl}"
        if description:
            content += f"\n描述: {description}"
        
        data_id = self._generate_id(content)
        
        training_item = {
            "id": data_id,
            "type": self.DATA_TYPE_DDL,
            "database": database,
            "table": table,
            "content": content,
            "ddl": ddl,
            "description": description,
            "created_at": datetime.now().isoformat()
        }
        
        self._store_training_data(database, training_item)
        
        return {
            "id": data_id,
            "type": self.DATA_TYPE_DDL,
            "status": "success"
        }
    
    def add_sql(self, database: str, sql: str, question: str,
                tables: List[str] = None, intent_tags: List[str] = None) -> Dict[str, Any]:
        """添加 SQL 示例训练数据
        
        Args:
            database: 数据库名
            sql: SQL 语句
            question: 对应的自然语言问题
            tables: 涉及的表名列表
            intent_tags: 意图标签列表（用于增强检索）
        
        Returns:
            添加结果
        """
        content = f"数据库: {database}\n问题: {question}\nSQL:\n{sql}"
        if tables:
            content += f"\n涉及表: {', '.join(tables)}"
        if intent_tags:
            content += f"\n意图标签: {', '.join(intent_tags)}"
        
        data_id = self._generate_id(content)
        
        training_item = {
            "id": data_id,
            "type": self.DATA_TYPE_SQL,
            "database": database,
            "sql": sql,
            "question": question,
            "tables": tables or [],
            "intent_tags": intent_tags or [],
            "content": content,
            "created_at": datetime.now().isoformat()
        }
        
        self._store_training_data(database, training_item)
        
        return {
            "id": data_id,
            "type": self.DATA_TYPE_SQL,
            "status": "success"
        }
    
    def add_documentation(self, database: str, content: str,
                          title: str = None, source: str = None,
                          intent_tags: List[str] = None) -> Dict[str, Any]:
        """添加文档训练数据
        
        Args:
            database: 数据库名
            content: 文档内容
            title: 文档标题
            source: 文档来源
            intent_tags: 意图标签列表（用于增强检索）
        
        Returns:
            添加结果
        """
        doc_content = f"数据库: {database}\n"
        if title:
            doc_content += f"标题: {title}\n"
        if source:
            doc_content += f"来源: {source}\n"
        if intent_tags:
            doc_content += f"意图标签: {', '.join(intent_tags)}\n"
        doc_content += f"内容:\n{content}"
        
        data_id = self._generate_id(doc_content)
        
        training_item = {
            "id": data_id,
            "type": self.DATA_TYPE_DOC,
            "database": database,
            "content": doc_content,
            "title": title,
            "source": source,
            "intent_tags": intent_tags or [],
            "created_at": datetime.now().isoformat()
        }
        
        self._store_training_data(database, training_item)
        
        return {
            "id": data_id,
            "type": self.DATA_TYPE_DOC,
            "status": "success"
        }
    
    def add_ddl_from_schema(self, database: str, schema_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从 schema 信息自动生成 DDL 训练数据
        
        Args:
            database: 数据库名
            schema_info: schema 信息，格式: {"tables": {"table_name": [{"name": "col1", "type": "VARCHAR"}, ...]}}
        
        Returns:
            添加结果列表
        """
        results = []
        
        for table_name, columns in schema_info.get("tables", {}).items():
            ddl = self._generate_ddl(table_name, columns)
            result = self.add_ddl(database, table_name, ddl)
            results.append(result)
        
        return results
    
    def _generate_ddl(self, table_name: str, columns: List[Dict[str, Any]]) -> str:
        """生成 DDL 语句"""
        col_defs = []
        for col in columns:
            col_name = col.get("name", "")
            col_type = col.get("type", "VARCHAR")
            col_defs.append(f"    {col_name} {col_type}")
        
        ddl = f"CREATE TABLE {table_name} (\n"
        ddl += ",\n".join(col_defs)
        ddl += "\n)"
        
        return ddl
    
    def _store_training_data(self, database: str, training_item: Dict[str, Any]) -> None:
        """存储训练数据到文件和向量数据库"""
        data_type = training_item["type"]
        data_id = training_item["id"]
        
        cache_key = f"{database}_{data_type}"
        if cache_key not in self._training_data_cache:
            self._training_data_cache[cache_key] = self._load_training_data(database, data_type)
        
        self._training_data_cache[cache_key][data_id] = training_item
        
        self._save_training_data(database, data_type, self._training_data_cache[cache_key])
        
        if self.rag_workflow and self.rag_workflow.local_rag_initialized:
            self._add_to_vector_store(database, training_item)
    
    def _load_training_data(self, database: str, data_type: str) -> Dict[str, Any]:
        """加载训练数据"""
        file_path = self._get_data_file_path(database, data_type)
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_training_data(self, database: str, data_type: str, data: Dict[str, Any]) -> None:
        """保存训练数据"""
        file_path = self._get_data_file_path(database, data_type)
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _get_data_file_path(self, database: str, data_type: str) -> str:
        """获取数据文件路径"""
        safe_db_name = database.replace('/', '_').replace('\\', '_').replace('.', '_')
        return os.path.join(self.training_data_dir, f"{safe_db_name}_{data_type}.json")
    
    def _add_to_vector_store(self, database: str, training_item: Dict[str, Any]) -> None:
        """添加到向量数据库"""
        try:
            collection_name = self._get_collection_name(database)
            collection = self.rag_workflow._get_or_create_collection(collection_name)
            
            content = training_item.get("content", "")
            data_id = training_item.get("id", "")
            metadata = {
                "type": training_item.get("type", ""),
                "database": database,
                "id": data_id
            }
            
            if training_item.get("type") == self.DATA_TYPE_DDL:
                metadata["table"] = training_item.get("table", "")
            elif training_item.get("type") == self.DATA_TYPE_SQL:
                metadata["tables"] = json.dumps(training_item.get("tables", []))
            
            collection.add(
                documents=[content],
                ids=[data_id],
                metadatas=[metadata]
            )
        except Exception as e:
            print(f"添加到向量数据库失败: {e}")
    
    def _get_collection_name(self, database: str) -> str:
        """获取集合名称"""
        safe_db_name = database.replace('/', '_').replace('\\', '_').replace('.', '_')
        return f"training_{safe_db_name}"
    
    def get_training_data(self, database: str, data_type: str = None) -> List[Dict[str, Any]]:
        """获取训练数据
        
        Args:
            database: 数据库名
            data_type: 数据类型，None 表示获取所有类型
        
        Returns:
            训练数据列表
        """
        if data_type:
            cache_key = f"{database}_{data_type}"
            if cache_key not in self._training_data_cache:
                self._training_data_cache[cache_key] = self._load_training_data(database, data_type)
            return list(self._training_data_cache[cache_key].values())
        else:
            all_data = []
            for dt in [self.DATA_TYPE_DDL, self.DATA_TYPE_SQL, self.DATA_TYPE_DOC]:
                all_data.extend(self.get_training_data(database, dt))
            return all_data
    
    def search_similar(self, database: str, query: str, top_k: int = 5,
                       data_type: str = None) -> List[Dict[str, Any]]:
        """搜索相似的训练数据
        
        Args:
            database: 数据库名
            query: 查询文本
            top_k: 返回数量
            data_type: 数据类型过滤
        
        Returns:
            相似的训练数据列表
        """
        if not self.rag_workflow or not self.rag_workflow.local_rag_initialized:
            return []
        
        try:
            collection_name = self._get_collection_name(database)
            collection = self.rag_workflow._get_or_create_collection(collection_name)
            
            where_filter = None
            if data_type:
                where_filter = {"type": data_type}
            
            results = collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where_filter
            )
            
            similar_items = []
            if results and results.get("documents"):
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results.get("metadatas", [[]])[0][i] if results.get("metadatas") else {}
                    similar_items.append({
                        "content": doc,
                        "metadata": metadata,
                        "distance": results.get("distances", [[]])[0][i] if results.get("distances") else None
                    })
            
            return similar_items
        except Exception as e:
            print(f"搜索相似训练数据失败: {e}")
            return []
    
    def remove_training_data(self, database: str, data_id: str, data_type: str) -> bool:
        """删除训练数据
        
        Args:
            database: 数据库名
            data_id: 数据 ID
            data_type: 数据类型
        
        Returns:
            是否成功
        """
        try:
            cache_key = f"{database}_{data_type}"
            if cache_key not in self._training_data_cache:
                self._training_data_cache[cache_key] = self._load_training_data(database, data_type)
            
            if data_id in self._training_data_cache[cache_key]:
                del self._training_data_cache[cache_key][data_id]
                self._save_training_data(database, data_type, self._training_data_cache[cache_key])
                
                if self.rag_workflow and self.rag_workflow.local_rag_initialized:
                    collection_name = self._get_collection_name(database)
                    collection = self.rag_workflow._get_or_create_collection(collection_name)
                    collection.delete(ids=[data_id])
                
                return True
            return False
        except Exception as e:
            print(f"删除训练数据失败: {e}")
            return False
    
    def get_training_stats(self, database: str) -> Dict[str, Any]:
        """获取训练数据统计
        
        Args:
            database: 数据库名
        
        Returns:
            统计信息
        """
        stats = {
            "database": database,
            "ddl_count": len(self.get_training_data(database, self.DATA_TYPE_DDL)),
            "sql_count": len(self.get_training_data(database, self.DATA_TYPE_SQL)),
            "doc_count": len(self.get_training_data(database, self.DATA_TYPE_DOC)),
            "total": 0
        }
        stats["total"] = stats["ddl_count"] + stats["sql_count"] + stats["doc_count"]
        return stats


def get_training_data_collector(rag_workflow=None) -> TrainingDataCollector:
    """获取训练数据收集器实例"""
    return TrainingDataCollector(rag_workflow)
