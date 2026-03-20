#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练数据配置加载器
支持从 YAML 配置文件加载业务术语和训练样本
"""

import os
import yaml
from typing import Dict, Any, List, Optional


class TrainingConfigLoader:
    """训练配置加载器"""
    
    def __init__(self, training_collector=None):
        self.training_collector = training_collector
    
    def load_from_yaml(self, config_path: str) -> Dict[str, Any]:
        """从 YAML 文件加载配置
        
        Args:
            config_path: 配置文件路径
        
        Returns:
            加载结果
        """
        if not os.path.exists(config_path):
            return {"status": "error", "message": f"配置文件不存在: {config_path}"}
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        return self.load_from_dict(config)
    
    def load_from_dict(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """从字典加载配置
        
        Args:
            config: 配置字典
        
        Returns:
            加载结果
        """
        results = {
            "business_terms": 0,
            "training_sql": 0,
            "training_docs": 0,
            "errors": []
        }
        
        database = config.get("database", "default_db")
        
        if "business_terms" in config:
            terms_count = self._load_business_terms(config["business_terms"])
            results["business_terms"] = terms_count
        
        if self.training_collector:
            if "training_sql" in config:
                sql_count, sql_errors = self._load_training_sql(
                    database, config["training_sql"]
                )
                results["training_sql"] = sql_count
                results["errors"].extend(sql_errors)
            
            if "training_docs" in config:
                docs_count, docs_errors = self._load_training_docs(
                    database, config["training_docs"]
                )
                results["training_docs"] = docs_count
                results["errors"].extend(docs_errors)
        
        results["status"] = "success" if not results["errors"] else "partial"
        return results
    
    def _load_business_terms(self, terms: Dict[str, List[str]]) -> int:
        """加载业务术语映射
        
        将术语添加到意图识别器的词典中
        """
        from intent_recognizer import get_intent_recognizer
        
        recognizer = get_intent_recognizer()
        count = 0
        
        for term, mappings in terms.items():
            if isinstance(mappings, list):
                recognizer.add_business_term(term, mappings)
                count += 1
        
        return count
    
    def _load_training_sql(self, database: str, 
                           sql_list: List[Dict[str, Any]]) -> tuple:
        """加载 SQL 训练数据"""
        count = 0
        errors = []
        
        for item in sql_list:
            try:
                self.training_collector.add_sql(
                    database=database,
                    sql=item.get("sql", ""),
                    question=item.get("question", ""),
                    tables=item.get("tables", []),
                    intent_tags=item.get("intent_tags", [])
                )
                count += 1
            except Exception as e:
                errors.append(f"SQL 加载失败: {item.get('question', 'unknown')} - {str(e)}")
        
        return count, errors
    
    def _load_training_docs(self, database: str,
                            docs_list: List[Dict[str, Any]]) -> tuple:
        """加载文档训练数据"""
        count = 0
        errors = []
        
        for item in docs_list:
            try:
                self.training_collector.add_documentation(
                    database=database,
                    content=item.get("content", ""),
                    title=item.get("title"),
                    source=item.get("source"),
                    intent_tags=item.get("intent_tags", [])
                )
                count += 1
            except Exception as e:
                errors.append(f"文档加载失败: {item.get('title', 'unknown')} - {str(e)}")
        
        return count, errors


def load_training_config(config_path: str, training_collector=None) -> Dict[str, Any]:
    """便捷函数：加载训练配置"""
    loader = TrainingConfigLoader(training_collector)
    return loader.load_from_yaml(config_path)
