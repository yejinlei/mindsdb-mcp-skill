# MindsDB MCP Skill v2.0

## 项目简介 | Project Introduction

基于MindsDB MCP接口开发的Python技能包，采用**三模块架构**设计，支持RAG知识库全流程操作、NLP2SQL自然语言查询、智能数据分析等功能，可直接集成到Agent系统，实现数据源与RAG知识库的一站式管理。

**核心价值**：任意 Agent（包括 AI IDE）可通过本技能实现 NLP2SQL 能力，无需在 MindsDB EDIT 内定义 Agent+RAG，通过外部 Agent+SKILL+MindsDB 的组合方式，大大提升效率和通用性。

**Core Value**: Any Agent (including AI IDE) can implement NLP2SQL capabilities through this skill, without defining Agent+RAG within MindsDB EDIT. The combination of external Agent+SKILL+MindsDB greatly improves efficiency and versatility.

## 架构设计 | Architecture Design

本技能采用**三模块架构**，职责分离清晰，便于维护和扩展：

### 模块1：db_connector（公共数据库连接模块）
- **职责**：统一管理数据库连接，封装MCP请求
- **功能**：
  - MindsDB服务自动检测、安装和启动
  - 数据库连接管理（DuckDB、MySQL、TDengine等）
  - 统一MCP请求发送和响应处理
  - 连接信息缓存

### 模块2：workflow_rag_build（本地RAG构建与管理工作流）
- **职责**：构建和维护本地RAG知识库
- **功能**：
  - 本地RAG系统初始化（ChromaDB + all-MiniLM-L6-v2）
  - 知识库管理（创建、列表、删除）
  - 数据字典管理（获取、搜索、刷新）
  - 数据持久化管理

### 模块3：workflow_rag_analysis（基于RAG的NLP2SQL和数据分析工作流）
- **职责**：利用RAG进行智能数据分析和查询
- **功能**：
  - 自然语言到SQL转换（NLP2SQL）
  - 智能数据分析
  - 知识库智能问答
  - AI模型创建与预测

## 一、功能概述 | I. Function Overview

本技能包以RAG（检索增强生成）为核心，封装了MindsDB MCP接口的常用操作，提供标准化的调用入口和返回格式，降低MindsDB二次开发门槛，适用于需要快速集成RAG能力、对接多数据源的场景。

This skill package is centered around RAG (Retrieval-Augmented Generation), encapsulating common operations of the MindsDB MCP interface, providing standardized call entry points and return formats, reducing the threshold for MindsDB secondary development, and suitable for scenarios requiring rapid integration of RAG capabilities and connection to multiple data sources.

### 核心功能 | Core Functions

- **RAG知识库全流程**：创建知识库、知识库智能问答、删除知识库、列出所有知识库，支持检索参数（top_k、相关性阈值）自定义。
  **RAG Knowledge Base Full Process**: Create knowledge base, intelligent Q&A with knowledge base, delete knowledge base, list all knowledge bases, support custom retrieval parameters (top_k, relevance threshold).

- **本地RAG备用方案**：当MindsDB未配置embedding model时，自动切换到本地RAG系统（ChromaDB + all-MiniLM-L6-v2），优先从国内源下载模型，确保RAG功能始终可用。
  **Local RAG Alternative**: When MindsDB embedding model is not configured, automatically switch to local RAG system (ChromaDB + all-MiniLM-L6-v2), prioritize downloading models from domestic sources to ensure RAG functionality is always available.

- **数据源管理**：连接多类型数据源（MySQL、DuckDB、TDengine等）、列出所有数据源、查看数据表结构。
  **Data Source Management**: Connect multiple types of data sources (MySQL, DuckDB, TDengine, etc.), list all data sources, view data table structures.

- **NLP2SQL自然语言查询**：将自然语言自动转换为SQL语句并执行，无需用户编写SQL。
  **NLP2SQL Natural Language Query**: Automatically convert natural language to SQL statements and execute, no need for users to write SQL.

- **数据交互**：自然语言查询数据、执行自定义SQL、数据智能分析。
  **Data Interaction**: Natural language data query, execute custom SQL, intelligent data analysis.

- **模型训练**：基于数据源创建预测模型，支持指定预测字段。
  **Model Training**: Create prediction models based on data sources, support specifying prediction fields.

