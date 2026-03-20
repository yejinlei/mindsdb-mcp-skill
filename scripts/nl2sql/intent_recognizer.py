#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
意图识别模块
在 RAG 检索之前进行意图分析，提高 SQL 生成准确性
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class IntentType(Enum):
    """意图类型枚举"""
    QUERY = "query"
    COUNT = "count"
    AGGREGATE = "aggregate"
    COMPARE = "compare"
    LIST = "list"
    DETAIL = "detail"
    TREND = "trend"
    UNKNOWN = "unknown"


@dataclass
class Intent:
    """意图识别结果"""
    intent_type: IntentType
    target: str
    action: str
    entities: Dict[str, str] = field(default_factory=dict)
    filters: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    original_text: str = ""
    enhanced_text: str = ""


class IntentRecognizer:
    """意图识别器"""
    
    DEFAULT_BUSINESS_TERMS = {
        "卡点": ["issues", "问题", "风险"],
        "资金流向": ["finance_type", "资金类型", "财务类型"],
        "收入": ["income", "收入类型"],
        "支出": ["expense", "支出类型"],
        "借款": ["loan", "借款类型"],
        "资金需求": ["fund_requirement", "资金需求类型"],
        "部门": ["department", "部门名称"],
        "负责人": ["leader_name", "部门负责人"],
        "项目": ["project", "项目名称"],
        "进度": ["progress", "项目进度"],
        "状态": ["status", "处理状态"],
        "金额": ["amount", "资金金额"],
        "周报": ["weekly_report", "周报表"],
        "人员": ["human_resource", "人力资源"],
        "支持需求": ["support_requests", "支持请求"],
    }
    
    INTENT_PATTERNS = {
        IntentType.COUNT: [
            r"多少|几个|数量|统计.*数量|计数|count",
        ],
        IntentType.AGGREGATE: [
            r"合计|总计|汇总|平均|最大|最小|sum|avg|max|min",
        ],
        IntentType.COMPARE: [
            r"对比|比较|区别|差异|哪个|哪个更",
        ],
        IntentType.LIST: [
            r"列出|所有|全部|查询.*所有|显示.*所有",
        ],
        IntentType.DETAIL: [
            r"详情|详细|具体|详细信息",
        ],
        IntentType.TREND: [
            r"趋势|变化|增长|下降|走势",
        ],
        IntentType.QUERY: [
            r"查询|查找|搜索|显示|获取",
        ],
    }
    
    ACTION_PATTERNS = {
        "list": r"列出|所有|全部|查询",
        "filter": r"条件|筛选|过滤|where",
        "group": r"按.*分组|分类|group by",
        "order": r"排序|排名|order by|top",
        "limit": r"前\d+|top\d+|限制",
    }
    
    def __init__(self, business_terms: Dict[str, List[str]] = None):
        """初始化意图识别器
        
        Args:
            business_terms: 自定义业务术语映射
        """
        self.business_terms = {**self.DEFAULT_BUSINESS_TERMS}
        if business_terms:
            self.business_terms.update(business_terms)
        
        self._build_reverse_mapping()
    
    def add_business_term(self, term: str, mappings: List[str]):
        """动态添加业务术语映射
        
        Args:
            term: 业务术语（如"卡点"）
            mappings: 映射列表（如["issues", "问题"]）
        """
        self.business_terms[term] = mappings
        
        self.term_to_standard[term.lower()] = term
        for mapping in mappings:
            self.term_to_standard[mapping.lower()] = term
    
    def add_business_terms(self, terms: Dict[str, List[str]]):
        """批量添加业务术语映射
        
        Args:
            terms: 术语映射字典
        """
        for term, mappings in terms.items():
            self.add_business_term(term, mappings)
    
    def _build_reverse_mapping(self):
        """构建反向映射：术语 -> 标准词"""
        self.term_to_standard = {}
        for standard, synonyms in self.business_terms.items():
            for synonym in synonyms:
                self.term_to_standard[synonym.lower()] = standard
            self.term_to_standard[standard.lower()] = standard
    
    def recognize(self, nl_text: str) -> Intent:
        """识别用户意图
        
        Args:
            nl_text: 自然语言查询
        
        Returns:
            意图识别结果
        """
        intent_type = self._classify_intent(nl_text)
        target = self._extract_target(nl_text)
        action = self._extract_action(nl_text)
        entities = self._extract_entities(nl_text)
        filters = self._extract_filters(nl_text)
        enhanced_text = self._enhance_text(nl_text, entities)
        
        confidence = self._calculate_confidence(
            intent_type, target, entities, filters
        )
        
        return Intent(
            intent_type=intent_type,
            target=target,
            action=action,
            entities=entities,
            filters=filters,
            confidence=confidence,
            original_text=nl_text,
            enhanced_text=enhanced_text
        )
    
    def _classify_intent(self, nl_text: str) -> IntentType:
        """分类意图类型"""
        text_lower = nl_text.lower()
        
        for intent_type, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return intent_type
        
        return IntentType.QUERY
    
    def _extract_target(self, nl_text: str) -> str:
        """提取查询目标"""
        for term in self.business_terms.keys():
            if term in nl_text:
                return term
        
        for synonym, standard in self.term_to_standard.items():
            if synonym in nl_text.lower():
                return standard
        
        return "unknown"
    
    def _extract_action(self, nl_text: str) -> str:
        """提取操作类型"""
        for action, pattern in self.ACTION_PATTERNS.items():
            if re.search(pattern, nl_text):
                return action
        return "query"
    
    def _extract_entities(self, nl_text: str) -> Dict[str, str]:
        """提取实体并映射到数据库字段"""
        entities = {}
        
        for term, synonyms in self.business_terms.items():
            if term in nl_text:
                entities[term] = synonyms[0]
        
        for synonym, standard in self.term_to_standard.items():
            if synonym in nl_text.lower():
                if standard not in entities:
                    entities[standard] = self.business_terms[standard][0]
        
        return entities
    
    def _extract_filters(self, nl_text: str) -> List[Dict[str, Any]]:
        """提取过滤条件"""
        filters = []
        
        value_patterns = [
            (r"['\"]([^'\"]+)['\"]", "exact"),
            (r"为\s*(\S+)", "equals"),
            (r"等于\s*(\S+)", "equals"),
            (r"是\s*(\S+)", "equals"),
            (r"包含\s*(\S+)", "contains"),
        ]
        
        for pattern, filter_type in value_patterns:
            matches = re.findall(pattern, nl_text)
            for match in matches:
                if len(match) > 0 and len(match) < 50:
                    filters.append({
                        "value": match,
                        "type": filter_type
                    })
        
        return filters[:5]
    
    def _enhance_text(self, nl_text: str, entities: Dict[str, str]) -> str:
        """增强文本：将业务术语替换为数据库字段"""
        enhanced = nl_text
        
        for term, field in entities.items():
            if term in enhanced:
                enhanced = enhanced.replace(term, f"{term}({field})")
        
        return enhanced
    
    def _calculate_confidence(self, intent_type: IntentType, target: str,
                               entities: Dict[str, str], filters: List) -> float:
        """计算置信度"""
        confidence = 0.0
        
        if intent_type != IntentType.UNKNOWN:
            confidence += 0.3
        
        if target != "unknown":
            confidence += 0.3
        
        if entities:
            confidence += min(len(entities) * 0.1, 0.3)
        
        if filters:
            confidence += min(len(filters) * 0.05, 0.1)
        
        return min(confidence, 1.0)
    
    def get_table_suggestions(self, intent: Intent) -> List[str]:
        """根据意图推荐相关表"""
        table_mapping = {
            "卡点": ["odw_weekly_report", "odw_project"],
            "资金流向": ["odw_finance"],
            "部门": ["odw_department"],
            "负责人": ["odw_department"],
            "项目": ["odw_project"],
            "人员": ["odw_human_resource"],
            "周报": ["odw_weekly_report"],
        }
        
        suggestions = []
        target = intent.target
        
        if target in table_mapping:
            suggestions.extend(table_mapping[target])
        
        for entity in intent.entities:
            if entity in table_mapping:
                for table in table_mapping[entity]:
                    if table not in suggestions:
                        suggestions.append(table)
        
        return suggestions
    
    def get_field_suggestions(self, intent: Intent) -> Dict[str, str]:
        """根据意图推荐相关字段"""
        return intent.entities


def get_intent_recognizer(business_terms: Dict[str, List[str]] = None) -> IntentRecognizer:
    """获取意图识别器实例"""
    return IntentRecognizer(business_terms)
