#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能基准测试脚本
记录每个测试用例的执行时间和token使用量
"""

import sys
import os
import time
import json
from typing import Dict, Any, List

# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from workflow_rag_build import rag_build_workflow_entry
from workflow_rag_analysis import rag_analysis_workflow_entry


class PerformanceBenchmark:
    """性能基准测试器"""
    
    def __init__(self, evals_file: str):
        """初始化基准测试器"""
        self.evals_file = evals_file
        self.evals = self._load_evals()
        self.results = []
    
    def _load_evals(self) -> List[Dict[str, Any]]:
        """加载测试用例"""
        with open(self.evals_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('evals', [])
    
    def run_eval(self, eval_case: Dict[str, Any]) -> Dict[str, Any]:
        """运行单个测试用例"""
        print(f"\n运行测试用例 {eval_case['id']}: {eval_case['prompt'][:50]}...")
        
        start_time = time.time()
        
        # 根据模块选择工作流
        module = eval_case.get('module')
        action = eval_case.get('action')
        params = eval_case.get('params', {})
        
        try:
            if module == 'db_connector':
                result = self._run_db_connector(action, params)
            elif module == 'workflow_rag_build':
                result = self._run_rag_build(action, params)
            elif module == 'workflow_rag_analysis':
                result = self._run_rag_analysis(action, params)
            elif module == 'nl2sql':
                result = self._run_nl2sql(action, params)
            else:
                result = {
                    'code': -1,
                    'msg': f'Unknown module: {module}'
                }
        except Exception as e:
            result = {
                'code': -1,
                'msg': f'Error: {str(e)}'
            }
        
        end_time = time.time()
        duration_ms = int((end_time - start_time) * 1000)
        
        return {
            'eval_id': eval_case['id'],
            'module': module,
            'action': action,
            'duration_ms': duration_ms,
            'success': result.get('code') == 0,
            'result': result
        }
    
    def _run_db_connector(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """运行数据库连接器测试"""
        from db_connector import get_db_connector
        db = get_db_connector()
        
        if action == 'connect_db':
            return db.connect_database(**params)
        elif action == 'list_databases':
            return db.list_databases(params.get('host', 'localhost'), params.get('port', 47334))
        elif action == 'show_tables':
            return db.show_tables(params['database'], params.get('host', 'localhost'), params.get('port', 47334))
        elif action == 'describe_table':
            return db.describe_table(params['database'], params['table'], params.get('host', 'localhost'), params.get('port', 47334))
        elif action == 'execute_sql':
            return db.execute_sql(params['sql'], params.get('host', 'localhost'), params.get('port', 47334))
        else:
            return {'code': -2, 'msg': f'Unknown action: {action}'}
    
    def _run_rag_build(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """运行RAG构建测试"""
        return rag_build_workflow_entry({'action': action, **params})
    
    def _run_rag_analysis(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """运行RAG分析测试"""
        return rag_analysis_workflow_entry({'action': action, **params})
    
    def _run_nl2sql(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """运行NL2SQL测试"""
        from nl2sql.engine import get_nl2sql_engine
        engine = get_nl2sql_engine(None)
        
        if action == 'test_intent':
            from nl2sql.intent_recognizer import get_intent_recognizer
            recognizer = get_intent_recognizer()
            intent = recognizer.recognize(params['nl_text'])
            return {
                'code': 0,
                'data': {
                    'intent_type': intent.intent_type.value,
                    'target': intent.target,
                    'entities': intent.entities
                }
            }
        elif action == 'extract_schema':
            from nl2sql.schema_extractor import get_schema_extractor
            extractor = get_schema_extractor(None, None)
            result = extractor.extract_from_duckdb(params['db_path'], params['database'])
            return {'code': 0, 'data': result} if result.get('status') == 'success' else {'code': -1, 'msg': 'Schema extraction failed'}
        else:
            return {'code': -2, 'msg': f'Unknown action: {action}'}
    
    def run_all(self, max_evals: int = None) -> List[Dict[str, Any]]:
        """运行所有测试用例"""
        evals_to_run = self.evals[:max_evals] if max_evals else self.evals
        
        print(f"开始运行 {len(evals_to_run)} 个测试用例...")
        print("=" * 70)
        
        for eval_case in evals_to_run:
            result = self.run_eval(eval_case)
            self.results.append(result)
            
            if result['success']:
                print(f"  ✅ 测试用例 {eval_case['id']} 成功 ({result['duration_ms']}ms)")
            else:
                print(f"  ❌ 测试用例 {eval_case['id']} 失败 ({result['duration_ms']}ms)")
        
        return self.results
    
    def generate_report(self) -> Dict[str, Any]:
        """生成性能报告"""
        total_evals = len(self.results)
        successful_evals = sum(1 for r in self.results if r['success'])
        failed_evals = total_evals - successful_evals
        
        total_duration = sum(r['duration_ms'] for r in self.results)
        avg_duration = total_duration / total_evals if total_evals > 0 else 0
        
        # 按模块统计
        module_stats = {}
        for result in self.results:
            module = result['module']
            if module not in module_stats:
                module_stats[module] = {
                    'total': 0,
                    'success': 0,
                    'total_duration': 0
                }
            module_stats[module]['total'] += 1
            if result['success']:
                module_stats[module]['success'] += 1
            module_stats[module]['total_duration'] += result['duration_ms']
        
        # 计算每个模块的平均时间
        for module, stats in module_stats.items():
            stats['avg_duration'] = stats['total_duration'] / stats['total'] if stats['total'] > 0 else 0
            stats['success_rate'] = stats['success'] / stats['total'] if stats['total'] > 0 else 0
        
        return {
            'summary': {
                'total_evals': total_evals,
                'successful_evals': successful_evals,
                'failed_evals': failed_evals,
                'success_rate': successful_evals / total_evals if total_evals > 0 else 0,
                'total_duration_ms': total_duration,
                'avg_duration_ms': avg_duration
            },
            'module_stats': module_stats,
            'detailed_results': self.results
        }
    
    def save_report(self, output_file: str):
        """保存性能报告"""
        report = self.generate_report()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n性能报告已保存到: {output_file}")
        print(f"总测试数: {report['summary']['total_evals']}")
        print(f"成功率: {report['summary']['success_rate']:.2%}")
        print(f"平均执行时间: {report['summary']['avg_duration_ms']:.2f}ms")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MindsDB MCP Skill 性能基准测试')
    parser.add_argument('--evals', type=str, default='evals/evals_with_assertions.json',
                       help='测试用例文件路径')
    parser.add_argument('--output', type=str, default='benchmark_report.json',
                       help='输出报告文件路径')
    parser.add_argument('--max-evals', type=int, default=None,
                       help='最大运行测试用例数量')
    
    args = parser.parse_args()
    
    # 运行基准测试
    benchmark = PerformanceBenchmark(args.evals)
    benchmark.run_all(args.max_evals)
    
    # 生成并保存报告
    benchmark.save_report(args.output)


if __name__ == '__main__':
    main()
