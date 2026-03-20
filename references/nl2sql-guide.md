# NL2SQL 模块详细指南

本文档详细说明 mindsdb-mcp-skill 的 NL2SQL 核心模块实现和使用方法。

## 模块架构

```
nl2sql/
├── engine.py             # NL2SQL 引擎 - 整合各模块
├── intent_recognizer.py  # 意图识别器 - 识别用户查询意图
├── rag_generator.py      # RAG SQL 生成器 - 基于检索生成 SQL
├── schema_extractor.py   # Schema 提取器 - 自动提取数据库结构
├── training_data.py      # 训练数据管理 - DDL/SQL/文档管理
└── training_config.py    # 训练配置加载 - YAML 配置支持
```

## 意图识别器 (intent_recognizer.py)

### 支持的意图类型

| 类型 | 说明 | 触发关键词 |
|------|------|-----------|
| query | 通用查询 | 查询、查找、搜索、显示、获取 |
| count | 计数查询 | 多少、几个、数量、统计...数量、计数 |
| aggregate | 聚合查询 | 合计、总计、汇总、平均、最大、最小 |
| compare | 对比查询 | 对比、比较、区别、差异、哪个 |
| list | 列表查询 | 列出、所有、全部、查询...所有 |
| detail | 详情查询 | 详情、详细、具体、详细信息 |
| trend | 趋势查询 | 趋势、变化、增长、下降、走势 |

### 使用示例

```python
from nl2sql.intent_recognizer import get_intent_recognizer

recognizer = get_intent_recognizer()

# 识别意图
intent = recognizer.recognize("统计卡点数量")

print(f"意图类型: {intent.intent_type.value}")  # count
print(f"目标: {intent.target}")                 # 卡点
print(f"操作: {intent.action}")                 # query
print(f"实体映射: {intent.entities}")           # {'卡点': 'issues'}
print(f"置信度: {intent.confidence}")           # 0.7
print(f"增强文本: {intent.enhanced_text}")      # 统计卡点(issues)数量

# 获取推荐表
tables = recognizer.get_table_suggestions(intent)
print(f"推荐表: {tables}")  # ['odw_weekly_report', 'odw_project']
```

### 动态添加业务术语

```python
# 添加单个术语
recognizer.add_business_term("订单", ["order", "order_id", "订单号"])

# 批量添加
recognizer.add_business_terms({
    "客户": ["customer", "customer_name"],
    "产品": ["product", "product_name"]
})
```

## Schema 自动提取 (schema_extractor.py)

### 支持的数据库

- DuckDB
- SQLite
- PostgreSQL
- MySQL

### 自动推断规则

```python
FIELD_TERM_PATTERNS = {
    "issues": ["卡点", "问题", "风险"],
    "leader_name": ["负责人", "领导"],
    "finance_type": ["资金流向", "资金类型"],
    "department": ["部门"],
    "project": ["项目"],
    "amount": ["金额", "数额"],
    # ... 更多规则
}
```

### 使用示例

```python
from nl2sql.schema_extractor import get_schema_extractor
from nl2sql.training_data import get_training_data_collector
from nl2sql.intent_recognizer import get_intent_recognizer

# 初始化
training_collector = get_training_data_collector()
intent_recognizer = get_intent_recognizer()
extractor = get_schema_extractor(training_collector, intent_recognizer)

# 提取 DuckDB Schema
result = extractor.extract_from_duckdb(
    db_path="/path/to/database.duckdb",
    database="warehouse_db"
)

print(f"表数量: {len(result['tables'])}")
print(f"推断术语: {result['inferred_terms']}")
```

## RAG SQL 生成器 (rag_generator.py)

### 工作流程

```
用户问题
    ↓
意图识别 → 增强文本
    ↓
RAG 检索 (相似 SQL + DDL + 文档)
    ↓
意图标签过滤 → 优先匹配
    ↓
SQL 生成 (规则 + 模板)
    ↓
验证/修复 → 返回结果
```

### 使用示例

