SKILL.md（完整版·Markdown可直接拷贝）

name: mindsdb-mcp-skill

description: MindsDB MCP 服务器交互技能，用于通过自然语言查询和操作 200+ 企业级数据源。当用户需要查询数据库、分析数据、创建 AI 模型、连接数据源（MySQL、PostgreSQL、MongoDB、ClickHouse、TDengine、TiDB、DuckDB、Excel、CSV、Gmail、Slack 等）、执行 SQL 查询、进行数据预测、构建知识库（RAG）、智能问答、文档检索或任何与数据库交互的任务时使用此技能。即使没有明确提到 MindsDB，只要涉及数据库操作、数据分析、数据查询、知识库构建、AI 问答或需要连接多个数据源的场景，都应该使用此技能。本技能支持所有 MindsDB 兼容的数据库，不限于文档中列出的类型，无需修改代码即可适配新的 MindsDB 支持数据源。**核心价值**：任意 Agent（包括 AI IDE）可通过本技能实现 NLP2SQL 能力，无需在 MindsDB EDIT 内定义 Agent+RAG，通过外部 Agent+SKILL+MindsDB 的组合方式，大大提升效率和通用性。| MindsDB MCP Server Interaction Skill for querying and operating 200+ enterprise-level data sources through natural language. Use this skill when users need to query databases, analyze data, create AI models, connect data sources (MySQL, PostgreSQL, MongoDB, ClickHouse, TDengine, TiDB, DuckDB, Excel, CSV, Gmail, Slack, etc.), execute SQL queries, perform data prediction, build knowledge bases (RAG), conduct intelligent Q&A, retrieve documents, or perform any database-related tasks. Even if MindsDB is not explicitly mentioned, this skill should be used for scenarios involving database operations, data analysis, data queries, knowledge base construction, AI Q&A, or multi-data source connections. This skill supports all MindsDB-compatible databases, not limited to those listed in the documentation, and can adapt to new MindsDB-supported data sources without modifying code. **Core Value**: Any Agent (including AI IDE) can implement NLP2SQL capabilities through this skill, without defining Agent+RAG within MindsDB EDIT. The combination of external Agent+SKILL+MindsDB greatly improves efficiency and versatility.

version: 1.1.0

author: yejinlei

---

MindsDB MCP Skill | MindsDB MCP Skill

基于 MindsDB MCP 协议的通用数据库交互技能，支持自然语言操作各类数据源，自动适配本地/远程 MindsDB 部署，无需修改技能代码即可兼容所有 MindsDB 支持的数据库。| A universal database interaction skill based on the MindsDB MCP protocol, supporting natural language operations on various data sources, automatically adapting to local/remote MindsDB deployments, and compatible with all MindsDB-supported databases without modifying skill code.

## 技能用途 | Skill Purpose

### 主要用途 | Main Purposes

- 自然语言到SQL转换：将用户的自然语言查询自动转换为可执行的SQL语句，无需用户编写SQL
- 多数据源管理：统一管理和操作200+企业级数据源，包括SQL数据库、NoSQL数据库、时序数据库、文件型数据源等
- RAG知识库构建与查询：基于数据库数据构建知识库，支持智能问答和文档检索，提升数据分析能力
- 本地RAG备用方案：当MindsDB未配置embedding model时，自动切换到本地RAG（ChromaDB + all-MiniLM-L6-v2）
- AI模型训练与预测：基于数据源创建AI预测模型，进行数据预测和分析
- 跨源数据分析：支持多数据源联动查询与分析，提供统一的结果格式
- Agent系统集成：可直接集成到各类Agent系统，为Agent提供数据库操作能力

### 应用场景 | Application Scenarios

- 智能数据查询：用户通过自然语言查询数据库，无需了解SQL语法
- 知识库构建：基于企业数据构建智能知识库，支持员工快速获取信息
- 数据分析与报表：通过自然语言驱动的数据分析，自动生成报表和insights
- 工业设备监控：连接时序数据库，监控设备运行状态，预测设备故障
- 业务决策支持：基于多源数据的分析，为业务决策提供数据支持

## 如何使用 | How to Use

### 环境准备 | Environment Preparation

