#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能查询模块 - 基于元数据理解用户意图并自动构建查询

这个模块展示了如何固化经验：
1. 自动提取数据库元数据
2. 基于元数据理解用户问题
3. 自动匹配合适的表和字段
4. 生成并执行SQL查询
"""

import os
import sys
import json
import re
from typing import Dict, Any, List, Optional, Tuple
import duckdb

# 导入元数据提取器
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metadata_extractor import MetadataExtractor, extract_metadata_from_duckdb


class IntelligentQueryEngine:
    """智能查询引擎 - 基于元数据自动理解查询意图"""
    
    def __init__(self, db_path: str, metadata_path: str = None):
        """
        初始化智能查询引擎
        
        Args:
            db_path: 数据库文件路径
            metadata_path: 元数据文件路径（可选，如果不存在会自动提取）
        """
        self.db_path = db_path
        self.metadata_path = metadata_path or db_path.replace('.duckdb', '_metadata.json')
        self.data_dictionary = None
        self.conn = None
        
        self._load_or_extract_metadata()
        self._connect_db()
    
    def _load_or_extract_metadata(self):
        """加载或提取元数据"""
        if os.path.exists(self.metadata_path):
            print(f"加载已有元数据: {self.metadata_path}")
            with open(self.metadata_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 重建DataDictionary
            from metadata_extractor import DataDictionary
            self.data_dictionary = DataDictionary()
            self.data_dictionary.tables = data.get('tables', {})
            self.data_dictionary.columns = data.get('columns', {})
            self.data_dictionary.relationships = data.get('relationships', {})
            self.data_dictionary.business_metadata = data.get('business_metadata', {})
        else:
            print(f"提取元数据...")
            self.data_dictionary, _ = extract_metadata_from_duckdb(
                self.db_path, 
                self.metadata_path
            )
    
    def _connect_db(self):
        """连接数据库"""
        self.conn = duckdb.connect(self.db_path, read_only=True)
    
    def understand_question(self, question: str) -> Dict[str, Any]:
        """
        理解用户问题，提取关键信息
        
        Args:
            question: 用户的自然语言问题
            
        Returns:
            解析结果，包含意图、关键词、匹配到的表和字段
        """
        question_lower = question.lower()
        
        # 1. 识别查询意图
        intent = self._detect_intent(question_lower)
        
        # 2. 提取关键词
        keywords = self._extract_keywords(question_lower)
        
        # 3. 匹配相关表
        matched_tables = self._match_tables(keywords)
        
        # 4. 匹配相关字段
        matched_columns = self._match_columns(keywords, matched_tables)
        
        return {
            'intent': intent,
            'keywords': keywords,
            'matched_tables': matched_tables,
            'matched_columns': matched_columns,
            'original_question': question
        }
    
    def _detect_intent(self, question: str) -> str:
        """检测查询意图"""
        # 计数类问题
        count_patterns = ['多少', '几个', '数量', '总数', 'count', 'how many']
        # 列表类问题
        list_patterns = ['哪些', '列表', '所有', '全部', 'list', 'all']
        # 统计类问题
        stats_patterns = ['统计', '汇总', '分析', '分布', 'statistics', 'summary']
        # 详情类问题
        detail_patterns = ['详情', '信息', '内容', 'detail', 'info']
        
        for pattern in count_patterns:
            if pattern in question:
                return 'count'
        
        for pattern in list_patterns:
            if pattern in question:
                return 'list'
        
        for pattern in stats_patterns:
            if pattern in question:
                return 'statistics'
        
        for pattern in detail_patterns:
            if pattern in question:
                return 'detail'
        
        return 'general'
    
    def _extract_keywords(self, question: str) -> List[str]:
        """提取关键词"""
        # 预定义的关键词映射
        keyword_mappings = {
            # 部门相关
            '部门': ['department', 'dept', '部门'],
            '组织': ['department', 'org', '组织'],
            
            # 人员相关
            '人': ['human_resource', 'hr', 'people', 'person', '员工', '人员'],
            '员工': ['human_resource', 'hr', 'employee', '员工'],
            '人力': ['human_resource', 'hr', '人力资源'],
            
            # 项目相关
            '项目': ['project', '项目'],
            '进度': ['project', 'progress', '进度'],
            
            # 财务相关
            '财务': ['finance', '财务', '资金', '金额'],
            '钱': ['finance', 'amount', '资金'],
            
            # 周报相关
            '周报': ['weekly_report', 'report', '周报'],
            '报告': ['weekly_report', 'report', '报告'],
            
            # 问题相关
            '问题': ['issues', 'problem', '卡点', '风险'],
            '卡点': ['issues', 'blocker', '卡点'],
            '风险': ['issues', 'risk', '风险'],
        }
        
        matched_keywords = []
        for keyword, mappings in keyword_mappings.items():
            if keyword in question:
                matched_keywords.extend(mappings)
        
        return list(set(matched_keywords))
    
    def _match_tables(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """根据关键词匹配表"""
        matched = []
        
        for table_name, table_meta in self.data_dictionary.tables.items():
            score = 0
            
            # 表名匹配
            for keyword in keywords:
                if keyword.lower() in table_name.lower():
                    score += 10
            
            # 标签匹配
            tags = table_meta.get('tags', [])
            for keyword in keywords:
                if any(keyword.lower() in tag.lower() for tag in tags):
                    score += 5
            
            # 业务含义匹配
            business_meaning = table_meta.get('business_meaning', '')
            for keyword in keywords:
                if keyword.lower() in business_meaning.lower():
                    score += 3
            
            if score > 0:
                matched.append({
                    'table_name': table_name,
                    'score': score,
                    'metadata': table_meta
                })
        
        # 按匹配分数排序
        matched.sort(key=lambda x: x['score'], reverse=True)
        return matched
    
    def _match_columns(self, keywords: List[str], matched_tables: List[Dict]) -> List[Dict[str, Any]]:
        """根据关键词匹配列"""
        matched = []
        
        # 只在已匹配的表中查找列
        table_names = [t['table_name'] for t in matched_tables]
        
        for table_name in table_names:
            if table_name not in self.data_dictionary.columns:
                continue
            
            for column_name, column_meta in self.data_dictionary.columns[table_name].items():
                score = 0
                
                # 列名匹配
                for keyword in keywords:
                    if keyword.lower() in column_name.lower():
                        score += 10
                
                # 标签匹配
                tags = column_meta.get('tags', [])
                for keyword in keywords:
                    if any(keyword.lower() in tag.lower() for tag in tags):
                        score += 5
                
                # 业务含义匹配
                business_meaning = column_meta.get('business_meaning', '')
                for keyword in keywords:
                    if keyword.lower() in business_meaning.lower():
                        score += 3
                
                if score > 0:
                    matched.append({
                        'table_name': table_name,
                        'column_name': column_name,
                        'score': score,
                        'metadata': column_meta
                    })
        
        # 按匹配分数排序
        matched.sort(key=lambda x: x['score'], reverse=True)
        return matched
    
    def generate_sql(self, understanding: Dict[str, Any]) -> str:
        """
        根据理解结果生成SQL
        
        Args:
            understanding: understand_question的返回结果
            
        Returns:
            生成的SQL语句
        """
        intent = understanding['intent']
        matched_tables = understanding['matched_tables']
        matched_columns = understanding['matched_columns']
        
        if not matched_tables:
            return "-- 无法匹配到相关表"
        
        # 选择最佳匹配的表
        primary_table = matched_tables[0]['table_name']
        
        # 根据意图生成SQL
        if intent == 'count':
            return f"SELECT COUNT(*) FROM {primary_table}"
        
        elif intent == 'list':
            if matched_columns:
                # 选择最佳匹配的列
                primary_column = matched_columns[0]
                return f"SELECT DISTINCT {primary_column['column_name']} FROM {primary_table} LIMIT 20"
            else:
                return f"SELECT * FROM {primary_table} LIMIT 10"
        
        elif intent == 'statistics':
            # 生成统计查询
            if matched_columns:
                col = matched_columns[0]
                return f"""
                SELECT 
                    {col['column_name']},
                    COUNT(*) as count
                FROM {primary_table}
                GROUP BY {col['column_name']}
                ORDER BY count DESC
                LIMIT 10
                """.strip()
            else:
                return f"SELECT COUNT(*) as total FROM {primary_table}"
        
        else:  # general or detail
            return f"SELECT * FROM {primary_table} LIMIT 10"
    
    def execute_query(self, sql: str) -> Tuple[List, List]:
        """
        执行SQL查询
        
        Returns:
            (列名列表, 数据列表)
        """
        try:
            result = self.conn.execute(sql).fetchall()
            columns = [desc[0] for desc in self.conn.description] if self.conn.description else []
            return columns, result
        except Exception as e:
            print(f"查询执行失败: {e}")
            return [], []
    
    def query(self, question: str) -> Dict[str, Any]:
        """
        主查询接口 - 一站式智能查询
        
        Args:
            question: 自然语言问题
            
        Returns:
            包含理解结果、SQL和查询结果的字典
        """
        print(f"问题: {question}")
        print("-" * 60)
        
        # 1. 理解问题
        understanding = self.understand_question(question)
        print(f"意图: {understanding['intent']}")
        print(f"关键词: {understanding['keywords']}")
        print(f"匹配表: {[t['table_name'] for t in understanding['matched_tables'][:3]]}")
        
        # 2. 生成SQL
        sql = self.generate_sql(understanding)
        print(f"\n生成SQL:\n{sql}")
        
        # 3. 执行查询
        columns, data = self.execute_query(sql)
        
        return {
            'understanding': understanding,
            'sql': sql,
            'columns': columns,
            'data': data
        }
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()


def demo():
    """演示智能查询"""
    db_path = r"f:\src\tmp\周报智能分析\weekly_report_warehouse.duckdb"
    
    print("=" * 70)
    print("智能查询引擎演示")
    print("=" * 70)
    
    engine = IntelligentQueryEngine(db_path)
    
    # 演示问题列表
    questions = [
        "总共几个部门",
        "有多少人",
        "所有卡点",
        "项目进度如何",
        "财务状况",
    ]
    
    for question in questions:
        print("\n" + "=" * 70)
        result = engine.query(question)
        
        print(f"\n查询结果:")
        if result['data']:
            for row in result['data'][:5]:
                print(f"  {row}")
        else:
            print("  无数据")
    
    engine.close()


if __name__ == "__main__":
    demo()
