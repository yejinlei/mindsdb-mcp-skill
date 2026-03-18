# MindsDB MCP Skill

## 项目简介 | Project Introduction

基于MindsDB MCP接口开发的Python技能包，核心支持RAG知识库全流程操作，同时兼容200+企业级数据源的自然语言交互、SQL执行、模型训练等功能，可直接集成到Agent系统，实现数据源与RAG知识库的一站式管理。

**核心价值**：任意 Agent（包括 AI IDE）可通过本技能实现 NLP2SQL 能力，无需在 MindsDB EDIT 内定义 Agent+RAG，通过外部 Agent+SKILL+MindsDB 的组合方式，大大提升效率和通用性。

**Core Value**: Any Agent (including AI IDE) can implement NLP2SQL capabilities through this skill, without defining Agent+RAG within MindsDB EDIT. The combination of external Agent+SKILL+MindsDB greatly improves efficiency and versatility.

## 一、功能概述 | I. Function Overview

本技能包以RAG（检索增强生成）为核心，封装了MindsDB MCP接口的常用操作，提供标准化的调用入口和返回格式，降低MindsDB二次开发门槛，适用于需要快速集成RAG能力、对接多数据源的场景。

This skill package is centered around RAG (Retrieval-Augmented Generation), encapsulating common operations of the MindsDB MCP interface, providing standardized call entry points and return formats, reducing the threshold for MindsDB secondary development, and suitable for scenarios requiring rapid integration of RAG capabilities and connection to multiple data sources.

### 核心功能 | Core Functions

- **RAG知识库全流程**：创建知识库、知识库智能问答、删除知识库、列出所有知识库，支持检索参数（top_k、相关性阈值）自定义。
  **RAG Knowledge Base Full Process**: Create knowledge base, intelligent Q&A with knowledge base, delete knowledge base, list all knowledge bases, support custom retrieval parameters (top_k, relevance threshold).

- **本地RAG备用方案**：当MindsDB未配置embedding model时，自动切换到本地RAG系统（ChromaDB + all-MiniLM-L6-v2），优先从国内源下载模型，确保RAG功能始终可用。
  **Local RAG Alternative**: When MindsDB embedding model is not configured, automatically switch to local RAG system (ChromaDB + all-MiniLM-L6-v2), prioritize downloading models from domestic sources to ensure RAG functionality is always available.

- **数据源管理**：连接多类型数据源（MySQL、CSV、Excel等）、列出所有数据源、查看数据表结构。
  **Data Source Management**: Connect multiple types of data sources (MySQL, CSV, Excel, etc.), list all data sources, view data table structures.

- **数据交互**：自然语言查询数据、执行自定义SQL、数据智能分析。
  **Data Interaction**: Natural language data query, execute custom SQL, intelligent data analysis.

- **模型训练**：基于数据源创建预测模型，支持指定预测字段。
  **Model Training**: Create prediction models based on data sources, support specifying prediction fields.

- **异常处理**：完善的参数校验和异常捕获，提供RAG专属错误提示，便于调试。
  **Exception Handling**: Comprehensive parameter validation and exception capture, providing RAG-specific error prompts for easy debugging.

## 二、环境准备 | II. Environment Preparation

### 2.1 依赖安装 | 2.1 Dependency Installation

安装技能包所需依赖，执行以下命令：

Install the dependencies required for the skill package by executing the following command:

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
│   └── mindsdb_skill.py  # 核心技能代码（包含RAG全流程实现）
├── evals/
│   └── evals.json        # 测试用例
├── references/
│   ├── knowledge-base.md  # 知识库构建指南
│   └── ...
├── README.md             # 说明文档
├── SKILL.md              # 技能定义文件
└── mcp.json              # MCP配置文件
```

### 3.2 基础调用示例 | 3.2 Basic Call Examples

导入技能包，通过入口函数mindsdb_skill_entry()调用各类功能，传入参数字典即可获取标准化返回结果。

Import the skill package and call various functions through the entry function mindsdb_skill_entry(), passing in a parameter dictionary to get standardized return results.

#### 示例1：连接MySQL数据源 | Example 1: Connect to MySQL Data Source

```python
from scripts.mindsdb_skill import mindsdb_skill_entry

# 连接参数
params = {
    "action": "connect_db",
    "db_type": "mysql",  # 数据源类型（支持所有MindsDB兼容类型）
    "host": "localhost",
    "port": 3306,
    "username": "root",
    "password": "123456"
}

# 执行连接
result = mindsdb_skill_entry(params)
print(result)
```

#### 示例2：RAG知识库全流程测试（核心） | Example 2: RAG Knowledge Base Full Process Test (Core)

```python
from scripts.mindsdb_skill import mindsdb_skill_entry
import json

# 基础配置（已连接MySQL数据源，数据源名称为mysql_db）
base_config = {
    "host": "localhost",
    "port": 47334,
    "username": "admin",
    "password": "password123",
    "database": "mysql_db"
}