安装技能包所需依赖：

```bash
pip install requests
```

#### MindsDB自动安装与启动 | MindsDB Automatic Installation and Startup

本技能支持自动检测、安装和启动MindsDB服务，无需手动操作：

- **自动检测**：首次使用时会检查MindsDB是否已安装
- **自动安装**：如果未安装，自动执行 `pip install mindsdb`
- **自动启动**：安装完成后自动启动MindsDB服务（默认端口47334）
- **服务验证**：确保MindsDB服务正常运行

#### 本地RAG备用方案 | Local RAG Alternative

当MindsDB未配置embedding model时，技能会自动切换到本地RAG系统：

- **自动检测**：检测MindsDB的RAG功能是否就绪
- **自动安装**：需要时自动安装chromadb和sentence-transformers
- **本地模型**：使用轻量级的all-MiniLM-L6-v2模型（约80MB）
- **国内源下载**：优先从国内源（https://hf-mirror.com）下载模型，解决网络问题
- **自动下载**：首次使用时自动下载模型到本地缓存
- **降级方案**：当模型下载失败时，自动使用基于TF-IDF的检索作为降级方案

**手动安装选项**：如果您希望手动安装和配置MindsDB，可以：
1. 执行 `pip install mindsdb` 安装MindsDB
2. 执行 `python -m mindsdb` 启动MindsDB服务
3. 确保服务在默认端口47334上运行

### 基础调用示例 | Basic Call Examples

#### 示例1：连接MySQL数据源 | Example 1: Connect to MySQL Data Source

```python
from scripts.mindsdb_skill import mindsdb_skill_entry

# 连接参数
params = {
    "action": "connect_db",
    "db_type": "mysql",
    "host": "localhost",
    "port": 3306,
    "username": "root",
    "password": "123456"
}

# 执行连接
result = mindsdb_skill_entry(params)
print(result)
```

#### 示例2：自然语言查询数据 | Example 2: Natural Language Data Query

```python
from scripts.mindsdb_skill import mindsdb_skill_entry

# 查询参数
params = {
    "action": "nl_query",
    "database": "mysql_db",
    "nl_text": "查询销售额最高的前10个产品",
    "host": "localhost",
    "port": 47334,
    "username": "admin",
    "password": "password123"
}

# 执行查询
result = mindsdb_skill_entry(params)
print(result)
```

#### 示例3：RAG知识库操作 | Example 3: RAG Knowledge Base Operations

```python
from scripts.mindsdb_skill import mindsdb_skill_entry

# 基础配置
base_config = {
    "host": "localhost",
    "port": 47334,
    "username": "admin",
    "password": "password123",
    "database": "mysql_db"
}

# 创建RAG知识库
create_kb = {**base_config, "action": "create_kb", "kb_name": "sales_kb"}
create_result = mindsdb_skill_entry(create_kb)
print("创建知识库结果：", create_result)

# 知识库智能问答
query_kb = {**base_config, "action": "query_kb", "kb_name": "sales_kb", "nl_text": "2024年第一季度销售额是多少？"}
query_result = mindsdb_skill_entry(query_kb)
print("问答结果：", query_result)

# 删除知识库
delete_kb = {**base_config, "action": "delete_kb", "kb_name": "sales_kb"}
delete_result = mindsdb_skill_entry(delete_kb)
print("删除知识库结果：", delete_result)
```

## 底层原理 | Underlying Principles

### 技术架构 | Technical Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Agent System  │────>│  MindsDB MCP    │────>│    MindsDB      │
│   (AI IDE等)    │<────│    Skill        │<────│    服务器       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### 核心流程 | Core Process

1. 参数接收与验证：接收Agent传入的参数字典，进行参数校验和补全
2. MCP请求构建：根据action类型，构建对应的MCP请求，包含必要的SQL语句或操作指令
3. MindsDB交互：通过HTTP请求与MindsDB服务器通信，发送MCP请求并接收响应
4. 结果处理：解析MindsDB响应，转换为统一的JSON格式返回给Agent

### 关键技术 | Key Technologies

