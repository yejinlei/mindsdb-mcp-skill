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
    
    def get_table_last_updated(self, table_name: str) -> Optional[str]:
        """
        获取表的最后更新时间
        :param table_name: 表名
        :return: 最后更新时间（ISO格式字符串），如果表不存在返回None
        """
        table_meta = self.tables.get(table_name)
        if table_meta:
            return table_meta.get('last_updated')
        return None
    
    def update_table_metadata(self, table_name: str, metadata: Dict[str, Any]) -> bool:
        """
        更新表元数据（增量更新）
        :param table_name: 表名
        :param metadata: 新的元数据
        :return: 是否成功
        """
        if table_name not in self.tables:
            self.tables[table_name] = {}
        
        self.tables[table_name].update(metadata)
        self.tables[table_name]['last_updated'] = datetime.now().isoformat()
        return True
    
    def remove_table(self, table_name: str) -> bool:
        """
        删除表及其所有列元数据
        :param table_name: 表名
        :return: 是否成功
        """
        if table_name in self.tables:
            del self.tables[table_name]
        
        if table_name in self.columns:
            del self.columns[table_name]
        
        # 删除相关的关系
        keys_to_remove = []
        for rel_key in self.relationships:
            if (table_name in self.relationships[rel_key]['from_table'] or
                table_name in self.relationships[rel_key]['to_table']):
                keys_to_remove.append(rel_key)
        
        for key in keys_to_remove:
            del self.relationships[key]
        
        return True
    
    def get_changed_tables(self, since: str = None) -> List[str]:
        """
        获取自指定时间以来变更的表
        :param since: ISO格式的时间字符串，如果为None则返回所有表
        :return: 变更的表名列表
        """
        if since is None:
            return list(self.tables.keys())
        
        changed_tables = []
        for table_name, table_meta in self.tables.items():
            last_updated = table_meta.get('last_updated')
            if last_updated and last_updated > since:
                changed_tables.append(table_name)
        
        return changed_tables
    
    def merge_with_existing(self, new_data_dict: 'DataDictionary', 
                          mode: str = 'replace') -> Dict[str, Any]:
        """
        合并新的数据字典到现有数据字典
        :param new_data_dict: 新的数据字典
        :param mode: 合并模式
            - 'replace': 完全替换（默认）
            - 'merge': 合并更新
            - 'incremental': 增量更新（只更新变更的表）
        :return: 合并统计信息
        """
        stats = {
            'tables_added': 0,
            'tables_updated': 0,
            'tables_removed': 0,
            'columns_added': 0,
            'columns_updated': 0,
            'relationships_added': 0,
            'total_changes': 0
        }
        
        if mode == 'replace':
            # 完全替换
            self.tables = new_data_dict.tables.copy()
            self.columns = new_data_dict.columns.copy()
            self.relationships = new_data_dict.relationships.copy()
            self.business_metadata = new_data_dict.business_metadata.copy()
            self.last_updated = datetime.now().isoformat()
            
            stats['tables_added'] = len(self.tables)
            stats['columns_added'] = sum(len(cols) for cols in self.columns.values())
            stats['relationships_added'] = len(self.relationships)
            stats['total_changes'] = stats['tables_added'] + stats['columns_added'] + stats['relationships_added']
            return stats
        
        elif mode == 'merge':
            # 合并更新
            for table_name, table_meta in new_data_dict.tables.items():
                if table_name in self.tables:
                    # 更新现有表
                    self.tables[table_name].update(table_meta)
                    stats['tables_updated'] += 1
                else:
                    # 添加新表
                    self.tables[table_name] = table_meta.copy()
                    stats['tables_added'] += 1
            
            # 合并列元数据
            for table_name, columns in new_data_dict.columns.items():
                if table_name not in self.columns:
                    self.columns[table_name] = {}
                    stats['columns_added'] += len(columns)
                else:
                    for col_name, col_meta in columns.items():
                        if col_name in self.columns[table_name]:
                            self.columns[table_name][col_name].update(col_meta)
                            stats['columns_updated'] += 1
                        else:
                            self.columns[table_name][col_name] = col_meta.copy()
                            stats['columns_added'] += 1
            
            # 合并关系
            for rel_key, rel_meta in new_data_dict.relationships.items():
                if rel_key not in self.relationships:
                    self.relationships[rel_key] = rel_meta.copy()
                    stats['relationships_added'] += 1
            
            # 合并业务元数据
            for domain_name, domain_meta in new_data_dict.business_metadata.items():
                if domain_name in self.business_metadata:
                    self.business_metadata[domain_name].update(domain_meta)
                else:
                    self.business_metadata[domain_name] = domain_meta.copy()
            
            self.last_updated = datetime.now().isoformat()
            stats['total_changes'] = (stats['tables_added'] + stats['tables_updated'] + 
                                     stats['columns_added'] + stats['columns_updated'] + 
                                     stats['relationships_added'])
            return stats
        
        elif mode == 'incremental':
            # 增量更新（基于时间戳）
            current_time = self.last_updated
            
            for table_name, table_meta in new_data_dict.tables.items():
                new_last_updated = table_meta.get('last_updated', '')
                
                # 如果新数据更新时间晚于当前时间，则更新
                if not current_time or new_last_updated > current_time:
                    if table_name in self.tables:
                        self.tables[table_name].update(table_meta)
                        stats['tables_updated'] += 1
                    else:
                        self.tables[table_name] = table_meta.copy()
                        stats['tables_added'] += 1
            
            # 增量更新列元数据
            for table_name, columns in new_data_dict.columns.items():
                if table_name not in self.columns:
                    self.columns[table_name] = {}
                
                for col_name, col_meta in columns.items():
                    new_col_updated = col_meta.get('last_updated', '')
                    existing_col = self.columns[table_name].get(col_name)
                    
                    if existing_col:
                        existing_col_updated = existing_col.get('last_updated', '')
                        if new_col_updated > existing_col_updated:
                            self.columns[table_name][col_name].update(col_meta)
                            stats['columns_updated'] += 1
                    else:
                        self.columns[table_name][col_name] = col_meta.copy()
                        stats['columns_added'] += 1
            
            # 增量更新关系
            for rel_key, rel_meta in new_data_dict.relationships.items():
                if rel_key not in self.relationships:
                    self.relationships[rel_key] = rel_meta.copy()
                    stats['relationships_added'] += 1
            
            self.last_updated = datetime.now().isoformat()
            stats['total_changes'] = (stats['tables_added'] + stats['tables_updated'] + 
                                     stats['columns_added'] + stats['columns_updated'] + 
                                     stats['relationships_added'])
            return stats
        
        else:
            raise ValueError(f"不支持的合并模式: {mode}")
    
    def get_version(self) -> str:
        """
        获取数据字典版本号
        :return: 版本号（基于last_updated时间戳）
        """
        return self.last_updated or datetime.now().isoformat()
    
    def export_changes(self, since: str) -> Dict[str, Any]:
        """
        导出自指定时间以来的变更
        :param since: ISO格式的时间字符串
        :return: 变更数据
        """
        changes = {
            'since': since,
            'exported_at': datetime.now().isoformat(),
            'tables': {},
            'columns': {},
            'relationships': {},
            'business_metadata': {}
        }
        
        # 导出变更的表
        for table_name, table_meta in self.tables.items():
            last_updated = table_meta.get('last_updated', '')
            if last_updated > since:
                changes['tables'][table_name] = table_meta
        
        # 导出变更的列
        for table_name, columns in self.columns.items():
            for col_name, col_meta in columns.items():
                last_updated = col_meta.get('last_updated', '')
                if last_updated > since:
                    if table_name not in changes['columns']:
                        changes['columns'][table_name] = {}
                    changes['columns'][table_name][col_name] = col_meta
        
        # 导出变更的关系
        for rel_key, rel_meta in self.relationships.items():
            last_updated = rel_meta.get('last_updated', '')
            if last_updated > since:
                changes['relationships'][rel_key] = rel_meta
        
        return changes