# 1. 创建RAG知识库（设置检索参数top_k=3，相关性阈值=0.6）
create_kb = {**base_config, "action": "create_kb", "kb_name": "test_rag_kb", "top_k": 3, "threshold": 0.6}
create_result = mindsdb_skill_entry(create_kb)
print("创建知识库结果：", json.dumps(create_result, ensure_ascii=False, indent=2))

# 2. 列出所有RAG知识库
list_kb = {**base_config, "action": "list_kb"}
list_result = mindsdb_skill_entry(list_kb)
print("所有知识库列表：", json.dumps(list_result, ensure_ascii=False, indent=2))

# 3. 知识库智能问答（RAG核心功能）
query_kb = {**base_config, "action": "query_kb", "kb_name": "test_rag_kb", "nl_text": "查询数据源中的核心数据信息", "top_k": 3}
query_result = mindsdb_skill_entry(query_kb)
print("问答结果：", json.dumps(query_result, ensure_ascii=False, indent=2))

# 4. 删除RAG知识库
delete_kb = {**base_config, "action": "delete_kb", "kb_name": "test_rag_kb"}
delete_result = mindsdb_skill_entry(delete_kb)
print("删除知识库结果：", json.dumps(delete_result, ensure_ascii=False, indent=2))
```

## 四、核心功能详细说明 | IV. Detailed Core Function Description

### 4.1 RAG知识库操作（核心） | 4.1 RAG Knowledge Base Operations (Core)

RAG相关操作是本技能包的核心，支持创建、查询、删除、列表全流程，所有操作均通过MCP接口与MindsDB交互，自动完成数据向量化、检索匹配等底层逻辑。当MindsDB未配置embedding model时，技能会自动切换到本地RAG系统（ChromaDB + all-MiniLM-L6-v2）。

RAG-related operations are the core of this skill package, supporting the full process of creation, querying, deletion, and listing. All operations interact with MindsDB through the MCP interface, automatically completing underlying logic such as data vectorization and retrieval matching. When MindsDB embedding model is not configured, the skill will automatically switch to the local RAG system (ChromaDB + all-MiniLM-L6-v2).

| 动作（action） | 必传参数 | 可选参数 | 功能说明 |
|---------------|---------|---------|----------|
| create_kb | database、kb_name | top_k、threshold | 创建RAG知识库，关联指定数据源，可配置检索返回数量和相关性阈值 |
| query_kb | database、kb_name、nl_text | top_k、threshold | 向指定知识库发送自然语言查询，返回相关性匹配的结果 |
| delete_kb | kb_name | 无 | 删除指定名称的RAG知识库 |
| list_kb | 无 | 无 | 列出所有已创建的RAG知识库 |

| Action | Required Parameters | Optional Parameters | Function Description |
|--------|-------------------|-------------------|---------------------|
| create_kb | database, kb_name | top_k, threshold | Create RAG knowledge base, associate with specified data source, configurable retrieval return quantity and relevance threshold |
| query_kb | database, kb_name, nl_text | top_k, threshold | Send natural language query to specified knowledge base, return relevance-matched results |
| delete_kb | kb_name | None | Delete RAG knowledge base with specified name |
| list_kb | None | None | List all created RAG knowledge bases |

### 4.2 其他常用操作 | 4.2 Other Common Operations

| 动作（action） | 必传参数 | 功能说明 |
|---------------|---------|----------|
| connect_db | db_type | 连接指定类型的数据源，支持MySQL、PostgreSQL、CSV等200+类型 |
| list_databases | 无 | 列出所有已连接的数据源 |
| show_table_schema | database | 查看指定数据源的所有数据表结构 |
| nl_query | database、nl_text | 通过自然语言查询指定数据源的数据，无需编写SQL |
| exec_sql | database、sql | 执行自定义SQL语句，操作指定数据源 |
| create_model | model_name、predict_field | 基于指定数据源创建预测模型，指定预测字段 |
| analyze_data | database、nl_text | 对指定数据源进行自然语言驱动的数据分析 |

| Action | Required Parameters | Function Description |
|--------|-------------------|---------------------|
| connect_db | db_type | Connect to specified type of data source, supporting MySQL, PostgreSQL, CSV, etc. (200+ types) |
| list_databases | None | List all connected data sources |
| show_table_schema | database | View all data table structures of specified data source |
| nl_query | database, nl_text | Query data from specified data source through natural language, no need to write SQL |
| exec_sql | database, sql | Execute custom SQL statements to operate specified data source |
| create_model | model_name, predict_field | Create prediction model based on specified data source, specify prediction field |
| analyze_data | database, nl_text | Perform natural language-driven data analysis on specified data source |

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

- 0：操作成功
  0: Operation successful

- -1：缺失必传参数action
  -1: Missing required parameter action

- -2：不支持的action
  -2: Unsupported action

- -3：缺失当前action的必传参数
  -3: Missing required parameters for current action

- -4：MCP接口请求失败（RAG操作会补充专属错误提示）
  -4: MCP interface request failed (RAG operations will add specific error prompts)

- -5：MindsDB连接超时
  -5: MindsDB connection timeout

- -6：MindsDB服务不可达
  -6: MindsDB service unreachable

- -7：HTTP请求异常
  -7: HTTP request exception

- -8：未知异常（RAG相关异常会补充专属提示）
  -8: Unknown exception (RAG-related exceptions will add specific prompts)

## 六、注意事项 | VI. Notes

- 创建RAG知识库（create_kb）前，必须先通过connect_db连接数据源，否则会报错。
  Before creating a RAG knowledge base (create_kb), you must first connect to the data source through connect_db, otherwise an error will be reported.

- RAG知识库的名称（kb_name）需唯一，重复创建会返回错误。
  The name of the RAG knowledge base (kb_name) must be unique; duplicate creation will return an error.

- 检索参数top_k（默认5）和threshold（默认0.7）可根据需求调整，threshold值越高，检索结果相关性越强。
  The retrieval parameters top_k (default 5) and threshold (default 0.7) can be adjusted according to needs; the higher the threshold value, the stronger the relevance of retrieval results.

- **本地RAG注意事项**：
  - 首次使用本地RAG时会自动从国内源（https://hf-mirror.com）下载all-MiniLM-L6-v2模型（约80MB），解决网络问题
  - 当模型下载失败时，会自动使用基于TF-IDF的检索作为降级方案
  - 本地RAG默认使用内存存储，重启后数据会丢失（可配置持久化）
  - 本地RAG的性能取决于硬件，但对于一般场景足够使用
  
  **Local RAG Notes**:
  - The first time you use local RAG, it will automatically download the all-MiniLM-L6-v2 model (about 80MB) from domestic sources (https://hf-mirror.com) to solve network issues
  - When model download fails, it will automatically use TF-IDF-based retrieval as a fallback solution
  - Local RAG uses memory storage by default, and data will be lost after restart (persistence can be configured)
  - The performance of local RAG depends on hardware, but it is sufficient for general scenarios

- 测试代码位于mindsdb_skill.py末尾，可直接运行，需提前修改base_config中的数据源信息。
  The test code is located at the end of mindsdb_skill.py and can be run directly, but you need to modify the data source information in base_config in advance.

- 若MindsDB服务部署在远程服务器，需修改host参数为远程IP，并确保端口可访问。
  If the MindsDB service is deployed on a remote server, you need to modify the host parameter to the remote IP and ensure the port is accessible.

## 七、扩展说明 | VII. Extension Instructions

- 本技能包可直接集成到各类Agent系统，只需调用mindsdb_skill_entry()入口函数，传入符合要求的参数即可。
  This skill package can be directly integrated into various Agent systems by simply calling the mindsdb_skill_entry() entry function and passing in the required parameters.

- 支持扩展更多MCP接口操作，可在_generate_mcp_request()方法中添加新的action逻辑。
  Supports extending more MCP interface operations; new action logic can be added in the _generate_mcp_request() method.

- RAG底层依赖MindsDB的知识库功能，若需自定义向量化模型，可在MindsDB中进行配置后，本技能包无需修改即可兼容。
  RAG relies on MindsDB's knowledge base functionality at the bottom; if you need to customize the vectorization model, you can configure it in MindsDB, and this skill package will be compatible without modification.

## 参考资料 | VIII. Reference Materials

- **知识库构建指南**：references/knowledge-base.md - 详细的RAG知识库构建流程和示例
  **Knowledge Base Construction Guide**: references/knowledge-base.md - Detailed RAG knowledge base construction process and examples

- **工业设备监控案例**：references/industrial-monitoring-case.md - TDengine时序数据库实际应用案例
  **Industrial Equipment Monitoring Case**: references/industrial-monitoring-case.md - TDengine time-series database practical application case

- **数据源配置参考**：references/data-sources.md - 各种数据库连接配置示例
  **Data Source Configuration Reference**: references/data-sources.md - Various database connection configuration examples

- **智能分析指南**：references/intelligent-analysis.md - 数据分析方法和示例
  **Intelligent Analysis Guide**: references/intelligent-analysis.md - Data analysis methods and examples

- **MindsDB工具介绍**：references/mindsdb-tools.md - MindsDB工具使用指南
  **MindsDB Tools Introduction**: references/mindsdb-tools.md - MindsDB tool usage guide

- **MLOps高级指南**：references/mlops-advanced.md - 模型部署和监控最佳实践
  **MLOps Advanced Guide**: references/mlops-advanced.md - Model deployment and monitoring best practices

- **SDK和API参考**：references/sdk-api.md - MindsDB编程接口说明
  **SDK and API Reference**: references/sdk-api.md - MindsDB programming interface description

- **SQL示例集合**：references/sql-examples.md - 常见SQL查询和操作示例
  **SQL Examples Collection**: references/sql-examples.md - Common SQL query and operation examples

- **流处理管道指南**：references/streaming-pipelines.md - 实时数据处理示例
  **Streaming Pipeline Guide**: references/streaming-pipelines.md - Real-time data processing examples

- **MindsDB官方文档**：https://docs.mindsdb.com/  **MindsDB Official Documentation**: https://docs.mindsdb.com/