- MCP协议：MindsDB Control Protocol，用于与MindsDB服务器通信的标准化协议
- NL2SQL转换：利用MindsDB的自然语言处理能力，将自然语言查询转换为SQL语句
- RAG技术：Retrieval-Augmented Generation，结合向量检索和语言模型生成，实现智能问答
- 向量存储：用于存储文档的向量表示，支持高效的相似性搜索
- 嵌入模型：将文本转换为向量的模型，如sentence-transformers/all-MiniLM-L6-v2

### RAG工作原理 | RAG Working Principle

1. 知识库创建：将数据库中的结构化数据转换为文本，通过嵌入模型转换为向量，存储到向量数据库中
2. 查询处理：将用户的自然语言查询转换为向量，在向量数据库中进行相似性搜索，找到相关的文档
3. 答案生成：将检索到的相关文档与原始查询一起输入到语言模型，生成准确的回答

一、技能功能 | I. Skill Functions

- 通用数据库连接：支持所有 MindsDB 兼容数据源（SQL/NoSQL/时序库/文件型/云数据源）| Universal Database Connection: Supports all MindsDB-compatible data sources (SQL/NoSQL/time-series databases/file-based/cloud data sources)

- 自然语言查询（NL2SQL）：自动将自然语言转换为可执行查询语句，适配各类支持查询的数据库 | Natural Language Query (NL2SQL): Automatically converts natural language into executable query statements, adapting to various query-supported databases

- 数据字典生成：自动获取数据库表结构、字段属性，生成统一格式的数据字典 | Data Dictionary Generation: Automatically obtains database table structures and field attributes to generate a unified format data dictionary

- SQL 执行：支持手动输入 SQL 语句，执行各类数据库操作 | SQL Execution: Supports manual input of SQL statements to perform various database operations

- AI 模型管理：创建、预测、分析 AI 预测模型，适配所有结构化数据源 | AI Model Management: Creates, predicts, and analyzes AI prediction models, adapting to all structured data sources

- RAG 知识库：基于数据库结构化数据构建知识库，支持智能问答、文档检索 | RAG Knowledge Base: Builds knowledge bases based on structured database data, supporting intelligent Q&A and document retrieval

- 跨源分析：支持多数据源联动查询与数据分析，统一返回结果格式 | Cross-Source Analysis: Supports linked queries and data analysis across multiple data sources with a unified result format

二、触发场景 | II. Trigger Scenarios

当用户有以下需求时，Agent 应自动调用本技能：| The Agent should automatically call this skill when the user has the following needs:

- 需要查询、操作、分析任意类型数据库（无论是否明确提及 MindsDB）| Needs to query, operate, or analyze any type of database (whether MindsDB is explicitly mentioned or not)

- 需要连接具体数据源（如 MySQL、PostgreSQL、MongoDB、ClickHouse 等）| Needs to connect to specific data sources (e.g., MySQL, PostgreSQL, MongoDB, ClickHouse, etc.)

- 需要通过自然语言生成 SQL，或手动执行 SQL 查询 | Needs to generate SQL through natural language or manually execute SQL queries

- 需要查看数据库表结构、生成数据字典 | Needs to view database table structures and generate data dictionaries

- 需要构建知识库、进行文档检索、智能问答 | Needs to build knowledge bases, perform document retrieval, and conduct intelligent Q&A

- 需要创建 AI 预测模型、进行数据分析、生成报表 | Needs to create AI prediction models, perform data analysis, and generate reports

- 需要连接多个数据源，进行跨源查询与分析 | Needs to connect multiple data sources for cross-source queries and analysis

2.1 具体触发短语 | 2.1 Specific Trigger Phrases

- 中文触发短语：连接MySQL数据库、用自然语言查数据、生成数据库数据字典、创建AI预测模型、构建RAG知识库、执行SQL语句、跨源查询数据、连接远程MindsDB、查询数据库表结构、分析数据趋势

- 英文触发短语：query database、execute SQL、create AI model、build knowledge base、connect database、NL to SQL、generate data dictionary、cross-source analysis

2.2 使用边界与限制 | 2.2 Usage Boundaries and Restrictions

- 不支持非 MindsDB 兼容的数据库引擎 | Does not support database engines incompatible with MindsDB

