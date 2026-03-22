#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元数据自动提取模块 - 自动从数据库中提取表结构、列信息、样本数据等元数据
支持DuckDB、MySQL、PostgreSQL等多种数据库

使用示例:
    from metadata_extractor import extract_metadata_from_duckdb
    
    # 提取元数据
    data_dict, stats = extract_metadata_from_duckdb(
        db_path="path/to/database.duckdb",
        save_path="path/to/metadata.json"
    )
    
    # 查看提取的元数据
    print(data_dict.generate_summary())
"""

import os
import sys
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date
import re
import json

# 尝试导入data_dictionary模块
try:
    skill_path = "C:/Users/T480/.trae-cn/skills/mindsdb-mcp-skill/scripts"
    if skill_path not in sys.path:
        sys.path.insert(0, skill_path)
    from data_dictionary import DataDictionary
except ImportError:
    # 如果无法导入，使用简化版DataDictionary
    class DataDictionary:
        def __init__(self):
            self.tables = {}
            self.columns = {}
            self.relationships = {}
            self.business_metadata = {}
        
        def add_table_metadata(self, table_name: str, metadata: Dict[str, Any]):
            self.tables[table_name] = metadata
        
        def add_column_metadata(self, table_name: str, column_name: str, metadata: Dict[str, Any]):
            if table_name not in self.columns:
                self.columns[table_name] = {}
            self.columns[table_name][column_name] = metadata
        
        def add_relationship(self, from_table: str, from_column: str, 
                            to_table: str, to_column: str, 
                            relationship_type: str, metadata: Dict[str, Any]):
            key = f"{from_table}.{from_column}->{to_table}.{to_column}"
            self.relationships[key] = {
                'from_table': from_table,
                'from_column': from_column,
                'to_table': to_table,
                'to_column': to_column,
                'relationship_type': relationship_type,
                **metadata
            }
        
        def add_business_metadata(self, domain: str, metadata: Dict[str, Any]):
            self.business_metadata[domain] = metadata
        
        def get_table_metadata(self, table_name: str):
            return self.tables.get(table_name)
        
        def get_table_columns(self, table_name: str):
            return list(self.columns.get(table_name, {}).keys())
        
        def get_column_metadata(self, table_name: str, column_name: str):
            return self.columns.get(table_name, {}).get(column_name)
        
        def generate_summary(self) -> str:
            summary = []
            summary.append(f"数据字典摘要")
            summary.append(f"=" * 50)
            summary.append(f"表数量: {len(self.tables)}")
            summary.append(f"列数量: {sum(len(cols) for cols in self.columns.values())}")
            summary.append(f"关系数量: {len(self.relationships)}")
            summary.append(f"业务域数量: {len(self.business_metadata)}")
            summary.append(f"=" * 50)
            
            if self.tables:
                summary.append(f"\n表列表:")
                for table_name, table_meta in self.tables.items():
                    desc = table_meta.get('business_meaning', '无描述')
                    row_count = table_meta.get('row_count', '未知')
                    summary.append(f"  - {table_name} ({row_count}行): {desc}")
            
            return "\n".join(summary)
        
        def save_to_file(self, file_path: str) -> bool:
            try:
                data = {
                    'tables': self.tables,
                    'columns': self.columns,
                    'relationships': self.relationships,
                    'business_metadata': self.business_metadata,
                    'last_updated': datetime.now().isoformat()
                }
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2, default=str)
                return True
            except Exception as e:
                print(f"保存失败: {e}")
                # 尝试修复日期序列化问题
                try:
                    data = {
                        'tables': self.tables,
                        'columns': self.columns,
                        'relationships': self.relationships,
                        'business_metadata': self.business_metadata,
                        'last_updated': datetime.now().isoformat()
                    }
                    # 递归转换日期类型
                    def convert_dates(obj):
                        if isinstance(obj, (datetime, date)):
                            return obj.isoformat()
                        elif isinstance(obj, dict):
                            return {k: convert_dates(v) for k, v in obj.items()}
                        elif isinstance(obj, list):
                            return [convert_dates(item) for item in obj]
                        else:
                            return obj
                    data = convert_dates(data)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    return True
                except Exception as e2:
                    print(f"修复后保存仍然失败: {e2}")
                    return False


class MetadataExtractor:
    """元数据提取器 - 自动从数据库提取元数据"""
    
    def __init__(self):
        self.data_dictionary = DataDictionary()
        self.extraction_stats = {
            'tables_extracted': 0,
            'columns_extracted': 0,
            'relationships_detected': 0,
            'sample_rows_collected': 0
        }
    
    def extract_from_duckdb(self, db_path: str, 
                           existing_data_dict: DataDictionary = None,
                           mode: str = 'full') -> DataDictionary:
        """
        从DuckDB数据库提取元数据
        
        Args:
            db_path: DuckDB数据库文件路径
            existing_data_dict: 现有的数据字典（用于增量更新）
            mode: 提取模式
                - 'full': 全量提取（默认）
                - 'incremental': 增量提取（基于时间戳）
            
        Returns:
            填充好的DataDictionary对象
        """
        try:
            import duckdb
            
            conn = duckdb.connect(db_path, read_only=True)
            
            if mode == 'full' or existing_data_dict is None:
                # 全量提取
                self.data_dictionary = DataDictionary()
            else:
                # 增量提取：使用现有数据字典
                self.data_dictionary = existing_data_dict
            
            # 获取所有表
            tables = conn.execute("SHOW TABLES").fetchall()
            table_names = [table_row[0] for table_row in tables]
            
            if mode == 'incremental':
                # 增量模式：只处理变更的表
                last_updated = existing_data_dict.last_updated
                changed_tables = self._get_changed_tables(conn, table_names, last_updated)
                print(f"增量提取：发现 {len(changed_tables)} 个变更的表")
                
                for table_name in changed_tables:
                    self._extract_table_metadata(conn, table_name)
                    self._extract_columns_metadata(conn, table_name)
                    self._extract_sample_data(conn, table_name)
            else:
                # 全量模式：处理所有表
                for table_name in table_names:
                    self._extract_table_metadata(conn, table_name)
                    self._extract_columns_metadata(conn, table_name)
                    self._extract_sample_data(conn, table_name)
            
            # 2. 检测表关系
            if mode == 'full':
                self._detect_relationships(conn)
            else:
                # 增量模式：只检测变更表的关系
                self._detect_relationships_incremental(conn, table_names)
            
            # 3. 推断业务域
            if mode == 'full':
                self._infer_business_domains()
            else:
                # 增量模式：更新业务域
                self._infer_business_domains()
            
            conn.close()
            
            return self.data_dictionary
            
        except Exception as e:
            print(f"从DuckDB提取元数据失败: {e}")
            raise
    
    def _get_changed_tables(self, conn, table_names: List[str], 
                          since: str = None) -> List[str]:
        """
        获取自指定时间以来变更的表
        :param conn: 数据库连接
        :param table_names: 所有表名
        :param since: ISO格式的时间字符串
        :return: 变更的表名列表
        """
        if since is None:
            return table_names
        
        changed_tables = []
        
        for table_name in table_names:
            try:
                # 尝试获取表的最后修改时间
                # DuckDB 不直接提供表的修改时间，使用行数变化作为替代
                result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
                current_row_count = result[0] if result else 0
                
                # 检查现有数据字典中的行数
                existing_meta = self.data_dictionary.get_table_metadata(table_name)
                if existing_meta:
                    existing_row_count = existing_meta.get('row_count', 0)
                    # 如果行数变化，认为表有变更
                    if current_row_count != existing_row_count:
                        changed_tables.append(table_name)
                        print(f"  表 {table_name} 行数变化: {existing_row_count} -> {current_row_count}")
                else:
                    # 新表
                    changed_tables.append(table_name)
                    print(f"  新表: {table_name}")
            except Exception as e:
                print(f"  检查表 {table_name} 变更失败: {e}")
                # 出错时保守处理，认为表有变更
                changed_tables.append(table_name)
        
        return changed_tables
    
    def _detect_relationships_incremental(self, conn, table_names: List[str]):
        """
        增量检测表关系（只检测变更表的关系）
        :param conn: 数据库连接
        :param table_names: 表名列表
        """
        try:
            # 只检测变更表的关系
            for table_name in table_names:
                # 检查外键关系
                columns_info = conn.execute(f"DESCRIBE {table_name}").fetchall()
                
                for col_info in columns_info:
                    column_name = col_info[0]
                    
                    # 检测外键关系
                    if column_name.lower().endswith('_id') and not column_name.lower() == 'id':
                        # 推断目标表名
                        target_table = column_name[:-3]  # 移除 '_id'
                        
                        # 检查目标表是否存在
                        target_tables = [t[0] for t in conn.execute("SHOW TABLES").fetchall()]
                        if target_table in target_tables:
                            self.data_dictionary.add_relationship(
                                from_table=table_name,
                                from_column=column_name,
                                to_table=target_table,
                                to_column='id',
                                relationship_type='foreign_key',
                                metadata={
                                    'description': f'{table_name}.{column_name} 引用 {target_table}.id',
                                    'business_rule': '一对多关系'
                                }
                            )
                            self.extraction_stats['relationships_detected'] += 1
            
        except Exception as e:
            print(f"增量检测表关系失败: {e}")
    
    def _extract_table_metadata(self, conn, table_name: str):
        """提取表级元数据"""
        try:
            # 获取行数
            row_count_result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            row_count = row_count_result[0] if row_count_result else 0
            
            # 推断业务含义
            business_meaning = self._infer_table_business_meaning(table_name)
            
            # 添加到数据字典
            self.data_dictionary.add_table_metadata(
                table_name=table_name,
                metadata={
                    'description': f'表 {table_name}',
                    'business_meaning': business_meaning,
                    'row_count': row_count,
                    'update_frequency': '未知',
                    'data_source': 'DuckDB数据库',
                    'owner': '未知',
                    'tags': self._generate_table_tags(table_name),
                    'last_modified': datetime.now().isoformat()
                }
            )
            
            self.extraction_stats['tables_extracted'] += 1
            
        except Exception as e:
            print(f"提取表 {table_name} 元数据失败: {e}")
    
    def _extract_columns_metadata(self, conn, table_name: str):
        """提取列级元数据"""
        try:
            # 获取列信息
            columns_info = conn.execute(f"DESCRIBE {table_name}").fetchall()
            
            for col_info in columns_info:
                column_name = col_info[0]
                data_type = col_info[1] if len(col_info) > 1 else '未知'
                nullable = col_info[2] if len(col_info) > 2 else True
                
                # 推断业务含义
                business_meaning = self._infer_column_business_meaning(column_name, table_name)
                
                # 判断是否为主键或外键
                is_primary_key = column_name.lower() in ['id', f'{table_name}_id'.lower()]
                is_foreign_key = column_name.lower().endswith('_id') and not is_primary_key
                
                # 获取样本值
                sample_values = self._get_column_samples(conn, table_name, column_name)
                
                self.data_dictionary.add_column_metadata(
                    table_name=table_name,
                    column_name=column_name,
                    metadata={
                        'data_type': data_type,
                        'description': f'列 {column_name}',
                        'business_meaning': business_meaning,
                        'nullable': nullable,
                        'primary_key': is_primary_key,
                        'foreign_key': is_foreign_key,
                        'unique': is_primary_key,
                        'sample_values': sample_values[:5] if sample_values else [],
                        'tags': self._generate_column_tags(column_name, data_type)
                    }
                )
                
                self.extraction_stats['columns_extracted'] += 1
                
        except Exception as e:
            print(f"提取表 {table_name} 列元数据失败: {e}")
    
    def _extract_sample_data(self, conn, table_name: str, limit: int = 5):
        """提取样本数据"""
        try:
            sample_data = conn.execute(f"SELECT * FROM {table_name} LIMIT {limit}").fetchall()
            
            # 存储样本数据到表元数据中
            table_meta = self.data_dictionary.get_table_metadata(table_name)
            if table_meta:
                columns = self.data_dictionary.get_table_columns(table_name)
                table_meta['sample_data'] = [
                    dict(zip(columns, row))
                    for row in sample_data
                ]
                self.extraction_stats['sample_rows_collected'] += len(sample_data)
                
        except Exception as e:
            print(f"提取表 {table_name} 样本数据失败: {e}")
    
    def _detect_relationships(self, conn):
        """检测表之间的关系"""
        try:
            tables = list(self.data_dictionary.tables.keys())
            
            for table_name in tables:
                columns = self.data_dictionary.get_table_columns(table_name)
                
                for column_name in columns:
                    column_meta = self.data_dictionary.get_column_metadata(table_name, column_name)
                    
                    # 检测外键关系 (列名以_id结尾)
                    if column_name.lower().endswith('_id') and not column_meta.get('primary_key', False):
                        # 推断关联表名
                        referenced_table = column_name.lower().replace('_id', '')
                        
                        # 检查是否存在对应的表
                        for ref_table in tables:
                            if ref_table.lower() == referenced_table or \
                               ref_table.lower().endswith(referenced_table):
                                self.data_dictionary.add_relationship(
                                    from_table=table_name,
                                    from_column=column_name,
                                    to_table=ref_table,
                                    to_column='id',
                                    relationship_type='foreign_key',
                                    metadata={
                                        'description': f'{table_name}.{column_name} 引用 {ref_table}.id',
                                        'business_rule': f'外键关联',
                                        'detected_by': 'auto_detection'
                                    }
                                )
                                self.extraction_stats['relationships_detected'] += 1
                                break
                                
        except Exception as e:
            print(f"检测表关系失败: {e}")
    
    def _infer_table_business_meaning(self, table_name: str) -> str:
        """推断表的业务含义"""
        # 基于表名前缀推断
        patterns = {
            r'^ods?_.*': 'ODS层 - 操作数据存储',
            r'^odw?_.*': 'ODW层 - 数据仓库',
            r'^dim_.*': '维度表',
            r'^fact_.*': '事实表',
            r'^stg_.*': 'STG层 - 数据暂存',
            r'^report_.*': '报表数据',
            r'^analysis_.*': '分析数据',
            r'^log_.*': '日志数据',
            r'^config_.*': '配置数据',
            r'^user.*': '用户相关数据',
            r'^order.*': '订单相关数据',
            r'^product.*': '产品相关数据',
        }
        
        for pattern, meaning in patterns.items():
            if re.match(pattern, table_name, re.IGNORECASE):
                return meaning
        
        # 基于关键词推断
        keywords = {
            'department': '部门信息',
            'project': '项目信息',
            'user': '用户信息',
            'finance': '财务数据',
            'hr': '人力资源',
            'report': '报告/报表',
            'weekly': '周报数据',
            'log': '日志数据',
        }
        
        for keyword, meaning in keywords.items():
            if keyword in table_name.lower():
                return meaning
        
        return '业务数据表'
    
    def _infer_column_business_meaning(self, column_name: str, table_name: str) -> str:
        """推断列的业务含义"""
        patterns = {
            r'^id$': '主键ID',
            r'.*_id$': '外键ID',
            r'^name$': '名称',
            r'.*_name$': '名称',
            r'^status$': '状态',
            r'.*_status$': '状态',
            r'^type$': '类型',
            r'.*_type$': '类型',
            r'^created_at$': '创建时间',
            r'^updated_at$': '更新时间',
            r'^description$': '描述',
            r'.*_description$': '描述',
            r'^amount$': '金额',
            r'.*_amount$': '金额/数量',
            r'^count$': '数量',
            r'.*_count$': '数量',
            r'^progress$': '进度',
            r'.*_progress$': '进度',
            r'^content$': '内容',
            r'.*_content$': '内容',
        }
        
        for pattern, meaning in patterns.items():
            if re.match(pattern, column_name, re.IGNORECASE):
                return meaning
        
        return f'{column_name} 字段'
    
    def _get_column_samples(self, conn, table_name: str, column_name: str, limit: int = 5) -> List[Any]:
        """获取列的样本值"""
        try:
            samples = conn.execute(
                f"SELECT DISTINCT {column_name} FROM {table_name} WHERE {column_name} IS NOT NULL LIMIT {limit}"
            ).fetchall()
            return [row[0] for row in samples]
        except:
            return []
    
    def _generate_table_tags(self, table_name: str) -> List[str]:
        """生成表标签"""
        tags = []
        
        if 'weekly' in table_name.lower() or 'report' in table_name.lower():
            tags.append('周报')
        if 'project' in table_name.lower():
            tags.append('项目')
        if 'department' in table_name.lower():
            tags.append('部门')
        if 'finance' in table_name.lower():
            tags.append('财务')
        if 'hr' in table_name.lower() or 'human' in table_name.lower():
            tags.append('人力资源')
        if 'ods' in table_name.lower():
            tags.append('ODS')
        if 'odw' in table_name.lower():
            tags.append('ODW')
        
        return tags
    
    def _generate_column_tags(self, column_name: str, data_type: str) -> List[str]:
        """生成列标签"""
        tags = []
        
        if column_name.lower().endswith('_id'):
            tags.append('ID')
        if 'time' in column_name.lower() or 'date' in column_name.lower():
            tags.append('时间')
        if 'status' in column_name.lower():
            tags.append('状态')
        if 'type' in column_name.lower():
            tags.append('类型')
        if 'varchar' in data_type.lower() or 'string' in data_type.lower():
            tags.append('文本')
        if 'int' in data_type.lower():
            tags.append('整数')
        if 'float' in data_type.lower() or 'double' in data_type.lower() or 'decimal' in data_type.lower():
            tags.append('数值')
        
        return tags
    
    def _infer_business_domains(self):
        """推断业务域"""
        tables = list(self.data_dictionary.tables.keys())
        
        # 按关键词分组
        domain_mappings = {
            '项目管理': ['project', '项目'],
            '人力资源': ['hr', 'human_resource', '人员', '员工'],
            '财务管理': ['finance', '财务', '资金'],
            '部门组织': ['department', '部门', '组织'],
            '周报管理': ['weekly', 'report', '周报', '报告'],
        }
        
        for domain_name, keywords in domain_mappings.items():
            related_tables = []
            
            for table_name in tables:
                if any(keyword in table_name.lower() for keyword in keywords):
                    related_tables.append(table_name)
            
            if related_tables:
                self.data_dictionary.add_business_metadata(
                    domain=domain_name,
                    metadata={
                        'description': f'{domain_name}相关业务数据',
                        'tables': related_tables,
                        'business_rules': [],
                        'detected_by': 'auto_inference'
                    }
                )
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """获取提取统计信息"""
        return {
            **self.extraction_stats,
            'tables_in_dictionary': len(self.data_dictionary.tables),
            'columns_in_dictionary': sum(
                len(cols) for cols in self.data_dictionary.columns.values()
            ),
            'relationships_in_dictionary': len(self.data_dictionary.relationships),
            'business_domains_in_dictionary': len(self.data_dictionary.business_metadata)
        }
    
    def save_to_file(self, file_path: str) -> bool:
        """保存数据字典到文件"""
        return self.data_dictionary.save_to_file(file_path)


# 便捷函数
def extract_metadata_from_duckdb(db_path: str, save_path: str = None) -> Tuple[DataDictionary, Dict]:
    """
    从DuckDB数据库提取元数据的便捷函数
    
    Args:
        db_path: DuckDB数据库文件路径
        save_path: 可选，保存数据字典的文件路径
        
    Returns:
        (DataDictionary对象, 提取统计信息)
    """
    extractor = MetadataExtractor()
    data_dict = extractor.extract_from_duckdb(db_path)
    stats = extractor.get_extraction_stats()
    
    if save_path:
        extractor.save_to_file(save_path)
        print(f"数据字典已保存到: {save_path}")
    
    return data_dict, stats


if __name__ == "__main__":
    import argparse
    
    # 测试代码
    parser = argparse.ArgumentParser(description="从数据库提取元数据")
    parser.add_argument("--db-path", required=True, help="数据库文件路径")
    parser.add_argument("--save-path", required=True, help="保存路径")
    
    args = parser.parse_args()
    
    db_path = args.db_path
    save_path = args.save_path
    
    print("开始提取元数据...")
    data_dict, stats = extract_metadata_from_duckdb(db_path, save_path)
    
    print("\n提取统计:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n数据字典摘要:")
    print(data_dict.generate_summary())
