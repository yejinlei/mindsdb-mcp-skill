---
name: mindsdb-mcp-skill
description: MindsDB MCP服务器交互技能，支持通过自然语言查询和操作200+企业级数据源。核心功能包括：1) 数据库连接与查询；2) NL2SQL自然语言转SQL；3) RAG知识库构建与智能问答；4) 数据分析与可视化；5) AI预测模型创建；6) 元数据自动提取。**触发场景**：当用户需要查询数据库、分析数据、构建知识库、自然语言转SQL、搜索数据、创建预测模型、提取数据库元数据、或进行任何实际数据库操作时使用。**不触发场景**：纯SQL编写、SQL性能优化、数据库配置问题、编程脚本编写等非实际数据库操作场景。 | MindsDB MCP server interaction skill supporting natural language queries and operations on 200+ enterprise data sources. Core features: 1) Database connection and queries; 2) NL2SQL natural language to SQL; 3) RAG knowledge base construction and intelligent Q&A; 4) Data analysis and visualization; 5) AI prediction model creation; 6) Automatic metadata extraction. **Trigger scenarios**: Use when users need to query databases, analyze data, build knowledge bases, convert natural language to SQL, search data, create prediction models, extract database metadata, or perform any actual database operations. **No-trigger scenarios**: Pure SQL writing, SQL performance optimization, database configuration issues, programming script writing, and other non-actual database operation scenarios.
version: 2.7.2
author: yejinlei
---

# MindsDB MCP Skill | MindsDB MCP Skill

基于 MindsDB MCP 协议的通用数据库交互技能，采用**三模块架构**设计，支持自然语言操作各类数据源，自动适配本地/远程 MindsDB 部署，无需修改技能代码即可兼容所有 MindsDB 支持的数据库。

A universal database interaction skill based on the MindsDB MCP protocol, featuring a **three-module architecture**, supporting natural language operations on various data sources, automatically adapting to local/remote MindsDB deployments, and compatible with all MindsDB-supported databases without modifying skill code.

## 架构设计 | Architecture Design

本技能采用**三模块架构**，职责分离清晰，便于维护和扩展：

### 模块1：db_connector（公共数据库连接模块）
- **职责**：统一管理数据库连接，封装MCP请求
- **功能**：
  - MindsDB服务自动检测、安装和启动
  - 数据库连接管理（支持200+企业级数据源）
  - 统一MCP请求发送和响应处理
  - 连接信息缓存

### 模块2：workflow_rag_build（本地RAG构建与管理工作流）
- **职责**：构建和维护本地RAG知识库
- **功能**：
  - 本地RAG系统初始化（ChromaDB + all-MiniLM-L6-v2）
  - 知识库管理（创建、列表、删除）
  - 数据字典管理（获取、搜索、刷新）
  - 元数据自动提取：自动从数据库提取表结构、列信息、业务含义
  - 数据持久化管理

### 模块3：workflow_rag_analysis（基于RAG的NLP2SQL和数据分析工作流）
- **职责**：利用RAG进行智能数据分析和查询
- **功能**：
  - 自然语言到SQL转换（NLP2SQL）
  - 智能查询引擎：基于元数据理解用户意图，自动生成SQL
  - 智能数据分析
  - 知识库智能问答
  - AI模型创建与预测

## 技能用途 | Skill Purpose

### 主要用途 | Main Purposes