- 远程连接需开放 MindsDB 47334 端口，确保 Agent 与 MindsDB 服务可正常连通 | Remote connection requires opening MindsDB port 47334 to ensure normal connection between Agent and MindsDB service

- 大型数据库查询建议使用 LIMIT 限制结果数量，避免查询超时 | For large database queries, it is recommended to use LIMIT to limit the number of results to avoid query timeout

- 需确保 MindsDB 版本 ≥ 23.11（需启用 MCP 接口）| Ensure MindsDB version ≥ 23.11 (MCP interface must be enabled)

三、Agent 调用规范 | III. Agent Call Specification

3.1 通用参数（所有动作统一适用）| 3.1 Universal Parameters (Applicable to All Actions)

所有动作均使用以下统一参数结构，Agent 无需区分数据库类型，仅需按需求传递对应参数：| All actions use the following unified parameter structure. The Agent does not need to distinguish between database types, only passing the corresponding parameters as needed:

参数名

类型

是否必传

描述

默认值

Parameter Name

Type

Required

Description

Default Value

action

string

是

需执行的具体动作（枚举值见 3.2）

-

action

string

Yes

Specific action to execute (see 3.2 for enumeration values)

-

db_type

string

否（除 connect_db 外）

MindsDB 支持的数据库引擎名称（如 mysql、clickhouse、mongodb 等）

-

db_type

string

No (except connect_db)

MindsDB-supported database engine name (e.g., mysql, clickhouse, mongodb, etc.)

-

host

string

否

MindsDB 服务地址或目标数据库地址（本地/远程 IP/域名）

localhost

host

string

No

MindsDB service address or target database address (local/remote IP/domain)

localhost

port

number

否

MindsDB 服务端口或目标数据库端口

47334（MindsDB 默认端口）

port

number

No

MindsDB service port or target database port

47334 (MindsDB Default Port)

username

string

否

MindsDB 登录账号或目标数据库账号

admin

username

string

No

MindsDB login username or target database username

admin

password

string

否

MindsDB 登录密码或目标数据库密码

password123

password

string

No

MindsDB login password or target database password

password123

database

string

否（除 list_databases 外）

目标数据库名称

-

database

string

No (except list_databases)

Target database name

-

nl_text

string

否（仅 nl_query、query_kb 需传）

自然语言查询文本

-

nl_text

string

No (only for nl_query, query_kb)

Natural language query text

-

sql

string

否（仅 exec_sql 需传）

需执行的 SQL 语句

-

sql

string

No (only for exec_sql)

SQL statement to execute

-

kb_name

string

否（仅知识库相关动作需传）

知识库名称

default_kb

kb_name

string

No (only for knowledge base-related actions)

Knowledge base name

default_kb

model_name

string

否（仅模型相关动作需传）

AI 模型名称

default_model

model_name

string

No (only for model-related actions)

AI model name

default_model

predict_field

string

否（仅 create_model 需传）

模型预测字段

-

predict_field

string

No (only for create_model)

Model prediction field

-

top_k

number

否（仅 RAG 相关动作需传）

RAG 检索时返回的相关结果数量

5

top_k

number

No (only for RAG-related actions)

Number of relevant results returned during RAG retrieval

5

threshold

number

否（仅 RAG 相关动作需传）

RAG 检索相关性阈值

0.7

threshold

number

No (only for RAG-related actions)

RAG retrieval relevance threshold

0.7

3.2 支持的 Action 枚举 | 3.2 Supported Action Enumeration

Action

动作描述

额外必传参数

适用场景

Action

Action Description

Additional Required Parameters

Applicable Scenarios

connect_db

连接目标数据库

db_type

首次连接任意数据库

connect_db

Connect to target database

db_type

First connection to any database

list_databases

列出 MindsDB 已连接的所有数据库

无

查看当前可用数据库

list_databases

List all databases connected to MindsDB

None

View currently available databases

show_table_schema

获取表结构，生成数据字典

database

查看数据库表结构、字段信息

show_table_schema

Get table structure and generate data dictionary

database

View database table structure and field information

nl_query

自然语言转 SQL 并执行查询

database、nl_text

无需写 SQL，通过自然语言查询数据

nl_query

Convert natural language to SQL and execute query

database, nl_text