- **异常处理**：完善的参数校验和异常捕获，提供RAG专属错误提示，便于调试。
  **Exception Handling**: Comprehensive parameter validation and exception capture, providing RAG-specific error prompts for easy debugging.

## 二、环境准备 | II. Environment Preparation

### 2.1 依赖安装 | 2.1 Dependency Installation

安装技能包所需依赖，执行以下命令：

```bash
pip install requests
```

**本地RAG依赖**：当MindsDB RAG不可用时，技能会自动安装以下依赖：
- chromadb：轻量级向量数据库
- sentence-transformers：提供all-MiniLM-L6-v2嵌入模型

**Local RAG Dependencies**: When MindsDB RAG is unavailable, the skill will automatically install the following dependencies:
- chromadb: Lightweight vector database
- sentence-transformers: Provides all-MiniLM-L6-v2 embedding model

### 2.2 MindsDB环境要求 | 2.2 MindsDB Environment Requirements

- **自动安装和启动**：本技能包支持自动检测、安装和启动MindsDB服务，无需手动操作。当您首次使用技能时，它会：
  1. 检查MindsDB是否已安装
  2. 如果未安装，自动执行 `pip install mindsdb`
  3. 启动MindsDB服务（默认端口47334）
  4. 验证服务是否正常运行

- **手动安装选项**：如果您希望手动安装和配置MindsDB，可以：
  1. 执行 `pip install mindsdb` 安装MindsDB
  2. 执行 `python -m mindsdb` 启动MindsDB服务
  3. 确保服务在默认端口47334上运行

- MindsDB版本：建议v23.10及以上（支持MCP接口和RAG知识库功能）。
  MindsDB version: v23.10 or above is recommended (supports MCP interface and RAG knowledge base functionality).