- **自然语言到SQL转换**：将用户的自然语言查询自动转换为可执行的SQL语句，无需用户编写SQL
- **元数据自动提取**：自动理解数据库结构，无需手动配置即可进行智能查询
- **多数据源管理**：通过MindsDB HTTP API统一管理和操作200+企业级数据源，包括关系型数据库、时序数据库、文档数据库、数据仓库等各类数据源
- **RAG知识库构建与查询**：基于数据库数据构建知识库，支持智能问答和文档检索，提升数据分析能力
- **本地RAG备用方案**：当MindsDB未配置embedding model时，自动切换到本地RAG（ChromaDB + all-MiniLM-L6-v2）
- **AI模型训练与预测**：基于数据源创建AI预测模型，进行数据预测和分析
- **跨源数据分析**：支持多数据源联动查询与分析，提供统一的结果格式
- **通用数据库查询**：不依赖特定业务场景，自动适应任何数据库结构，对所有文本字段进行智能搜索
- **NL2SQL 转换**（v2.4.2 新增）：结合本地 RAG 技术，将自然语言转换为 SQL 查询，支持智能意图理解和结果处理
- **Agent系统集成**：可直接集成到各类Agent系统，为Agent提供数据库操作能力

### 应用场景 | Application Scenarios

- **智能数据查询**：用户通过自然语言查询数据库，无需了解SQL语法
- **零配置数据分析**：自动提取元数据，无需预先配置即可进行智能分析
- **知识库构建**：基于企业数据构建智能知识库，支持员工快速获取信息
- **数据分析与报表**：通过自然语言驱动的数据分析，自动生成报表和insights
- **工业设备监控**：连接时序数据库，监控设备运行状态，预测设备故障
- **业务决策支持**：基于多源数据的分析，为业务决策提供数据支持

## 如何使用 | How to Use

### 环境准备 | Environment Preparation

### Python虚拟环境建议 | Python Virtual Environment Recommendation

为避免污染全局Python环境，建议使用项目级虚拟环境：

**创建并激活虚拟环境**：
```bash
# 在项目目录中创建虚拟环境
python -m venv venv

# 激活虚拟环境 (Windows)
venv\Scripts\activate

# 激活虚拟环境 (Linux/Mac)
source venv/bin/activate
```

**使用虚拟环境的优势**：
- 隔离项目依赖，避免全局Python环境污染
- 确保依赖版本一致性
- 简化依赖管理和部署

安装技能包所需依赖：

```bash
pip install requests
```

#### 元数据提取（示例）| Metadata Extraction (Example)

元数据自动提取功能以DuckDB为例，实际使用时无需安装duckdb：
```bash
# 示例：如果需要使用DuckDB作为数据源
# pip install duckdb
```

#### MindsDB自动安装与启动 | MindsDB Automatic Installation and Startup

本技能支持自动检测、安装和启动MindsDB服务，无需手动操作：

- **自动检测**：首次使用时会检查MindsDB是否已安装
- **自动安装**：如果未安装，自动执行 `pip install mindsdb`
- **自动启动**：自动启动MindsDB服务（默认端口47334）
- **服务验证**：验证MindsDB服务是否正常运行

#### 手动安装选项 | Manual Installation Option

如果您希望手动安装和配置MindsDB：

```bash
# 安装MindsDB
pip install mindsdb

# 启动MindsDB服务
python -m mindsdb
```

确保MindsDB服务在默认端口47334上运行。

#### 本地RAG依赖 | Local RAG Dependencies

当MindsDB RAG不可用时，技能会自动安装以下依赖：
- **chromadb**：轻量级向量数据库
- **sentence-transformers**：提供all-MiniLM-L6-v2嵌入模型

### 快速开始 | Quick Start

#### 方式1：使用元数据提取模块 | Method 1: Use Metadata Extraction Module

```python
from scripts.metadata_extractor import extract_metadata_from_duckdb

# 提取数据库元数据（以DuckDB为例）
data_dict, stats = extract_metadata_from_duckdb(
    db_path="data/weekly_report_warehouse.duckdb",
    save_path="data/metadata.json"
)

# 查看提取统计
print(f"表数量: {stats['tables_extracted']}")
print(f"列数量: {stats['columns_extracted']}")
print(f"关系数量: {stats['relationships_detected']}")

# 查看数据字典摘要
print(data_dict.generate_summary())
```

#### 方式2：使用智能查询引擎 | Method 2: Use Intelligent Query Engine