Query data through natural language without writing SQL

exec_sql

执行自定义 SQL 语句

database、sql

手动执行复杂 SQL 查询/操作

exec_sql

Execute custom SQL statement

database, sql

Manually execute complex SQL queries/operations

create_kb

创建 RAG 知识库

database、kb_name

基于数据库数据构建知识库

create_kb

Create RAG knowledge base

database, kb_name

Build knowledge base based on database data

query_kb

RAG 知识库智能问答

database、kb_name、nl_text

通过自然语言查询知识库内容

query_kb

RAG knowledge base intelligent Q&A

database, kb_name, nl_text

Query knowledge base content through natural language

delete_kb

删除 RAG 知识库

kb_name

删除指定的知识库

delete_kb

Delete RAG knowledge base

kb_name

Delete specified knowledge base

list_kb

列出所有 RAG 知识库

无

查看当前可用的知识库

list_kb

List all RAG knowledge bases

None

View currently available knowledge bases

create_model

创建 AI 预测模型

model_name、predict_field

基于数据库数据训练预测模型

create_model

Create AI prediction model

model_name, predict_field

Train prediction model based on database data

analyze_data

自然语言数据分析

database、nl_text

通过自然语言进行数据统计、趋势分析

analyze_data

Natural language data analysis

database, nl_text

Perform data statistics and trend analysis through natural language

3.3 远程 MindsDB 适配规则 | 3.3 Remote MindsDB Adaptation Rules

本技能自动适配本地/远程 MindsDB 部署，Agent 无需额外修改调用逻辑：| This skill automatically adapts to local/remote MindsDB deployments, and the Agent does not need to modify the call logic:

1. 本地调用：无需传递 host、port，默认使用 localhost:47334 | Local Call: No need to pass host and port, default to localhost:47334

2. 远程调用：只需传递 host（远程 MindsDB IP/域名）、port（远程 MindsDB 端口），技能自动延长超时时间至 30 秒 | Remote Call: Only need to pass host (remote MindsDB IP/domain) and port (remote MindsDB port), the skill automatically extends the timeout to 30 seconds

3. 优先级：Agent 传入的 host/port > 环境变量配置 > 默认值 | Priority: Agent-passed host/port > Environment variable configuration > Default value

3.4 未在文档中列出的数据库适配 | 3.4 Adaptation of Databases Not Listed in the Documentation

只要 MindsDB 支持该数据库引擎，本技能即可无缝适配，无需修改代码：| As long as MindsDB supports the database engine, this skill can be seamlessly adapted without modifying code:

- Agent 只需将 db_type 参数设置为「MindsDB 支持的引擎名称」（如 clickhouse、influxdb、oracle、sqlserver 等）| The Agent only needs to set the db_type parameter to the "MindsDB-supported engine name" (e.g., clickhouse, influxdb, oracle, sqlserver, etc.)

- 技能会自动将 db_type 传递给 MindsDB，由 MindsDB 完成数据库连接与适配 | The skill will automatically pass db_type to MindsDB, which completes database connection and adaptation

- 若 db_type 错误（MindsDB 不支持），技能会返回标准化错误提示，告知 Agent 核对引擎名称 | If db_type is incorrect (not supported by MindsDB), the skill will return a standardized error prompt, informing the Agent to check the engine name

3.5 统一返回格式 | 3.5 Unified Return Format

无论操作成功/失败、无论哪种数据库，均返回以下统一格式，Agent 可直接解析：| Regardless of operation success/failure or database type, the following unified format is returned, which can be directly parsed by the Agent:

3.5.1 成功返回（code=0）| 3.5.1 Successful Return (code=0)

{
  "code": 0,
  "msg": "success",
  "data": "具体操作结果（文本/结构化信息，统一格式）| Specific operation result (text/structured information, unified format)"
}

3.5.2 失败返回（code≠0）| 3.5.2 Failed Return (code≠0)

状态码

含义

错误提示示例

排查建议

Status Code

Meaning

Error Prompt Example

Troubleshooting Suggestions

-1

通用失败

"operation failed: unknown error"

1. 检查参数是否完整 2. 确认 MindsDB 版本≥23.11 3. 验证数据源可正常访问

