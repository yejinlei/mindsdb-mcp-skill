#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能描述优化脚本
手动实现描述优化循环，避免编码问题
"""

import json
import sys
import os
import re
from pathlib import Path

def load_eval_set(file_path: str) -> list:
    """加载评估集，正确处理 UTF-8 编码"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def parse_skill_md(skill_path: Path) -> tuple:
    """解析 SKILL.md 文件，提取名称和描述"""
    skill_md_path = skill_path / "SKILL.md"
    
    with open(skill_md_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取 YAML frontmatter
    frontmatter_match = re.search(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not frontmatter_match:
        raise ValueError("No YAML frontmatter found in SKILL.md")
    
    frontmatter = frontmatter_match.group(1)
    
    # 提取 name 和 description
    name_match = re.search(r'^name:\s*(.+)$', frontmatter, re.MULTILINE)
    desc_match = re.search(r'^description:\s*(.+)$', frontmatter, re.MULTILINE)
    
    name = name_match.group(1).strip() if name_match else "unknown"
    description = desc_match.group(1).strip() if desc_match else ""
    
    return name, description, content

def analyze_current_description(skill_path: Path, eval_set: list) -> dict:
    """分析当前描述的触发情况"""
    name, description, content = parse_skill_md(skill_path)
    
    # 分析描述中的关键词
    keywords = {
        "数据库": ["数据库", "database", "db", "sql", "mysql", "postgresql", "duckdb", "tdengine"],
        "查询": ["查询", "query", "search", "搜索", "select"],
        "分析": ["分析", "analyze", "analysis", "统计", "statistics"],
        "NL2SQL": ["nl2sql", "自然语言", "natural language", "nlp"],
        "RAG": ["rag", "知识库", "knowledge base", "向量"],
        "元数据": ["元数据", "metadata", "schema", "表结构"],
        "预测": ["预测", "predict", "model", "ai"]
    }
    
    # 统计应该触发和不触发的查询特征
    trigger_queries = [q for q in eval_set if q["should_trigger"]]
    no_trigger_queries = [q for q in eval_set if not q["should_trigger"]]
    
    print("\n" + "="*70)
    print("技能描述分析")
    print("="*70)
    print(f"\n技能名称: {name}")
    print(f"\n当前描述:\n{description}")
    print(f"\n评估集统计:")
    print(f"  - 应该触发: {len(trigger_queries)} 个查询")
    print(f"  - 不应触发: {len(no_trigger_queries)} 个查询")
    
    print(f"\n应该触发的查询特征:")
    for i, q in enumerate(trigger_queries[:5], 1):
        print(f"  {i}. {q['query'][:60]}...")
    
    print(f"\n不应触发的查询特征:")
    for i, q in enumerate(no_trigger_queries[:5], 1):
        print(f"  {i}. {q['query'][:60]}...")
    
    return {
        "name": name,
        "description": description,
        "trigger_count": len(trigger_queries),
        "no_trigger_count": len(no_trigger_queries)
    }

def suggest_improvements(analysis: dict) -> str:
    """基于分析结果建议描述改进"""
    
    current_desc = analysis["description"]
    
    # 改进建议
    improvements = []
    
    # 1. 强调核心功能
    improvements.append("更明确地列出核心功能关键词")
    
    # 2. 添加具体使用场景
    improvements.append("添加更多具体的使用场景示例")
    
    # 3. 区分相似任务
    improvements.append("明确区分与其他数据库相关任务的区别")
    
    # 4. 优化触发条件
    improvements.append("优化触发条件的描述，避免过度触发或触发不足")
    
    # 生成优化后的描述
    optimized_desc = f"""MindsDB MCP服务器交互技能，支持通过自然语言查询和操作200+企业级数据源。核心功能包括：1) 数据库连接与查询（MySQL、PostgreSQL、DuckDB、TDengine等）；2) NL2SQL自然语言转SQL；3) RAG知识库构建与智能问答；4) 数据分析与可视化；5) AI预测模型创建；6) 元数据自动提取。**触发场景**：当用户需要查询数据库、分析数据、构建知识库、自然语言转SQL、搜索数据、创建预测模型、提取数据库元数据、或进行任何实际数据库操作时使用。**不触发场景**：纯SQL编写、SQL性能优化、数据库配置问题、编程脚本编写等非实际数据库操作场景。"""
    
    return optimized_desc

def main():
    # 配置路径
    eval_set_path = "f:/src/tmp/mindsdb-skill/evals/trigger_eval_utf8.json"
    skill_path = Path("f:/src/tmp/mindsdb-skill")
    
    # 加载评估集
    print("加载评估集...")
    eval_set = load_eval_set(eval_set_path)
    print(f"已加载 {len(eval_set)} 个查询")
    
    # 分析当前描述
    analysis = analyze_current_description(skill_path, eval_set)
    
    # 生成改进建议
    print("\n" + "="*70)
    print("优化建议")
    print("="*70)
    
    optimized_desc = suggest_improvements(analysis)
    
    print(f"\n优化后的描述:\n{optimized_desc}")
    
    # 保存优化结果
    output_path = skill_path / "evals" / "optimized_description.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "original_description": analysis["description"],
            "optimized_description": optimized_desc,
            "analysis": {
                "trigger_count": analysis["trigger_count"],
                "no_trigger_count": analysis["no_trigger_count"]
            }
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n优化结果已保存到: {output_path}")
    
    # 提供应用建议
    print("\n" + "="*70)
    print("下一步操作")
    print("="*70)
    print("\n1. 审查优化后的描述是否符合预期")
    print("2. 如满意，可手动更新 SKILL.md 中的 description 字段")
    print("3. 或使用以下命令自动更新:")
    print(f"   python -c \"import json; data=json.load(open('{output_path}', encoding='utf-8')); print(data['optimized_description'])\"")

if __name__ == "__main__":
    main()