- 确保MindsDB服务可正常访问（本地部署默认地址：http://localhost:47334）。
  Ensure the MindsDB service is accessible (default local deployment address: http://localhost:47334).

### 2.3 环境变量配置（可选） | 2.3 Environment Variable Configuration (Optional)

可通过环境变量配置MindsDB连接信息，优先级高于代码默认值，避免硬编码敏感信息：

You can configure MindsDB connection information through environment variables, which have higher priority than default values in code to avoid hardcoding sensitive information:

```bash
# Linux/Mac
export MINDSDB_HOST=localhost
export MINDSDB_PORT=47334
export MINDSDB_USERNAME=admin
export MINDSDB_PASSWORD=password123
```

```bash
# Windows（命令行）
set MINDSDB_HOST=localhost
set MINDSDB_PORT=47334
set MINDSDB_USERNAME=admin
set MINDSDB_PASSWORD=password123
```

## 三、快速开始 | III. Quick Start

### 3.1 项目结构 | 3.1 Project Structure

```
mindsdb-mcp-skill/
├── scripts/
│   ├── db_connector.py           # 公共数据库连接模块（新增）
│   ├── workflow_rag_build.py     # 工作流1：本地RAG构建与管理（新增）
│   ├── workflow_rag_analysis.py  # 工作流2：基于RAG的NLP2SQL和数据分析（新增）
│   ├── data_dictionary.py        # 数据字典实现
│   └── mindsdb_skill.py          # 原核心技能代码（保留兼容）
├── evals/
│   └── evals.json                # 测试用例（已更新为三模块架构）
├── data/
│   ├── chromadb_persist/         # RAG向量数据持久化目录
│   └── data_dictionary.json      # 数据字典持久化文件
├── references/                   # 参考文档
├── README.md                     # 说明文档
├── SKILL.md                      # 技能定义文件
└── mcp.json                      # MCP配置文件
```

### 3.2 基础调用示例 | 3.2 Basic Call Examples

#### 方式1：使用公共数据库连接模块 | Method 1: Use Database Connector Module

```python
from scripts.db_connector import get_db_connector

# 获取数据库连接器
db = get_db_connector()

# 连接DuckDB数据库
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

#### 方式2：使用RAG构建工作流 | Method 2: Use RAG Build Workflow

```python
from scripts.workflow_rag_build import rag_build_workflow_entry

# 创建RAG知识库
params = {
    "action": "create_kb",
    "kb_name": "weekly_report_kb",
    "database": "warehouse_db"
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

#### 方式3：使用RAG分析工作流 | Method 3: Use RAG Analysis Workflow

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

### 3.3 RAG知识库全流程测试（核心） | 3.3 RAG Knowledge Base Full Process Test (Core)

```python
from scripts.workflow_rag_build import rag_build_workflow_entry
from scripts.workflow_rag_analysis import rag_analysis_workflow_entry
import json

# 基础配置（已连接MySQL数据源，数据源名称为mysql_db）
base_config = {
    "host": "localhost",
    "port": 47334,
    "username": "admin",
    "password": "password123",
    "database": "warehouse_db"
}

# 1. 创建RAG知识库（工作流1）
create_kb = {**base_config, "action": "create_kb", "kb_name": "test_rag_kb", "top_k": 3, "threshold": 0.6}
create_result = rag_build_workflow_entry(create_kb)
print("创建知识库结果：", json.dumps(create_result, ensure_ascii=False, indent=2))

# 2. 列出所有RAG知识库
list_kb = {**base_config, "action": "list_kb"}
list_result = rag_build_workflow_entry(list_kb)
print("所有知识库列表：", json.dumps(list_result, ensure_ascii=False, indent=2))

# 3. 知识库智能问答（工作流2）
query_kb = {**base_config, "action": "query_kb", "kb_name": "test_rag_kb", "nl_text": "查询数据源中的核心数据信息", "top_k": 3}
query_result = rag_analysis_workflow_entry(query_kb)
print("问答结果：", json.dumps(query_result, ensure_ascii=False, indent=2))

# 4. 删除RAG知识库
delete_kb = {**base_config, "action": "delete_kb", "kb_name": "test_rag_kb"}
delete_result = rag_build_workflow_entry(delete_kb)
print("删除知识库结果：", json.dumps(delete_result, ensure_ascii=False, indent=2))
```

## 四、核心功能详细说明 | IV. Detailed Core Function Description

### 4.1 模块1：db_connector（公共数据库连接模块） | 4.1 Module 1: db_connector (Database Connector)

| 方法 | 必传参数 | 功能说明 |
|------|---------|----------|
| connect_database | db_type | 连接指定类型的数据源（DuckDB、MySQL、TDengine等） |
| list_databases | 无 | 列出所有已连接的数据源 |
| show_tables | database | 查看指定数据库的所有表 |
| describe_table | database, table | 查看指定表的结构 |
| execute_sql | sql | 执行自定义SQL语句 |

### 4.2 模块2：workflow_rag_build（RAG构建工作流） | 4.2 Module 2: workflow_rag_build (RAG Build Workflow)

| 动作（action） | 必传参数 | 可选参数 | 功能说明 |
|---------------|---------|---------|----------|
| create_kb | kb_name | database, top_k, threshold | 创建RAG知识库，自动提取数据库元数据 |
| list_kb | 无 | 无 | 列出所有已创建的RAG知识库 |
| delete_kb | kb_name | 无 | 删除指定名称的RAG知识库 |
| get_data_dict_summary | 无 | 无 | 获取数据字典摘要信息 |
| search_data_dict | keyword | 无 | 搜索数据字典中的元数据 |
| refresh_data_dict | database | 无 | 刷新指定数据库的数据字典 |

### 4.3 模块3：workflow_rag_analysis（RAG分析工作流） | 4.3 Module 3: workflow_rag_analysis (RAG Analysis Workflow)

| 动作（action） | 必传参数 | 可选参数 | 功能说明 |
|---------------|---------|---------|----------|
| connect_db | db_type | host, port, username, password, database | 连接指定类型的数据源 |
| list_databases | 无 | 无 | 列出所有已连接的数据源 |
| show_table_schema | database | 无 | 查看指定数据源的所有数据表结构 |
| nl_query | database, nl_text | 无 | 通过自然语言查询数据（NLP2SQL） |
| exec_sql | database, sql | 无 | 执行自定义SQL语句 |
| analyze_data | database, nl_text | 无 | 对数据进行自然语言驱动的智能分析 |
| query_kb | kb_name, nl_text | top_k, threshold | 向知识库发送自然语言查询 |
| create_model | model_name, predict_field | database | 创建AI预测模型 |

## 五、返回格式说明 | V. Return Format Description

所有操作的返回结果均为统一JSON格式，便于Agent解析和处理：

All operation return results are in a unified JSON format for easy Agent parsing and processing:

```json
{
  "code": 0,          // 状态码：0=成功，非0=失败
  "msg": "success",   // 状态信息，失败时返回错误详情（RAG操作会有专属提示）
  "data": {}          // 业务数据，成功时返回操作结果（如知识库列表、问答结果等）
}
```

### 状态码说明 | Status Code Description

- **0**：操作成功
  0: Operation successful

- **-1**：缺失必传参数action
  -1: Missing required parameter action

- **-2**：不支持的action
  -2: Unsupported action

- **-3**：缺失当前action的必传参数
  -3: Missing required parameters for current action

- **-4**：MCP接口请求失败（RAG操作会补充专属错误提示）
  -4: MCP interface request failed (RAG operations will add specific error prompts)

- **-5**：MindsDB连接超时
  -5: MindsDB connection timeout

- **-6**：MindsDB服务不可达
  -6: MindsDB service unreachable

- **-7**：HTTP请求异常
  -7: HTTP request exception

- **-8**：未知异常（RAG相关异常会补充专属提示）
  -8: Unknown exception (RAG-related exceptions will add specific prompts)

- **-9**：MindsDB服务未就绪
  -9: MindsDB service not ready

- **-10**：本地RAG初始化失败
  -10: Local RAG initialization failed

## 六、注意事项 | VI. Notes

- 创建RAG知识库（create_kb）前，建议先通过db_connector或workflow_rag_analysis连接数据源。
  Before creating a RAG knowledge base (create_kb), it is recommended to first connect to the data source through db_connector or workflow_rag_analysis.

- RAG知识库的名称（kb_name）需唯一，重复创建会返回错误。
  The name of the RAG knowledge base (kb_name) must be unique; duplicate creation will return an error.

- 检索参数top_k（默认5）和threshold（默认0.7）可根据需求调整，threshold值越高，检索结果相关性越强。
  The retrieval parameters top_k (default 5) and threshold (default 0.7) can be adjusted according to needs; the higher the threshold value, the stronger the relevance of retrieval results.

- **本地RAG注意事项**：
  - 首次使用本地RAG时会自动从国内源（https://hf-mirror.com）下载all-MiniLM-L6-v2模型（约80MB），解决网络问题
  - 当模型下载失败时，会自动使用基于TF-IDF的检索作为降级方案
  - 本地RAG使用ChromaDB持久化存储，数据保存在`data/chromadb_persist`目录
  - 数据字典自动持久化到`data/data_dictionary.json`文件
  
  **Local RAG Notes**:
  - The first time you use local RAG, it will automatically download the all-MiniLM-L6-v2 model (about 80MB) from domestic sources (https://hf-mirror.com) to solve network issues
  - When model download fails, it will automatically use TF-IDF-based retrieval as a fallback solution
  - Local RAG uses ChromaDB persistent storage, data is saved in the `data/chromadb_persist` directory
  - Data dictionary is automatically persisted to the `data/data_dictionary.json` file

- 测试代码位于各模块文件末尾，可直接运行，需提前修改配置中的数据源信息。
  The test code is located at the end of each module file and can be run directly, but you need to modify the data source information in the configuration in advance.

- 若MindsDB服务部署在远程服务器，需修改host参数为远程IP，并确保端口可访问。
  If the MindsDB service is deployed on a remote server, you need to modify the host parameter to the remote IP and ensure the port is accessible.

## 七、扩展说明 | VII. Extension Instructions

- 本技能包可直接集成到各类Agent系统，调用各模块的入口函数即可：
  - db_connector模块：`from scripts.db_connector import get_db_connector`
  - RAG构建工作流：`from scripts.workflow_rag_build import rag_build_workflow_entry`
  - RAG分析工作流：`from scripts.workflow_rag_analysis import rag_analysis_workflow_entry`

- 支持扩展更多MCP接口操作，可在各模块中添加新的action逻辑。
  Supports extending more MCP interface operations; new action logic can be added in each module.

## 八、版本历史 | VIII. Version History

- **v2.0.0** (2026-03-19)：重构为三模块架构（db_connector、workflow_rag_build、workflow_rag_analysis）
  - 新增公共数据库连接模块db_connector
  - 新增RAG构建工作流workflow_rag_build
  - 新增RAG分析工作流workflow_rag_analysis
  - 更新evals.json测试用例为三模块架构
  - 保留原mindsdb_skill.py以兼容旧版本

- **v1.2.0**：原单模块架构版本
