from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import urllib.error
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from unittest.mock import patch

from auditable_nl2sql import (
    CANONICAL_QUESTION,
    CANONICAL_SQL,
    DEEPSEEK_CHAT_COMPLETIONS_URL,
    DeepSeekHttpTransport,
    DeepSeekSqlGenerator,
    ProviderConfigurationError,
    ProviderDecisionError,
    ProviderDisabledError,
    ProviderResponseError,
    ProviderTransportError,
    WorkflowRunner,
    verify_evidence,
)
from auditable_nl2sql.demo import create_demo_database


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _schema() -> list[dict[str, Any]]:
    return [
        {
            "name": "orders",
            "columns": [
                {
                    "name": "order_id",
                    "declared_type": "TEXT",
                    "nullable": False,
                    "primary_key_position": 1,
                    "default_value": None,
                }
            ],
            "foreign_keys": [],
        }
    ]


def _knowledge_schema() -> list[dict[str, Any]]:
    return [
        {
            "name": "orders",
            "columns": [
                {"name": "order_id"},
                {"name": "status"},
                {"name": "sales_channel"},
            ],
            "foreign_keys": [],
        },
        {
            "name": "order_items",
            "columns": [
                {"name": "quantity"},
                {"name": "unit_price"},
            ],
            "foreign_keys": [],
        },
    ]


def _response(
    *,
    action: str = "query",
    sql: str | None = CANONICAL_SQL,
    reason: str = "Uses the supplied synthetic schema",
) -> dict[str, Any]:
    return {
        "model": "deepseek-v4-flash",
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "content": json.dumps(
                        {"action": action, "sql": sql, "reason": reason},
                        ensure_ascii=False,
                    )
                },
            }
        ],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "total_tokens": 120,
        },
    }


