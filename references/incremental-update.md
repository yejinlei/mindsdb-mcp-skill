# 增量更新功能 | Incremental Update

当目标数据库新增数据或结构变更时，本技能支持**增量更新**，避免全量重建的开销。

## 增量更新原理

- 基于时间戳检测变更：比较现有数据字典的 `last_updated` 时间戳
- 只处理变更的表：检测行数变化、新增表、删除表
- 智能合并更新：使用 `merge_with_existing` 方法合并新旧数据
- 自动同步 RAG：更新数据字典后自动更新向量数据库

## 使用方式

```python
from scripts.workflow_rag_build import rag_build_workflow_entry

# 1. 增量刷新数据字典（默认模式）
params = {
    "action": "refresh_data_dict",
    "database": "warehouse_db",
    "mode": "incremental"  # 增量模式（默认）
}
result = rag_build_workflow_entry(params)
print(result)

# 返回示例：
# {
#   "code": 0,
#   "msg": "Data dictionary refreshed",
#   "data": {
#     "database": "warehouse_db",
#     "mode": "incremental",
#     "force_rebuild": false,
#     "tables_added": 2,
#     "tables_updated": 1,
#     "columns_added": 15,
#     "columns_updated": 3,
#     "relationships_added": 5,
#     "total_changes": 26
#   }
# }

# 2. 全量刷新数据字典（强制重建）
params = {
    "action": "refresh_data_dict",
    "database": "warehouse_db",
    "mode": "full",  # 全量模式
    "force_rebuild": True  # 强制重建
}
result = rag_build_workflow_entry(params)
```

## 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|----------|------|
| action | string | - | 固定为 `"refresh_data_dict"` |
| database | string | - | 数据库名称 |
| mode | string | `"incremental"` | 更新模式：`"incremental"`（增量）、`"full"`（全量） |
| force_rebuild | boolean | `false` | 是否强制重建（全量提取） |

## 返回字段说明

| 字段 | 说明 |
|------|------|
| tables_added | 新增的表数量 |
| tables_updated | 更新的表数量 |
| columns_added | 新增的列数量 |
| columns_updated | 更新的列数量 |
| relationships_added | 新增的关系数量 |
| total_changes | 总变更数量 |
| mode | 使用的更新模式 |

## 增量更新 vs 全量更新

| 场景 | 推荐模式 | 原因 |
|--------|-----------|------|
| 日常数据变更 | `incremental` | 只处理变更部分，速度快 |
| 新增少量表 | `incremental` | 只处理新表，保留现有数据 |
| 数据库结构大改 | `full` + `force_rebuild` | 完全重建，确保一致性 |
| 首次初始化 | `full` | 全量提取所有元数据 |

## 自动触发场景

- 数据库新增表时：自动检测并添加到数据字典
- 表行数变化时：自动更新表的元数据
- RAG 查询时：自动使用最新的元数据