```python
from scripts.intelligent_query import IntelligentQueryEngine

# 初始化引擎（自动加载或提取元数据，以DuckDB为例）
engine = IntelligentQueryEngine(
    db_path="data/weekly_report_warehouse.duckdb"
)

# 自然语言查询
result = engine.query("总共几个部门")
print(f"SQL: {result['sql']}")
print(f"结果: {result['data']}")

# 关闭连接
engine.close()
```

#### 方式3：使用公共数据库连接模块 | Method 3: Use Database Connector Module

```python
from scripts.db_connector import get_db_connector

# 获取数据库连接器
db = get_db_connector()

# 连接数据库（以DuckDB为例）
result = db.connect_database(
    db_type="duckdb",
    db_path="data/weekly_report_warehouse.duckdb",
    database="warehouse_db"
)
print(result)

# 执行SQL查询
result = db.execute_sql("SELECT * FROM warehouse_db.odw_project LIMIT 5")
print(result)
```

#### 方式4：使用RAG构建工作流 | Method 4: Use RAG Build Workflow

```python
from scripts.workflow_rag_build import rag_build_workflow_entry

# 创建RAG知识库（自动包含元数据）
params = {
    "action": "create_kb",
    "kb_name": "weekly_report_kb",
    "database": "warehouse_db",
    "extract_metadata": True
}
result = rag_build_workflow_entry(params)
print(result)

# 获取数据字典摘要
params = {
    "action": "get_data_dict_summary"
}
result = rag_build_workflow_entry(params)
print(result)
```

#### 方式5：使用RAG分析工作流 | Method 5: Use RAG Analysis Workflow

```python
from scripts.workflow_rag_analysis import rag_analysis_workflow_entry

# 自然语言查询（NLP2SQL）
params = {
    "action": "nl_query",
    "database": "warehouse_db",
    "nl_text": "查询所有项目的状态"
}
result = rag_analysis_workflow_entry(params)
print(result)

# 知识库智能问答
params = {
    "action": "query_kb",
    "kb_name": "weekly_report_kb",
    "nl_text": "项目进度如何"
}
result = rag_analysis_workflow_entry(params)
print(result)
```

### RAG知识库全流程 | RAG Knowledge Base Full Process

```python
from scripts.workflow_rag_build import rag_build_workflow_entry
from scripts.workflow_rag_analysis import rag_analysis_workflow_entry
import json

# 1. 创建RAG知识库（工作流1）- 自动提取元数据
create_kb = {
    "action": "create_kb",
    "kb_name": "test_rag_kb",
    "database": "warehouse_db",
    "extract_metadata": True
}
create_result = rag_build_workflow_entry(create_kb)
print("创建知识库结果:", create_result)

# 2. 知识库智能问答（工作流2）
query_kb = {
    "action": "query_kb",
    "kb_name": "test_rag_kb",
    "nl_text": "查询核心数据信息"
}
query_result = rag_analysis_workflow_entry(query_kb)
print("知识库查询结果:", query_result)
```

## 核心功能 | Core Functions

### 模块1：db_connector（公共数据库连接模块）

| 方法 | 必传参数 | 功能说明 |
|------|---------|----------|
| connect_database | db_type | 连接指定类型的数据源 |
| list_databases | 无 | 列出所有已连接的数据源 |
| show_tables | database | 查看指定数据库的所有表 |
| describe_table | database, table | 查看指定表的结构 |
| execute_sql | sql | 执行自定义SQL语句 |

### 模块2：workflow_rag_build（RAG构建工作流）

| 动作 | 必传参数 | 功能说明 |
|------|---------|----------|
| create_kb | kb_name | 创建RAG知识库，自动提取数据库元数据 |
| list_kb | 无 | 列出所有已创建的RAG知识库 |
| delete_kb | kb_name | 删除指定名称的RAG知识库 |
| get_data_dict_summary | 无 | 获取数据字典摘要信息 |
| search_data_dict | keyword | 搜索数据字典中的元数据 |
| refresh_data_dict | database | 刷新指定数据库的数据字典 |
| extract_metadata | database | 提取指定数据库的元数据 |

