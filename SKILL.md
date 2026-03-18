---
name: mindsdb-mcp-skill
description: MindsDB MCP服务器交互技能，用于通过自然语言查询和操作200+企业级数据源。支持数据库查询、数据分析、AI模型创建、RAG知识库构建等任务。
version: 1.2.0
author: yejinlei
---

# MindsDB MCP Skill | MindsDB MCP Skill

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
- chromadb：轻量级向量数据库
- sentence-transformers：提供all-MiniLM-L6-v2嵌入模型

### 快速开始 | Quick Start

```python
from scripts.mindsdb_skill import mindsdb_skill_entry

# 连接MySQL数据源
params = {
    "action": "connect_db",
    "db_type": "mysql",
    "host": "localhost",
    "port": 3306,
    "username": "root",
    "password": "123456"
}
result = mindsdb_skill_entry(params)
print(result)
```

### RAG知识库全流程 | RAG Knowledge Base Full Process

```python
from scripts.mindsdb_skill import mindsdb_skill_entry
import json

# 基础配置
base_config = {
    "host": "localhost",
    "port": 47334,
    "username": "admin",
    "password": "password123",
    "database": "mysql_db"
}

# 1. 创建RAG知识库
create_kb = {**base_config, "action": "create_kb", "kb_name": "test_rag_kb"}
create_result = mindsdb_skill_entry(create_kb)

# 2. 知识库智能问答
query_kb = {**base_config, "action": "query_kb", "kb_name": "test_rag_kb", "nl_text": "查询核心数据信息"}
query_result = mindsdb_skill_entry(query_kb)
```

## 核心功能 | Core Functions

### 数据源管理 | Data Source Management

| 动作 | 必传参数 | 功能说明 |
|------|---------|----------|
| connect_db | db_type | 连接指定类型的数据源，支持MySQL、PostgreSQL、MongoDB等200+类型 |
| list_databases | 无 | 列出所有已连接的数据源 |
| show_table_schema | database | 查看指定数据源的所有数据表结构 |

### 数据交互 | Data Interaction

| 动作 | 必传参数 | 功能说明 |
|------|---------|----------|
| nl_query | database、nl_text | 通过自然语言查询指定数据源的数据，无需编写SQL |
| exec_sql | database、sql | 执行自定义SQL语句，操作指定数据源 |
| analyze_data | database、nl_text | 对指定数据源进行自然语言驱动的数据分析 |

### RAG知识库 | RAG Knowledge Base

| 动作 | 必传参数 | 可选参数 | 功能说明 |
|------|---------|---------|----------|
| create_kb | database、kb_name | top_k、threshold | 创建RAG知识库，关联指定数据源 |
| query_kb | database、kb_name、nl_text | top_k、threshold | 向指定知识库发送自然语言查询 |
| delete_kb | kb_name | 无 | 删除指定名称的RAG知识库 |
| list_kb | 无 | 无 | 列出所有已创建的RAG知识库 |

### AI模型 | AI Models

| 动作 | 必传参数 | 功能说明 |
|------|---------|----------|
| create_model | model_name、predict_field | 基于指定数据源创建预测模型，指定预测字段 |

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

- 0：操作成功
- -1：缺失必传参数action
- -2：不支持的action
- -3：缺失当前action的必传参数
- -4：MCP接口请求失败
- -5：MindsDB连接超时
- -6：MindsDB服务不可达
- -7：HTTP请求异常
- -8：未知异常

## 注意事项 | Notes

- 创建RAG知识库前，必须先通过connect_db连接数据源
- RAG知识库的名称（kb_name）需唯一，重复创建会返回错误
- 检索参数top_k（默认5）和threshold（默认0.7）可根据需求调整
- 首次使用本地RAG时会自动下载all-MiniLM-L6-v2模型（约80MB）
- 本地RAG默认使用内存存储，重启后数据会丢失（可配置持久化）

## 项目结构 | Project Structure

```
mindsdb-mcp-skill/
├── scripts/
│   ├── data_dictionary.py  # 数据字典实现
│   └── mindsdb_skill.py    # 核心技能代码
├── evals/
│   └── evals.json          # 测试用例
├── references/             # 参考文档
├── README.md               # 说明文档
├── SKILL.md                # 技能定义文件
└── mcp.json                # MCP配置文件
```
