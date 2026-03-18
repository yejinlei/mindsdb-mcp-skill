#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据字典管理模块 - 提供更丰富的元数据信息
支持表级、列级、关系级和业务级元数据管理
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import re

class DataDictionary:
    """数据字典管理类"""
    
    def __init__(self):
        """初始化数据字典"""
        self.tables = {}
        self.columns = {}
        self.relationships = {}
        self.business_metadata = {}
        self.last_updated = None
    
    def add_table_metadata(self, table_name: str, metadata: Dict[str, Any]) -> bool:
        """
        添加表级元数据
        :param table_name: 表名
        :param metadata: 元数据字典，包含：
            - description: 表描述
            - business_meaning: 业务含义
            - row_count: 行数
            - update_frequency: 更新频率
            - data_source: 数据来源
            - owner: 数据负责人
            - tags: 标签列表
            - created_time: 创建时间
            - last_modified: 最后修改时间
        :return: 是否成功
        """
        if table_name not in self.tables:
            self.tables[table_name] = {}
        
        self.tables[table_name].update(metadata)
        self.tables[table_name]['last_updated'] = datetime.now().isoformat()
        return True
    
    def add_column_metadata(self, table_name: str, column_name: str, 
                           metadata: Dict[str, Any]) -> bool:
        """
        添加列级元数据
        :param table_name: 表名
        :param column_name: 列名
        :param metadata: 元数据字典，包含：
            - data_type: 数据类型
            - description: 列描述
            - business_meaning: 业务含义
            - nullable: 是否可空
            - primary_key: 是否主键
            - foreign_key: 外键信息
            - unique: 是否唯一
            - default_value: 默认值
            - sample_values: 示例值列表
            - value_range: 值范围
            - data_quality: 数据质量评分
            - tags: 标签列表
        :return: 是否成功
        """
        if table_name not in self.columns:
            self.columns[table_name] = {}
        
        if column_name not in self.columns[table_name]:
            self.columns[table_name][column_name] = {}
        
        self.columns[table_name][column_name].update(metadata)
        self.columns[table_name][column_name]['last_updated'] = datetime.now().isoformat()
        return True
    
    def add_relationship(self, from_table: str, from_column: str, 
                        to_table: str, to_column: str, 
                        relationship_type: str = "foreign_key",
                        metadata: Dict[str, Any] = None) -> bool:
        """
        添加表关系元数据
        :param from_table: 源表
        :param from_column: 源列
        :param to_table: 目标表
        :param to_column: 目标列
        :param relationship_type: 关系类型 (foreign_key, one_to_one, one_to_many, many_to_many)
        :param metadata: 额外元数据
        :return: 是否成功
        """
        if metadata is None:
            metadata = {}
        
        relationship_key = f"{from_table}.{from_column}->{to_table}.{to_column}"
        self.relationships[relationship_key] = {
            'from_table': from_table,
            'from_column': from_column,
            'to_table': to_table,
            'to_column': to_column,
            'relationship_type': relationship_type,
            'description': metadata.get('description', ''),
            'business_rule': metadata.get('business_rule', ''),
            'created_time': datetime.now().isoformat()
        }
        return True
    
    def add_business_metadata(self, domain: str, metadata: Dict[str, Any]) -> bool:
        """
        添加业务级元数据
        :param domain: 业务域名称
        :param metadata: 元数据字典，包含：
            - description: 业务域描述
            - tables: 相关表列表
            - business_rules: 业务规则列表
            - data_governance: 数据治理信息
            - quality_metrics: 质量指标
        :return: 是否成功
        """
        if domain not in self.business_metadata:
            self.business_metadata[domain] = {}
        
        self.business_metadata[domain].update(metadata)
        self.business_metadata[domain]['last_updated'] = datetime.now().isoformat()
        return True
    
    def get_table_metadata(self, table_name: str) -> Optional[Dict[str, Any]]:
        """获取表级元数据"""
        return self.tables.get(table_name)
    
    def get_column_metadata(self, table_name: str, column_name: str) -> Optional[Dict[str, Any]]:
        """获取列级元数据"""
        if table_name in self.columns:
            return self.columns[table_name].get(column_name)
        return None
    
    def get_table_columns(self, table_name: str) -> List[str]:
        """获取表的所有列名"""
        if table_name in self.columns:
            return list(self.columns[table_name].keys())
        return []
    
    def get_relationships(self, table_name: str = None) -> List[Dict[str, Any]]:
        """
        获取关系信息
        :param table_name: 可选，指定表名则只返回该表的关系
        :return: 关系列表
        """
        if table_name:
            return [
                rel for rel in self.relationships.values()
                if rel['from_table'] == table_name or rel['to_table'] == table_name
            ]
        return list(self.relationships.values())
    
    def get_business_metadata(self, domain: str = None) -> Dict[str, Any]:
        """
        获取业务元数据
        :param domain: 可选，指定业务域
        :return: 业务元数据
        """
        if domain:
            return self.business_metadata.get(domain)
        return self.business_metadata
    
    def search_metadata(self, keyword: str) -> Dict[str, Any]:
        """
        搜索元数据
        :param keyword: 搜索关键词
        :return: 匹配的元数据
        """
        results = {
            'tables': [],
            'columns': [],
            'relationships': [],
            'business_domains': []
        }
        
        keyword_lower = keyword.lower()
        
        # 搜索表
        for table_name, table_meta in self.tables.items():
            if (keyword_lower in table_name.lower() or
                any(keyword_lower in str(value).lower() for value in table_meta.values())):
                results['tables'].append({
                    'name': table_name,
                    'metadata': table_meta
                })
        
        # 搜索列
        for table_name, columns in self.columns.items():
            for column_name, column_meta in columns.items():
                if (keyword_lower in column_name.lower() or
                    any(keyword_lower in str(value).lower() for value in column_meta.values())):
                    results['columns'].append({
                        'table': table_name,
                        'column': column_name,
                        'metadata': column_meta
                    })
        
        # 搜索关系
        for rel_key, rel_meta in self.relationships.items():
            if (keyword_lower in rel_key.lower() or
                any(keyword_lower in str(value).lower() for value in rel_meta.values())):
                results['relationships'].append(rel_meta)
        
        # 搜索业务域
        for domain_name, domain_meta in self.business_metadata.items():
            if (keyword_lower in domain_name.lower() or
                any(keyword_lower in str(value).lower() for value in domain_meta.values())):
                results['business_domains'].append({
                    'name': domain_name,
                    'metadata': domain_meta
                })
        
        return results
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'tables': self.tables,
            'columns': self.columns,
            'relationships': self.relationships,
            'business_metadata': self.business_metadata,
            'last_updated': self.last_updated or datetime.now().isoformat()
        }
    
    def from_dict(self, data: Dict[str, Any]) -> bool:
        """从字典格式加载"""
        try:
            self.tables = data.get('tables', {})
            self.columns = data.get('columns', {})
            self.relationships = data.get('relationships', {})
            self.business_metadata = data.get('business_metadata', {})
            self.last_updated = data.get('last_updated')
            return True
        except Exception as e:
            print(f"加载数据字典失败: {e}")
            return False
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    def from_json(self, json_str: str) -> bool:
        """从JSON字符串加载"""
        try:
            data = json.loads(json_str)
            return self.from_dict(data)
        except Exception as e:
            print(f"解析数据字典JSON失败: {e}")
            return False
    
    def save_to_file(self, file_path: str) -> bool:
        """保存到文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.to_json())
            return True
        except Exception as e:
            print(f"保存数据字典文件失败: {e}")
            return False
    
    def load_from_file(self, file_path: str) -> bool:
        """从文件加载"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return self.from_json(f.read())
        except Exception as e:
            print(f"加载数据字典文件失败: {e}")
            return False
    
    def generate_summary(self) -> str:
        """生成数据字典摘要"""
        summary = []
        summary.append(f"数据字典摘要")
        summary.append(f"=" * 50)
        summary.append(f"表数量: {len(self.tables)}")
        summary.append(f"列数量: {sum(len(cols) for cols in self.columns.values())}")
        summary.append(f"关系数量: {len(self.relationships)}")
        summary.append(f"业务域数量: {len(self.business_metadata)}")
        summary.append(f"最后更新: {self.last_updated}")
        summary.append(f"=" * 50)
        
        if self.tables:
            summary.append(f"\n表列表:")
            for table_name, table_meta in self.tables.items():
                desc = table_meta.get('description', '无描述')
                summary.append(f"  - {table_name}: {desc}")
        
        return "\n".join(summary)
    
    def generate_rag_documents(self) -> List[Dict[str, Any]]:
        """
        生成用于RAG的文档
        :return: 文档列表，每个文档包含id、text和metadata
        """
        documents = []
        
        # 生成表级文档
        for table_name, table_meta in self.tables.items():
            doc_text = f"表 {table_name} 的元数据信息："
            doc_text += f" 描述：{table_meta.get('description', '无')}"
            doc_text += f" 业务含义：{table_meta.get('business_meaning', '无')}"
            doc_text += f" 行数：{table_meta.get('row_count', '未知')}"
            doc_text += f" 更新频率：{table_meta.get('update_frequency', '未知')}"
            doc_text += f" 数据来源：{table_meta.get('data_source', '未知')}"
            
            documents.append({
                'id': f"table_{table_name}",
                'text': doc_text,
                'metadata': {
                    'type': 'table',
                    'table_name': table_name,
                    'source': 'data_dictionary'
                }
            })
        
        # 生成列级文档
        for table_name, columns in self.columns.items():
            for column_name, column_meta in columns.items():
                doc_text = f"表 {table_name} 的列 {column_name} 元数据信息："
                doc_text += f" 数据类型：{column_meta.get('data_type', '未知')}"
                doc_text += f" 描述：{column_meta.get('description', '无')}"
                doc_text += f" 业务含义：{column_meta.get('business_meaning', '无')}"
                doc_text += f" 是否可空：{column_meta.get('nullable', '未知')}"
                doc_text += f" 是否主键：{column_meta.get('primary_key', '否')}"
                
                sample_values = column_meta.get('sample_values', [])
                if sample_values:
                    doc_text += f" 示例值：{', '.join(map(str, sample_values[:5]))}"
                
                documents.append({
                    'id': f"column_{table_name}_{column_name}",
                    'text': doc_text,
                    'metadata': {
                        'type': 'column',
                        'table_name': table_name,
                        'column_name': column_name,
                        'source': 'data_dictionary'
                    }
                })
        
        # 生成关系级文档
        for rel_key, rel_meta in self.relationships.items():
            doc_text = f"表关系信息：{rel_meta['from_table']}.{rel_meta['from_column']} "
            doc_text += f"-> {rel_meta['to_table']}.{rel_meta['to_column']}"
            doc_text += f" 关系类型：{rel_meta['relationship_type']}"
            doc_text += f" 描述：{rel_meta.get('description', '无')}"
            doc_text += f" 业务规则：{rel_meta.get('business_rule', '无')}"
            
            documents.append({
                'id': f"relationship_{rel_key}",
                'text': doc_text,
                'metadata': {
                    'type': 'relationship',
                    'from_table': rel_meta['from_table'],
                    'to_table': rel_meta['to_table'],
                    'source': 'data_dictionary'
                }
            })
        
        # 生成业务域文档
        for domain_name, domain_meta in self.business_metadata.items():
            doc_text = f"业务域 {domain_name} 的元数据信息："
            doc_text += f" 描述：{domain_meta.get('description', '无')}"
            doc_text += f" 相关表：{', '.join(domain_meta.get('tables', []))}"
            
            business_rules = domain_meta.get('business_rules', [])
            if business_rules:
                doc_text += f" 业务规则：{'; '.join(business_rules[:3])}"
            
            documents.append({
                'id': f"domain_{domain_name}",
                'text': doc_text,
                'metadata': {
                    'type': 'business_domain',
                    'domain_name': domain_name,
                    'source': 'data_dictionary'
                }
            })
        
        return documents