### 模块3：workflow_rag_analysis（RAG分析工作流）

| 动作 | 必传参数 | 功能说明 |
|------|---------|----------|
| connect_db | db_type | 连接指定类型的数据源 |
| list_databases | 无 | 列出所有已连接的数据源 |
| show_table_schema | database | 查看指定数据源的所有数据表结构 |
| nl_query | database, nl_text | 通过自然语言查询数据（使用MindsDB内置AI） |
| nl2sql | database, nl_text | 本地NL2SQL转换（Vanna风格RAG增强） |
| smart_query | database, nl_text | **智能查询（推荐）**：自动选择最佳查询方式 |
| exec_sql | database, sql | 执行自定义SQL语句 |
| analyze_data | database, nl_text | 对数据进行自然语言驱动的智能分析 |
| query_kb | kb_name, nl_text | 向知识库发送自然语言查询 |
| intelligent_query | database, nl_text | 智能查询（基于元数据） |
| create_model | model_name, predict_field | 创建AI预测模型 |
| generate_sql_prompt | database, nl_text | **生成 SQL prompt**：供 Agent LLM 生成 SQL |
| validate_sql | database, sql | 验证并修复 SQL 语句 |
| init_training | database | 初始化训练数据（自动提取DDL） |
| add_training_sql | database, sql, question | 添加SQL示例训练数据 |
| add_training_doc | database, content | 添加文档训练数据 |
| get_training_stats | database | 获取训练数据统计 |

#### smart_query 智能路由策略

`smart_query` 会自动选择最佳查询方式，路由策略如下：

| 优先级 | 条件 | 使用方式 |
|--------|------|----------|
| 1 | 指定了 `kb_name` 且知识库存在 | `query_kb` |
| 2 | MindsDB AI 能力可用 | `nl_query` |
| 3 | 本地 RAG 可用 | `nl2sql`（增强版） |
| 4 | 其他情况 | `nl2sql`（纯规则模式） |

返回结果中会包含 `route_info` 字段，说明选择了哪种方式及原因。

#### Vanna 风格 Agent LLM SQL 生成

本技能实现了完整的 Vanna 风格 NL2SQL 机制，核心流程如下：

```
用户问题 → RAG 检索 → 生成 Prompt → Agent LLM 生成 SQL → 验证/修复 → 执行
```

**核心方法**：`generate_sql_prompt`

此方法检索相关的 DDL、SQL 示例、文档，构建完整的 prompt，返回给 Agent 的 LLM 生成 SQL。

**使用示例**：

```python
# 1. 生成 SQL prompt（供 Agent LLM 使用）
params = {
    "action": "generate_sql_prompt",
    "database": "warehouse_db",
    "nl_text": "查询所有活跃项目"
}
result = rag_analysis_workflow_entry(params)

# result 包含:
# - prompt: 完整的 SQL 生成 prompt
# - context: 相关的 DDL、SQL 示例、文档
# - instruction_for_agent: 给 Agent 的指令

# 2. Agent LLM 根据 prompt 生成 SQL
# sql = agent_llm.generate(result["data"]["prompt"])

# 3. 验证并修复 SQL
params = {
    "action": "validate_sql",
    "database": "warehouse_db",
    "sql": "SELECT * FROM project WHERE status = 'active'"
}
result = rag_analysis_workflow_entry(params)

# 4. 执行 SQL
params = {
    "action": "exec_sql",
    "database": "warehouse_db",
    "sql": result["data"]["fixed_sql"]
}
```

#### Vanna 风格训练数据管理

本技能实现了类似 Vanna 的训练数据管理机制，支持：

| 数据类型 | 说明 | 用途 |
|----------|------|------|
| DDL | 表结构定义 | 帮助理解数据库结构 |
| SQL 示例 | 自然语言-SQL 对 | 相似查询时复用 SQL |
| 文档 | 业务文档/说明 | 提供业务上下文 |

