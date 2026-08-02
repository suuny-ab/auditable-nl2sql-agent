"""Deterministic, fail-closed intent rules for the fixed synthetic domain."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date


INTENT_POLICY_SCHEMA_VERSION = "intent-policy-v2"
SYNTHETIC_ORDER_DATE_START = date(2026, 1, 5)
SYNTHETIC_ORDER_DATE_END = date(2026, 3, 16)

_YEAR_PATTERN = re.compile(r"(?<!\d)(20\d{2})(?!\d)")
_REVENUE_TERMS = ("销售额", "营收", "收入", "gmv")
_GENERIC_REVENUE_FILLERS = (
    "请问",
    "帮我",
    "查询",
    "查一下",
    "一下",
    "的",
    "是",
    "有",
    "多少",
    "多少钱",
)
_AMBIGUOUS_BEST_SELLER_TERMS = ("最畅销", "最热销", "卖得最好")
_PRODUCT_TERMS = ("商品", "产品", "sku")
_BEST_SELLER_METRICS = (
    "销售额",
    "营收",
    "收入",
    "gmv",
    "销量",
    "数量",
    "件数",
)
_DISCOUNT_TERMS = ("折扣", "优惠")
_DISCOUNT_RANKING_TERMS = ("最大", "最高", "最多")
_DISCOUNT_METRICS = (
    "折扣率",
    "优惠率",
    "折扣金额",
    "优惠金额",
    "单件折扣",
    "单件优惠",
    "比例",
    "金额",
)
_REPEAT_PURCHASE_TERMS = ("复购",)
_VAGUE_ANALYSIS_TERMS = ("情况", "怎么样", "如何", "表现")
_REPEAT_PURCHASE_QUALIFIERS = (
    "复购率",
    "复购客户数",
    "复购人数",
    "复购订单数",
    "至少两笔",
    "至少2笔",
    "两次下单",
    "重复下单",
    "定义为",
    "口径",
)


@dataclass(frozen=True)
class IntentDecision:
    """A local semantic decision that prevents an unnecessary Provider call."""

    rule_id: str
    action: str
    reason: str


def _normalize(question: str) -> str:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be non-empty text")
    return "".join(character for character in question.casefold() if character.isalnum())


def _requests_unavailable_year(normalized: str) -> bool:
    supported_years = range(
        SYNTHETIC_ORDER_DATE_START.year,
        SYNTHETIC_ORDER_DATE_END.year + 1,
    )
    return any(int(year) not in supported_years for year in _YEAR_PATTERN.findall(normalized))


def _is_unscoped_revenue_question(normalized: str) -> bool:
    remainder = normalized
    matched = False
    for term in _REVENUE_TERMS:
        if term in remainder:
            matched = True
            remainder = remainder.replace(term, "")
    if not matched:
        return False
    for filler in _GENERIC_REVENUE_FILLERS:
        remainder = remainder.replace(filler, "")
    return not remainder


def _is_unqualified_best_seller_question(normalized: str) -> bool:
    return (
        any(term in normalized for term in _AMBIGUOUS_BEST_SELLER_TERMS)
        and any(term in normalized for term in _PRODUCT_TERMS)
        and not any(metric in normalized for metric in _BEST_SELLER_METRICS)
    )


def _is_unqualified_discount_ranking_question(normalized: str) -> bool:
    return (
        any(term in normalized for term in _DISCOUNT_TERMS)
        and any(term in normalized for term in _DISCOUNT_RANKING_TERMS)
        and any(term in normalized for term in _PRODUCT_TERMS)
        and not any(metric in normalized for metric in _DISCOUNT_METRICS)
    )


def _is_unqualified_repeat_purchase_question(normalized: str) -> bool:
    return (
        any(term in normalized for term in _REPEAT_PURCHASE_TERMS)
        and any(term in normalized for term in _VAGUE_ANALYSIS_TERMS)
        and not any(
            qualifier in normalized
            for qualifier in _REPEAT_PURCHASE_QUALIFIERS
        )
    )


def classify_question_intent(question: str) -> IntentDecision | None:
    """Return one bounded local decision, or ``None`` for normal Provider routing."""

    normalized = _normalize(question)
    if _requests_unavailable_year(normalized):
        return IntentDecision(
            rule_id="synthetic-order-year-outside-coverage",
            action="no_answer",
            reason=(
                "The requested year is outside the synthetic order-date coverage "
                f"{SYNTHETIC_ORDER_DATE_START.isoformat()} through "
                f"{SYNTHETIC_ORDER_DATE_END.isoformat()}."
            ),
        )
    if _is_unscoped_revenue_question(normalized):
        return IntentDecision(
            rule_id="revenue-scope-required",
            action="clarify",
            reason=(
                "Revenue requires a time range, grouping dimension, ranking scope, "
                "or an explicit all-data scope."
            ),
        )
    if _is_unqualified_best_seller_question(normalized):
        return IntentDecision(
            rule_id="best-seller-metric-required",
            action="clarify",
            reason=(
                "Best-selling product is ambiguous until revenue or quantity is "
                "selected as the ranking metric."
            ),
        )
    if _is_unqualified_discount_ranking_question(normalized):
        return IntentDecision(
            rule_id="discount-metric-required",
            action="clarify",
            reason=(
                "Maximum discount is ambiguous until amount or rate and the "
                "aggregation scope are specified."
            ),
        )
    if _is_unqualified_repeat_purchase_question(normalized):
        return IntentDecision(
            rule_id="repeat-purchase-definition-required",
            action="clarify",
            reason=(
                "Repeat purchase requires an explicit repeat definition or a "
                "specific metric such as customer count or repeat-purchase rate."
            ),
        )
    return None