-1

General Failure

"operation failed: unknown error"

1. Check if parameters are complete 2. Confirm MindsDB version ≥23.11 3. Verify that the data source is accessible

-2

参数缺失

"required parameter missing: db_type"

补充对应必传参数，参考 3.1 通用参数说明

-2

Missing Parameters

"required parameter missing: db_type"

Supplement the corresponding required parameters, refer to 3.1 Universal Parameters

-3

引擎不支持

"database engine not supported: xxx"

1. 核对 db_type 为 MindsDB 支持的引擎 2. 参考 MindsDB 官方引擎列表

-3

Unsupported Engine

"database engine not supported: xxx"

1. Verify that db_type is a MindsDB-supported engine 2. Refer to the MindsDB official engine list

-4

连接超时

"connection timeout"

1. 延长超时时间 2. 检查网络连通性 3. 确认远程 MindsDB 服务正常运行

-4

Connection Timeout

"connection timeout"

1. Extend timeout 2. Check network connectivity 3. Confirm that the remote MindsDB service is running

-5

查询失败

"query failed: xxx"

1. 检查 SQL 语句是否正确（exec_sql 动作）2. 简化自然语言描述（nl_query 动作）3. 大型查询添加 LIMIT 限制

-5

Query Failure

"query failed: xxx"

1. Check if the SQL statement is correct (exec_sql action) 2. Simplify natural language description (nl_query action) 3. Add LIMIT restriction for large queries

3.6 异常处理规则（Agent 应对策略）| 3.6 Exception Handling Rules (Agent Response Strategy)

异常类型

错误提示特征

Agent 应对动作

Exception Type

Error Prompt Characteristics

Agent Response Action

MindsDB 连接失败

包含“authentication failed”“connection refused”“timeout”

提示用户检查 MindsDB 地址、端口、账号密码；远程调用需确认防火墙开放 47334 端口

MindsDB Connection Failure

Contains "authentication failed", "connection refused", "timeout"

Prompt the user to check the MindsDB address, port, username, and password; for remote calls, confirm that port 47334 is open in the firewall

数据库连接失败

包含“engine not found”

提示用户核对 db_type 为 MindsDB 支持的引擎名称，参考 MindsDB 官方引擎列表

Database Connection Failure

Contains "engine not found"

Prompt the user to verify that db_type is a MindsDB-supported engine name, refer to the MindsDB official engine list

查询超时

包含“timeout”

自动在查询中添加 LIMIT 100 限制结果数量，重新调用技能

Query Timeout

Contains "timeout"

Automatically add LIMIT 100 to limit the number of results in the query and call the skill again

参数缺失

包含“required parameter missing”

提示用户补充对应必传参数（如 db_type、database、nl_text 等）

Missing Parameters

Contains "required parameter missing"

Prompt the user to supplement the corresponding required parameters (e.g., db_type, database, nl_text, etc.)

模型训练失败

包含“training failed”“data abnormal”

提示用户检查训练数据质量（如字段非空、预测字段为数值型/分类型）

Model Training Failure

Contains "training failed", "data abnormal"

Prompt the user to check the quality of training data (e.g., non-null fields, prediction fields are numeric/categorical)

四、使用示例（Agent 调用参考）| IV. Usage Examples (Agent Call Reference)

示例 1：连接本地 MySQL 数据库 | Example 1: Connect to Local MySQL Database

{
  "action": "connect_db",
  "db_type": "mysql",
  "host": "localhost",
  "port": 3306,
  "username": "root",
  "password": "123456",
  "database": "test_db"
}

输出结果 | Output Result

{
  "code": 0,
  "msg": "success",
  "data": {
    "db_type": "mysql",
    "host": "localhost",
    "database": "test_db",
    "available_tables": ["user", "order", "product"]
  }
}

示例 2：连接远程 ClickHouse 数据库（文档未列出）| Example 2: Connect to Remote ClickHouse Database (Not Listed in Documentation)

{
  "action": "connect_db",
  "db_type": "clickhouse",
  "host": "192.168.1.100",
  "port": 8123,
  "username": "default",
  "password": "",
  "database": "test_db"
}

输出结果 | Output Result