**使用示例**：

```python
# 1. 初始化训练数据（自动从 schema 提取 DDL）
params = {
    "action": "init_training",
    "database": "warehouse_db"
}

# 2. 添加 SQL 示例
params = {
    "action": "add_training_sql",
    "database": "warehouse_db",
    "sql": "SELECT * FROM projects WHERE status = 'active'",
    "question": "查询所有活跃项目",
    "tables": ["projects"]
}

# 3. 添加业务文档
params = {
    "action": "add_training_doc",
    "database": "warehouse_db",
    "content": "projects 表存储所有项目信息，status 字段表示项目状态...",
    "title": "项目表说明"
}

# 4. 查看训练数据统计
params = {
    "action": "get_training_stats",
    "database": "warehouse_db"
}
```

### 模块4：metadata_extractor（元数据提取模块）

| 方法 | 必传参数 | 功能说明 |
|------|---------|----------|
| extract_from_duckdb | db_path | 从数据库提取完整元数据（以DuckDB为例） |
| get_extraction_stats | 无 | 获取提取统计信息 |
| save_to_file | file_path | 保存数据字典到文件 |

### 模块5：intelligent_query（智能查询模块）

| 方法 | 必传参数 | 功能说明 |
|------|---------|----------|
| query | question | 主查询接口，一站式智能查询 |
| understand_question | question | 理解用户问题，提取关键信息 |
| generate_sql | understanding | 根据理解结果生成SQL |
| execute_query | sql | 执行SQL查询 |

## 返回格式 | Return Format

所有操作的返回结果均为统一JSON格式：

```json
{
  "code": 0,
  "msg": "success",
  "data": {}
}
```

### 状态码说明 | Status Code Description

- **0**：操作成功
- **-1**：缺失必传参数action
- **-2**：不支持的action
- **-3**：缺失当前action的必传参数
- **-4**：MCP接口请求失败
- **-5**：MindsDB连接超时
- **-6**：MindsDB服务不可达
- **-7**：HTTP请求异常
- **-8**：未知异常
- **-9**：MindsDB服务未就绪
- **-10**：本地RAG初始化失败
- **-11**：元数据提取失败

## 注意事项 | Notes

- 创建RAG知识库前，建议先通过db_connector或workflow_rag_analysis连接数据源
- RAG知识库的名称（kb_name）需唯一，重复创建会返回错误
- 首次使用本地RAG时会自动下载all-MiniLM-L6-v2模型（约80MB），优先从国内源下载
- 本地RAG使用ChromaDB持久化存储，数据保存在`data/chromadb_persist`目录
- 数据字典自动持久化到`data/data_dictionary.json`文件
- 元数据自动提取功能以DuckDB为例，其他数据库需要手动配置元数据
- 智能查询引擎依赖元数据，首次使用会自动提取并缓存

## 项目结构 | Project Structure

```
mindsdb-mcp-skill/
├── scripts/
│   ├── db_connector.py           # 公共数据库连接模块
│   ├── workflow_rag_build.py     # 工作流1：本地RAG构建与管理
│   ├── workflow_rag_analysis.py  # 工作流2：基于RAG的NLP2SQL和数据分析
│   ├── workflow_database.py      # 工作流3：数据库连接与查询工作流
│   ├── data_dictionary.py        # 数据字典实现
│   ├── metadata_extractor.py     # 元数据自动提取模块
│   ├── intelligent_query.py      # 智能查询引擎
│   ├── mindsdb_skill.py          # 核心技能代码
│   └── nl2sql/                   # NL2SQL 核心模块
│       ├── engine.py             # NL2SQL 引擎
│       ├── intent_recognizer.py  # 意图识别器
│       ├── rag_generator.py      # RAG SQL 生成器
│       ├── schema_extractor.py   # Schema 自动提取
│       ├── training_data.py      # 训练数据管理
│       └── training_config.py    # 训练配置加载
├── evals/
│   └── evals.json                # 测试用例
├── data/
│   ├── chromadb_persist/         # RAG向量数据持久化目录
│   ├── data_dictionary.json      # 数据字典持久化文件
│   └── training_data/            # 训练数据持久化目录
├── references/                   # 参考文档
├── README.md                     # 说明文档
├── SKILL.md                      # 技能定义文件
└── mcp.json                      # MCP配置文件
```