```python
from nl2sql.rag_generator import get_rag_sql_generator

generator = get_rag_sql_generator()

# 生成 SQL
result = generator.generate_sql_with_rag(
    nl_text="统计卡点数量",
    database="warehouse_db",
    schema_info=schema_info  # 可选
)

print(f"SQL: {result['sql']}")
print(f"方法: {result['method']}")
print(f"置信度: {result['confidence']}")
print(f"意图: {result['context']['intent']}")
```

### 生成 Agent LLM Prompt

```python
# 生成供 Agent LLM 使用的 prompt
result = generator.generate_sql_prompt(
    nl_text="查询所有活跃项目",
    database="warehouse_db"
)

# result 包含:
# - prompt: 完整的 SQL 生成 prompt
# - context: 相关的 DDL、SQL 示例、文档
# - instruction: 给 Agent 的指令
```

## 训练数据管理 (training_data.py)

### 数据类型

| 类型 | 说明 | 用途 |
|------|------|------|
| DDL | 表结构定义 | 帮助理解数据库结构 |
| SQL | 自然语言-SQL 对 | 相似查询时复用 SQL |
| 文档 | 业务文档/说明 | 提供业务上下文 |

### 使用示例

```python
from nl2sql.training_data import get_training_data_collector

collector = get_training_data_collector()

# 添加 DDL
collector.add_ddl(
    database="warehouse_db",
    table="odw_project",
    ddl="CREATE TABLE odw_project (id INTEGER, name VARCHAR, status VARCHAR)",
    description="项目表"
)

# 添加 SQL 示例（带意图标签）
collector.add_sql(
    database="warehouse_db",
    sql="SELECT COUNT(*) FROM odw_weekly_report WHERE issues IS NOT NULL",
    question="统计卡点数量",
    tables=["odw_weekly_report"],
    intent_tags=["count", "卡点", "issues"]
)

# 添加文档（带意图标签）
collector.add_documentation(
    database="warehouse_db",
    content="odw_weekly_report 表的 issues 字段存储卡点问题",
    title="周报表说明",
    intent_tags=["卡点", "issues", "周报"]
)

# 获取统计
stats = collector.get_stats("warehouse_db")
```

## 训练配置加载 (training_config.py)

### YAML 配置格式

```yaml
# training_config.yaml
database: warehouse_db

# 业务术语映射
business_terms:
  卡点: [issues, 问题, 风险]
  资金流向: [finance_type, 资金类型]
  部门: [department, department_name]

# SQL 示例
training_sql:
  - question: "查询所有卡点"
    sql: "SELECT issues FROM odw_weekly_report WHERE issues IS NOT NULL"
    tables: [odw_weekly_report]
    intent_tags: [list, 卡点]

# 业务文档
training_docs:
  - title: "周报表说明"
    content: "odw_weekly_report 表的 issues 字段存储卡点问题"
    intent_tags: [卡点, 周报]
```

### 加载配置

```python
from nl2sql.training_config import load_training_config
from nl2sql.training_data import get_training_data_collector

collector = get_training_data_collector()
result = load_training_config("training_config.yaml", collector)

# result: {'business_terms': 3, 'training_sql': 1, 'training_docs': 1, 'status': 'success'}
```

## 混合查询方案

结合意图识别和 RAG 检索，提高查询准确率：

```python
from nl2sql.engine import get_nl2sql_engine

engine = get_nl2sql_engine(rag_workflow)

# 智能查询（自动选择最佳方式）
result = engine.smart_query(
    database="warehouse_db",
    nl_text="统计卡点数量"
)

# result 包含:
# - sql: 生成的 SQL
# - route_info: 路由信息（使用了哪种方式）
# - intent: 意图识别结果
# - context: RAG 检索上下文
```

## 最佳实践

### 1. 零配置使用

```python
# 连接数据库时自动完成所有配置
rag_analysis_workflow_entry({
    "action": "connect_db",
    "db_type": "duckdb",
    "db_path": "/path/to/db.duckdb",
    "database": "my_db"
})
# 自动: Schema 提取 → 术语推断 → DDL 注册
```

### 2. 手动配置使用

```python
# 适合复杂业务场景
load_training_config("training_config.yaml", collector)
```

### 3. 混合使用

```python
# 零配置 + 手动补充
# 1. 连接时自动提取基础配置
# 2. 手动添加特定业务术语和 SQL 示例
```