{
  "code": 0,
  "msg": "success",
  "data": {
    "db_type": "clickhouse",
    "host": "192.168.1.100",
    "database": "test_db",
    "available_tables": ["sales", "log"]
  }
}

示例 3：自然语言查询数据 | Example 3: Natural Language Data Query

{
  "action": "nl_query",
  "database": "test_db",
  "nl_text": "查询 user 表的总记录数"
}

输出结果 | Output Result

{
  "code": 0,
  "msg": "success",
  "data": {
    "sql": "SELECT COUNT(*) FROM user",
    "result": [{"COUNT(*)": 150}]
  }
}

示例 4：生成数据库数据字典 | Example 4: Generate Database Data Dictionary

{
  "action": "show_table_schema",
  "database": "test_db"
}

输出结果 | Output Result

{
  "code": 0,
  "msg": "success",
  "data": {
    "database": "test_db",
    "table_list": ["user", "order"],
    "tables_detail": {
      "user": {
        "fields": [
          {"name": "id", "type": "int", "nullable": false, "comment": "用户ID"},
          {"name": "name", "type": "varchar", "nullable": false, "comment": "用户名"},
          {"name": "create_time", "type": "datetime", "nullable": true, "comment": "创建时间"}
        ]
      },
      "order": {
        "fields": [
          {"name": "order_id", "type": "varchar", "nullable": false, "comment": "订单ID"},
          {"name": "user_id", "type": "int", "nullable": false, "comment": "用户ID"},
          {"name": "amount", "type": "decimal", "nullable": false, "comment": "订单金额"}
        ]
      }
    }
  }
}

示例 5：创建 AI 预测模型 | Example 5: Create AI Prediction Model

{
  "action": "create_model",
  "database": "test_db",
  "model_name": "sales_predictor",
  "predict_field": "amount"
}

输出结果 | Output Result

{
  "code": 0,
  "msg": "success",
  "data": {
    "model_name": "sales_predictor",
    "predict_field": "amount",
    "database": "test_db",
    "description": "基于 MindsDB Lightwood 引擎，适配所有结构化数据库"
  }
}

示例 6：失败返回示例（参数缺失）| Example 6: Failed Return Example (Missing Parameters)

{
  "action": "connect_db"
}

输出结果 | Output Result

{
  "code": -2,
  "msg": "required parameter missing: db_type | 排查建议：补充对应必传参数，参考 3.1 通用参数说明",
  "data": null
}

示例 7：RAG 知识库创建 | Example 7: RAG Knowledge Base Creation

{
  "action": "create_kb",
  "database": "duck_db",
  "kb_name": "test_rag_kb",
  "top_k": 3,
  "threshold": 0.6
}

输出结果 | Output Result

{
  "code": 0,
  "msg": "RAG operation success: create_kb",
  "data": {
    "kb_name": "test_rag_kb",
    "database": "duck_db",
    "status": "created"
  }
}

示例 8：RAG 知识库智能问答 | Example 8: RAG Knowledge Base Intelligent Q&A

{
  "action": "query_kb",
  "database": "duck_db",
  "kb_name": "test_rag_kb",
  "nl_text": "请查询数据源中的核心数据信息",
  "top_k": 3
}

输出结果 | Output Result

{
  "code": 0,
  "msg": "RAG operation success: query_kb",
  "data": {
    "query": "请查询数据源中的核心数据信息",
    "answer": "根据知识库中的信息，核心数据包括用户信息、订单数据和产品信息",
    "relevant_docs": 3
  }
}

示例 9：列出所有 RAG 知识库 | Example 9: List All RAG Knowledge Bases

{
  "action": "list_kb"
}

输出结果 | Output Result

{
  "code": 0,
  "msg": "RAG operation success: list_kb",
  "data": {
    "knowledge_bases": ["test_rag_kb", "default_kb"]
  }
}

示例 10：删除 RAG 知识库 | Example 10: Delete RAG Knowledge Base

{
  "action": "delete_kb",
  "kb_name": "test_rag_kb"
}

输出结果 | Output Result

{
  "code": 0,
  "msg": "RAG operation success: delete_kb",
  "data": {
    "kb_name": "test_rag_kb",
    "status": "deleted"
  }
}