## 高级功能 | Advanced Features

### 意图识别增强 | Intent Recognition Enhancement

本技能实现了意图识别模块，在 RAG 检索之前进行意图分析，提高 SQL 生成准确性：

| 意图类型 | 说明 | 示例查询 |
|----------|------|----------|
| list | 列表查询 | "查询所有卡点" |
| count | 计数查询 | "统计卡点数量" |
| aggregate | 聚合查询 | "统计收入合计" |
| compare | 对比查询 | "对比各部门收入" |
| trend | 趋势查询 | "分析收入趋势" |
| detail | 详情查询 | "查看项目详情" |

**使用示例**：

```python
from scripts.nl2sql.intent_recognizer import get_intent_recognizer

recognizer = get_intent_recognizer()
intent = recognizer.recognize("统计卡点数量")

print(f"意图类型: {intent.intent_type.value}")  # count
print(f"目标: {intent.target}")                 # 卡点
print(f"实体映射: {intent.entities}")           # {'卡点': 'issues'}
```

### 零配置 Schema 自动提取 | Zero-Config Schema Extraction

连接数据库时自动提取表结构并推断业务术语映射，实现零配置使用：

```python
# 连接数据库时自动执行：
# 1. 提取所有表结构 (DDL)
# 2. 推断业务术语映射 (issues → 卡点, leader_name → 负责人)
# 3. 自动注册到意图识别器
# 4. 自动注册 DDL 训练数据

from scripts.workflow_rag_analysis import rag_analysis_workflow_entry

result = rag_analysis_workflow_entry({
    "action": "connect_db",
    "db_type": "duckdb",
    "db_path": "/path/to/database.duckdb",
    "database": "my_db"
})
# 自动完成 Schema 提取和术语推断
```

**自动推断规则示例**：

| 字段名 | 推断术语 |
|--------|----------|
| issues | 卡点, 问题, 风险 |
| leader_name | 负责人, 领导 |
| finance_type | 资金流向, 资金类型 |
| department | 部门 |
| project | 项目 |

### 训练数据配置文件 | Training Data Configuration

支持通过 YAML 配置文件批量导入训练数据：

```yaml
# training_config.yaml
database: warehouse_db

business_terms:
  卡点: [issues, 问题, 风险]
  资金流向: [finance_type, 资金类型]
  部门: [department, department_name]

training_sql:
  - question: "查询所有卡点"
    sql: "SELECT issues FROM odw_weekly_report WHERE issues IS NOT NULL"
    intent_tags: [list, 卡点]

training_docs:
  - title: "周报表说明"
    content: "odw_weekly_report 表的 issues 字段存储卡点问题"
    intent_tags: [卡点, 周报]
```

**加载配置**：

```python
from scripts.nl2sql.training_config import load_training_config
from scripts.nl2sql.training_data import get_training_data_collector

collector = get_training_data_collector()
result = load_training_config('training_config.yaml', collector)
# {'business_terms': 3, 'training_sql': 1, 'training_docs': 1, 'status': 'success'}
```

### 混合查询方案 | Hybrid Query Approach

结合意图识别和 RAG 检索，提高查询准确率：

```
用户问题: "统计卡点数量"
    ↓
第一层：意图识别
  → type: count, target: 卡点, entities: {卡点: issues}
    ↓
第二层：RAG 检索 + 意图标签过滤
  → 检索相似 SQL，按意图标签排序
    ↓
第三层：SQL 生成
  → SELECT COUNT(*) FROM odw_weekly_report WHERE issues IS NOT NULL
```