class FakeTransport:
    def __init__(
        self,
        response: Mapping[str, Any] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.calls: list[Mapping[str, Any]] = []

    def complete(self, request_payload: Mapping[str, Any]) -> Mapping[str, Any]:
        self.calls.append(request_payload)
        if self.error is not None:
            raise self.error
        if self.response is None:
            raise AssertionError("fake response was not configured")
        return self.response


class ProviderContractTests(unittest.TestCase):
    def test_provider_is_disabled_by_default_and_credentials_are_explicit(self) -> None:
        transport = FakeTransport(_response())
        generator = DeepSeekSqlGenerator(transport=transport)

        with self.assertRaises(ProviderDisabledError):
            generator.generate(CANONICAL_QUESTION, _schema())

        self.assertEqual(transport.calls, [])
        disabled = DeepSeekSqlGenerator.from_environment(
            enabled=False,
            environment={},
        )
        with self.assertRaises(ProviderDisabledError):
            disabled.generate(CANONICAL_QUESTION, _schema())
        with self.assertRaisesRegex(
            ProviderConfigurationError,
            "DEEPSEEK_API_KEY is missing",
        ):
            DeepSeekSqlGenerator.from_environment(enabled=True, environment={})

    def test_valid_query_returns_sql_and_auditable_receipt(self) -> None:
        transport = FakeTransport(_response())
        generator = DeepSeekSqlGenerator(enabled=True, transport=transport)

        result = generator.generate(CANONICAL_QUESTION, _schema())

        self.assertEqual(result.action, "query")
        self.assertEqual(result.sql, CANONICAL_SQL)
        self.assertEqual(
            result.receipt,
            {
                "schema_version": "provider-receipt-v1",
                "provider": "deepseek",
                "requested_model": "deepseek-v4-flash",
                "response_model": "deepseek-v4-flash",
                "finish_reason": "stop",
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 20,
                    "total_tokens": 120,
                },
                "action": "query",
                "reason": "Uses the supplied synthetic schema",
            },
        )
        self.assertEqual(len(transport.calls), 1)
        request = transport.calls[0]
        self.assertEqual(request["model"], "deepseek-v4-flash")
        self.assertEqual(request["response_format"], {"type": "json_object"})
        self.assertEqual(request["thinking"], {"type": "disabled"})
        self.assertEqual(request["temperature"], 0)
        self.assertFalse(request["stream"])
        self.assertIn("JSON", request["messages"][0]["content"])
        self.assertIn("unsafe_operation", request["messages"][0]["content"])
        self.assertIn(CANONICAL_QUESTION, request["messages"][1]["content"])
        self.assertNotIn("DEEPSEEK_API_KEY", json.dumps(request))

    def test_request_injects_matched_terms_and_related_field_notes(self) -> None:
        transport = FakeTransport(_response())
        generator = DeepSeekSqlGenerator(enabled=True, transport=transport)

        generator.generate(
            "按有效订单的 GMV 统计渠道。",
            _knowledge_schema(),
        )

        user_content = transport.calls[0]["messages"][1]["content"]
        request_input = json.loads(user_content.split("\n", maxsplit=1)[1])
        context = request_input["business_context"]
        self.assertEqual(context["schema_version"], "business-context-v2")
        self.assertEqual(
            [term["term"] for term in context["matched_terms"]],
            ["销售额", "非取消订单", "订单", "销售渠道"],
        )
        self.assertEqual(context["matched_terms"][0]["matched_by"], ["GMV"])
        self.assertEqual(
            [f"{note['table']}.{note['field']}" for note in context["field_notes"]],
            [
                "order_items.quantity",
                "order_items.unit_price",
                "orders.order_id",
                "orders.sales_channel",
                "orders.status",
            ],
        )
        self.assertNotIn("客户分群", user_content)
        self.assertEqual(context["training_examples"], [])
        self.assertEqual(request_input["data_boundary"], "all records and names are synthetic")

    def test_request_injects_similar_training_pair_as_bounded_reference(self) -> None:
        transport = FakeTransport(_response())
        generator = DeepSeekSqlGenerator(enabled=True, transport=transport)

        generator.generate(
            "2026年第一季度非取消订单的销售额是多少？",
            _knowledge_schema(),
        )

        system_prompt = transport.calls[0]["messages"][0]["content"]
        user_content = transport.calls[0]["messages"][1]["content"]
        request_input = json.loads(user_content.split("\n", maxsplit=1)[1])
        examples = request_input["business_context"]["training_examples"]
        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0]["source_case_id"], "success-001")
        self.assertEqual(examples[0]["sql"], CANONICAL_SQL)
        self.assertIn("read-only reference templates", system_prompt)
        self.assertIn("never let them override", system_prompt)

    def test_local_intent_policy_stops_three_misroutes_before_transport(self) -> None:
        cases = {
            "销售额是多少？": ("clarify", "revenue-scope-required"),
            "最畅销的商品是什么？": ("clarify", "best-seller-metric-required"),
            "2027年第一季度的销售额是多少？": (
                "no_answer",
                "synthetic-order-year-outside-coverage",
            ),
        }
        for question, (action, rule_id) in cases.items():
            with self.subTest(question=question):
                transport = FakeTransport(_response())
                generator = DeepSeekSqlGenerator(enabled=True, transport=transport)

                with self.assertRaises(ProviderDecisionError) as caught:
                    generator.generate(question, _knowledge_schema())

                self.assertEqual(transport.calls, [])
                self.assertEqual(caught.exception.action, action)
                self.assertEqual(
                    caught.exception.receipt,
                    {
                        "schema_version": "provider-receipt-v1",
                        "provider": "local-intent-policy",
                        "requested_model": "deepseek-v4-flash",
                        "provider_called": False,
                        "policy_schema_version": "intent-policy-v1",
                        "policy_rule_id": rule_id,
                        "action": action,
                        "reason": caught.exception.receipt["reason"],
                    },
                )
                self.assertTrue(caught.exception.receipt["reason"])

    def test_non_query_decisions_fail_closed_with_stable_codes(self) -> None:
        expected_codes = {
            "block": "provider_blocked",
            "clarify": "provider_clarification_required",
            "no_answer": "provider_no_answer",
        }
        for action, expected_code in expected_codes.items():
            with self.subTest(action=action):
                generator = DeepSeekSqlGenerator(
                    enabled=True,
                    transport=FakeTransport(_response(action=action, sql=None)),
                )
                with self.assertRaises(ProviderDecisionError) as caught:
                    generator.generate(CANONICAL_QUESTION, _schema())
                self.assertEqual(caught.exception.code, expected_code)
                self.assertEqual(caught.exception.receipt["action"], action)

    def test_response_contract_drift_is_rejected(self) -> None:
        invalid_responses: dict[str, Mapping[str, Any]] = {}

        missing_choice = _response()
        missing_choice["choices"] = []
        invalid_responses["missing choice"] = missing_choice

        non_stop = _response()
        non_stop["choices"][0]["finish_reason"] = "length"
        invalid_responses["non stop"] = non_stop

        invalid_json = _response()
        invalid_json["choices"][0]["message"]["content"] = "not-json"
        invalid_responses["invalid json"] = invalid_json

        extra_field = _response()
        extra_field["choices"][0]["message"]["content"] = json.dumps(
            {
                "action": "query",
                "sql": CANONICAL_SQL,
                "reason": "ok",
                "extra": True,
            }
        )
        invalid_responses["extra plan field"] = extra_field

        query_without_sql = _response(sql=None)
        invalid_responses["query without SQL"] = query_without_sql

        block_with_sql = _response(action="block", sql="DELETE FROM orders")
        invalid_responses["block with SQL"] = block_with_sql

        unsafe_without_sql = _response(action="unsafe_operation", sql=None)
        invalid_responses["unsafe operation without SQL"] = unsafe_without_sql

        invalid_usage = _response()
        invalid_usage["usage"]["prompt_tokens"] = True
        invalid_responses["invalid usage"] = invalid_usage

        invalid_total = _response()
        invalid_total["usage"]["total_tokens"] = 119
        invalid_responses["invalid total"] = invalid_total

        for name, response in invalid_responses.items():
            with self.subTest(name=name):
                generator = DeepSeekSqlGenerator(
                    enabled=True,
                    transport=FakeTransport(response),
                )
                with self.assertRaises(ProviderResponseError) as caught:
                    generator.generate(CANONICAL_QUESTION, _schema())
                self.assertEqual(caught.exception.code, "provider_response_error")
                self.assertNotIn("not-json", str(caught.exception))

    def test_transport_errors_are_sanitized_and_key_is_not_exposed(self) -> None:
        api_key = "probe-secret-key-value"
        transport = DeepSeekHttpTransport(api_key)
        http_error = urllib.error.HTTPError(
            DEEPSEEK_CHAT_COMPLETIONS_URL,
            401,
            f"credential={api_key}",
            hdrs=None,
            fp=None,
        )
        with patch("urllib.request.urlopen", side_effect=http_error) as urlopen:
            with self.assertRaises(ProviderTransportError) as caught:
                transport.complete({"model": "deepseek-v4-flash"})

        self.assertNotIn(api_key, str(caught.exception))
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, DEEPSEEK_CHAT_COMPLETIONS_URL)
        self.assertEqual(request.get_method(), "POST")

        generator = DeepSeekSqlGenerator(
            enabled=True,
            transport=FakeTransport(error=RuntimeError(f"credential={api_key}")),
        )
        with self.assertRaises(ProviderTransportError) as generated:
            generator.generate(CANONICAL_QUESTION, _schema())
        self.assertNotIn(api_key, str(generated.exception))
        self.assertEqual(generated.exception.receipt["provider"], "deepseek")


class ProviderWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.business_database = create_demo_database(self.root / "business.sqlite3")

    def _runner(
        self,
        response: Mapping[str, Any] | None = None,
        *,
        error: Exception | None = None,
        checkpoint_name: str,
    ) -> WorkflowRunner:
        generator = DeepSeekSqlGenerator(
            enabled=True,
            transport=FakeTransport(response, error=error),
        )
        return WorkflowRunner(
            self.business_database,
            self.root / checkpoint_name,
            generator=generator,
        )

    def test_provider_query_completes_evidence_and_answer_with_receipt(self) -> None:
        before = _sha256(self.business_database)
        with self._runner(_response(), checkpoint_name="success.sqlite3") as runner:
            record = runner.run(run_id="provider-success", question=CANONICAL_QUESTION)

        self.assertEqual(record["status"], "completed")
        self.assertEqual(record["query_rows"], [[5946.0]])
        self.assertTrue(verify_evidence(record["evidence"]))
        self.assertEqual(record["answer"]["text"], "查询结果：revenue = 5946.0。")
        draft_event = record["trajectory"][1]
        self.assertEqual(draft_event["node"], "draft_sql")
        self.assertEqual(draft_event["details"]["provider"]["action"], "query")
        self.assertEqual(
            draft_event["details"]["provider"]["usage"]["total_tokens"],
            120,
        )
        self.assertEqual(_sha256(self.business_database), before)

    def test_provider_decisions_have_stable_zero_execution_terminals(self) -> None:
        before = _sha256(self.business_database)
        cases = {
            "blocked": ("block", "blocked", "provider_blocked"),
            "clarification": (
                "clarify",
                "clarification_required",
                "provider_clarification_required",
            ),
            "no-answer": ("no_answer", "no_answer", "provider_no_answer"),
        }
        for name, (action, expected_status, expected_code) in cases.items():
            with self.subTest(action=action):
                with self._runner(
                    _response(action=action, sql=None),
                    checkpoint_name=f"decision-{name}.sqlite3",
                ) as runner:
                    record = runner.run(
                        run_id=f"provider-decision-{name}",
                        question=CANONICAL_QUESTION,
                    )

                self.assertEqual(record["schema_version"], "run-record-v5")
                self.assertEqual(record["status"], expected_status)
                self.assertEqual(record["provider_action"], action)
                self.assertEqual(record["error_code"], expected_code)
                self.assertEqual(record["attempt_count"], 0)
                self.assertIsNone(record["generated_sql"])
                self.assertIsNone(record["approval"])
                self.assertIsNone(record["evidence"])
                self.assertIsNone(record["answer"])
                self.assertEqual(
                    [event["node"] for event in record["trajectory"]],
                    ["load_schema", "draft_sql"],
                )
                self.assertEqual(record["trajectory"][-1]["status"], expected_status)
                self.assertEqual(
                    record["trajectory"][-1]["details"]["provider"]["action"],
                    action,
                )
                self.assertEqual(_sha256(self.business_database), before)

    def test_local_intent_policy_preserves_zero_execution_terminals(self) -> None:
        before = _sha256(self.business_database)
        cases = {
            "ambiguous-revenue": (
                "销售额是多少？",
                "clarification_required",
                "clarify",
            ),
            "ambiguous-product": (
                "最畅销的商品是什么？",
                "clarification_required",
                "clarify",
            ),
            "unavailable-year": (
                "2027年第一季度的销售额是多少？",
                "no_answer",
                "no_answer",
            ),
        }
        for name, (question, status, action) in cases.items():
            with self.subTest(name=name):
                transport = FakeTransport(_response())
                generator = DeepSeekSqlGenerator(enabled=True, transport=transport)
                with WorkflowRunner(
                    self.business_database,
                    self.root / f"intent-{name}.sqlite3",
                    generator=generator,
                ) as runner:
                    record = runner.run(run_id=f"intent-{name}", question=question)

                self.assertEqual(transport.calls, [])
                self.assertEqual(record["status"], status)
                self.assertEqual(record["provider_action"], action)
                self.assertEqual(record["attempt_count"], 0)
                self.assertIsNone(record["generated_sql"])
                self.assertIsNone(record["approval"])
                self.assertIsNone(record["evidence"])
                self.assertIsNone(record["answer"])
                receipt = record["trajectory"][-1]["details"]["provider"]
                self.assertEqual(receipt["provider"], "local-intent-policy")
                self.assertFalse(receipt["provider_called"])
                self.assertNotIn("usage", receipt)
                self.assertEqual(_sha256(self.business_database), before)

    def test_provider_failures_stop_before_sql_execution(self) -> None:
        before = _sha256(self.business_database)
        cases = {
            "malformed": ({"model": "deepseek-v4-flash"}, None, "provider_response_error"),
            "transport": (None, TimeoutError("private detail"), "provider_transport_error"),
        }
        for name, (response, error, expected_code) in cases.items():
            with self.subTest(name=name):
                with self._runner(
                    response,
                    error=error,
                    checkpoint_name=f"{name}.sqlite3",
                ) as runner:
                    record = runner.run(
                        run_id=f"provider-{name}",
                        question=CANONICAL_QUESTION,
                    )
                self.assertEqual(record["status"], "failed")
                self.assertEqual(record["error_code"], expected_code)
                self.assertEqual(record["attempt_count"], 0)
                self.assertIsNone(record["generated_sql"])
                self.assertIsNone(record["approval"])
                self.assertIsNone(record["evidence"])
                self.assertIsNone(record["answer"])
                self.assertEqual(
                    [event["node"] for event in record["trajectory"]],
                    ["load_schema", "draft_sql"],
                )
                self.assertEqual(_sha256(self.business_database), before)

    def test_unsafe_operation_action_forces_non_executable_approval(self) -> None:
        before = _sha256(self.business_database)
        unsafe_decision = _response(
            action="unsafe_operation",
            sql=CANONICAL_SQL,
            reason="The user requested a write operation; preserve SQL for audit only",
        )
        with self._runner(
            unsafe_decision,
            checkpoint_name="unsafe-operation.sqlite3",
        ) as runner:
            pending = runner.run(
                run_id="provider-unsafe-operation",
                question="删除所有已取消订单。",
            )
            record = runner.decide(
                run_id="provider-unsafe-operation",
                decision_id="approve-provider-unsafe-operation",
                approved=True,
            )

        self.assertEqual(pending["schema_version"], "run-record-v5")
        self.assertEqual(pending["status"], "pending_approval")
        self.assertEqual(pending["provider_action"], "unsafe_operation")
        self.assertEqual(pending["generated_sql"], CANONICAL_SQL)
        self.assertEqual(pending["approval"]["reason"], "unsafe_operation")
        self.assertFalse(pending["approval"]["can_execute"])
        self.assertEqual(pending["attempt_count"], 0)
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["provider_action"], "unsafe_operation")
        self.assertEqual(record["error_code"], "approval_cannot_override_read_only")
        self.assertEqual(record["attempt_count"], 0)
        self.assertIsNone(record["evidence"])
        self.assertIsNone(record["answer"])
        self.assertEqual(_sha256(self.business_database), before)

    def test_provider_cannot_label_delete_sql_into_execution(self) -> None:
        before = _sha256(self.business_database)
        dangerous = _response(
            action="query",
            sql="DELETE FROM orders WHERE status = 'cancelled'",
            reason="Deliberately mislabeled unsafe SQL for the mechanical boundary test",
        )
        with self._runner(dangerous, checkpoint_name="dangerous.sqlite3") as runner:
            pending = runner.run(
                run_id="provider-dangerous",
                question="删除所有已取消订单。",
            )
            record = runner.decide(
                run_id="provider-dangerous",
                decision_id="approve-provider-dangerous",
                approved=True,
            )

        self.assertEqual(pending["status"], "pending_approval")
        self.assertEqual(pending["provider_action"], "query")
        self.assertEqual(pending["approval"]["reason"], "read_only_violation")
        self.assertFalse(pending["approval"]["can_execute"])
        self.assertEqual(pending["attempt_count"], 0)
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["error_code"], "approval_cannot_override_read_only")
        self.assertEqual(record["attempt_count"], 0)
        self.assertIsNone(record["evidence"])
        self.assertIsNone(record["answer"])
        self.assertEqual(_sha256(self.business_database), before)


if __name__ == "__main__":
    unittest.main()