五、配置要求 | V. Configuration Requirements

- MindsDB 版本：≥ 23.11（需启用 MCP 接口）| MindsDB Version: ≥ 23.11 (MCP interface must be enabled)

- 运行环境：Python 3.8+ | Operating Environment: Python 3.8+

- 依赖库：mcp ≥ 0.1.0、requests ≥ 2.31.0 | Dependencies: mcp ≥ 0.1.0, requests ≥ 2.31.0

- 网络要求：Agent 与 MindsDB 服务可正常连通（本地/远程均可）| Network Requirements: The Agent can normally connect to the MindsDB service (local or remote)

六、注意事项 | VI. Notes

- 本技能不存储任何用户数据，所有操作均在 MindsDB 服务端执行 | This skill does not store any user data; all operations are performed on the MindsDB server

- 支持 200+ 数据源，不限于文档示例，只要 MindsDB 支持即可使用 | Supports 200+ data sources, not limited to the examples in the documentation, as long as MindsDB supports them

- 远程 MindsDB 需开放 47334 端口，确保 Agent 可正常访问 | The remote MindsDB needs to open port 47334 to ensure normal access by the Agent

- 大型数据库查询建议使用 LIMIT 限制结果数量，避免查询超时 | For large database queries, it is recommended to use LIMIT to limit the number of results to avoid query timeout

- 新增 MindsDB 支持的数据库时，无需修改技能代码，直接传递对应 db_type 即可 | When adding a new MindsDB-supported database, there is no need to modify the skill code, just pass the corresponding db_type

- 若出现“authentication failed”，请检查 MindsDB 账号密码是否正确，远程连接需验证账号权限 | If "authentication failed" occurs, check if the MindsDB username and password are correct; remote connections require verifying account permissions

七、故障排除 | VII. Troubleshooting

常见故障及解决方法 | Common Faults and Solutions

1. 故障：连接数据库提示“engine not found” | Fault: "engine not found" when connecting to the database
解决方法：核对 db_type 为 MindsDB 支持的引擎名称（如 mysql、clickhouse），参考 MindsDB 官方引擎列表 | Solution: Verify that db_type is a MindsDB-supported engine name (e.g., mysql, clickhouse), refer to the MindsDB official engine list

2. 故障：远程连接超时 | Fault: Remote connection timeout
解决方法：1. 确认远程 MindsDB 服务正常运行 2. 检查防火墙是否开放 47334 端口 3. 延长超时时间至 30 秒以上 | Solution: 1. Confirm that the remote MindsDB service is running 2. Check if the firewall opens port 47334 3. Extend the timeout to more than 30 seconds

3. 故障：SQL 执行失败 | Fault: SQL execution failed
解决方法：1. 检查 SQL 语句语法是否正确 2. 确认数据库表/字段存在 3. 验证账号是否有执行权限 | Solution: 1. Check if the SQL statement syntax is correct 2. Confirm that the database table/field exists 3. Verify that the account has execution permissions

4. 故障：模型训练失败 | Fault: Model training failed
解决方法：1. 检查训练数据质量（字段非空、预测字段为数值型/分类型）2. 确认数据库连接正常 3. 减少训练数据量重试 | Solution: 1. Check the quality of training data (non-null fields, prediction fields are numeric/categorical) 2. Confirm that the database connection is normal 3. Reduce the amount of training data and try again

八、参考资料 | VIII. Reference Materials

- MindsDB 官方文档：https://docs.mindsdb.com/

- MindsDB 支持的数据库引擎列表：https://docs.mindsdb.com/connecting-to-databases

- MCP 协议规范：https://docs.mindsdb.com/mcp-protocol

- 知识库构建指南：references/knowledge-base.md

- 工业设备监控案例：references/industrial-monitoring-case.md

- 数据源配置参考：references/data-sources.md

- 智能分析指南：references/intelligent-analysis.md

- MindsDB工具介绍：references/mindsdb-tools.md

- MLOps高级指南：references/mlops-advanced.md

- SDK和API参考：references/sdk-api.md

- SQL示例集合：references/sql-examples.md

- 流处理管道指南：references/streaming-pipelines.md
