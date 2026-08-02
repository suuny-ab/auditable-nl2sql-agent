from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from auditable_nl2sql import (
    SYNTHETIC_ORDER_DATE_END,
    SYNTHETIC_ORDER_DATE_START,
    classify_question_intent,
    execute_read_only,
)
from auditable_nl2sql.demo import create_demo_database


class IntentPolicyTests(unittest.TestCase):
    def test_order_date_policy_matches_the_synthetic_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = create_demo_database(Path(directory) / "business.sqlite3")
            result = execute_read_only(
                database,
                "SELECT MIN(order_date), MAX(order_date) FROM orders",
            )

        self.assertEqual(
            result.rows,
            ((
                SYNTHETIC_ORDER_DATE_START.isoformat(),
                SYNTHETIC_ORDER_DATE_END.isoformat(),
            ),),
        )

    def test_unscoped_revenue_requires_clarification(self) -> None:
        decision = classify_question_intent("销售额是多少？")

        self.assertIsNotNone(decision)
        self.assertEqual(decision.action, "clarify")
        self.assertEqual(decision.rule_id, "revenue-scope-required")

    def test_best_seller_without_metric_requires_clarification(self) -> None:
        decision = classify_question_intent("最畅销的商品是什么？")

        self.assertIsNotNone(decision)
        self.assertEqual(decision.action, "clarify")
        self.assertEqual(decision.rule_id, "best-seller-metric-required")

    def test_year_outside_synthetic_coverage_has_no_answer(self) -> None:
        decision = classify_question_intent("2027年第一季度的销售额是多少？")

        self.assertIsNotNone(decision)
        self.assertEqual(decision.action, "no_answer")
        self.assertEqual(decision.rule_id, "synthetic-order-year-outside-coverage")

    def test_discount_ranking_without_metric_requires_clarification(self) -> None:
        decision = classify_question_intent(
            "2026年第一季度非取消订单中，折扣最大的商品是什么？"
        )

        self.assertIsNotNone(decision)
        self.assertEqual(decision.action, "clarify")
        self.assertEqual(decision.rule_id, "discount-metric-required")
        self.assertIsNone(
            classify_question_intent(
                "2026年第一季度非取消订单中，单件优惠金额最大的商品是什么？"
            )
        )
        self.assertIsNone(
            classify_question_intent(
                "2026年第一季度非取消订单中，折扣率最高的商品是什么？"
            )
        )

    def test_repeat_purchase_without_definition_requires_clarification(self) -> None:
        decision = classify_question_intent("2026年3月客户复购情况怎么样？")

        self.assertIsNotNone(decision)
        self.assertEqual(decision.action, "clarify")
        self.assertEqual(decision.rule_id, "repeat-purchase-definition-required")
        self.assertIsNone(classify_question_intent("2026年3月客户复购率是多少？"))
        self.assertIsNone(
            classify_question_intent(
                "把同月下单至少两笔定义为复购，2026年3月复购客户数是多少？"
            )
        )

    def test_scoped_success_questions_continue_to_provider(self) -> None:
        questions = (
            "2026年第一季度非取消订单销售额是多少？",
            "非取消订单按销售渠道统计销售额，结果从高到低是什么？",
            "按非取消订单销售额计算，销售额最高的商品是什么？",
            "非取消订单按客户统计销售额，排名是什么？",
            "按销售数量计算，最畅销的商品是什么？",
        )

        for question in questions:
            with self.subTest(question=question):
                self.assertIsNone(classify_question_intent(question))


if __name__ == "__main__":
    unittest.main()
