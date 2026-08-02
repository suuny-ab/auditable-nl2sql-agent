"""Versioned synthetic business knowledge for bounded SQL-generation context."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from typing import Any


BUSINESS_CONTEXT_SCHEMA_VERSION = "business-context-v1"
BUSINESS_TERMS_SCHEMA_VERSION = "business-terms-v1"
FIELD_DESCRIPTIONS_SCHEMA_VERSION = "field-descriptions-v1"
_TERM_KEYS = {"term", "synonyms", "definition", "related_fields"}
_TABLE_KEYS = {"name", "description", "fields"}
_FIELD_KEYS = {"name", "description"}


class BusinessKnowledgeError(ValueError):
    """Raised when packaged business knowledge violates its strict contract."""


@dataclass(frozen=True)
class BusinessTerm:
    term: str
    synonyms: tuple[str, ...]
    definition: str
    related_fields: tuple[str, ...]


@dataclass(frozen=True)
class FieldDescription:
    table: str
    table_description: str
    field: str
    description: str

    @property
    def reference(self) -> str:
        return f"{self.table}.{self.field}"


@dataclass(frozen=True)
class BusinessKnowledge:
    terms: tuple[BusinessTerm, ...]
    field_descriptions: tuple[FieldDescription, ...]


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant is not allowed: {value}")


def _read_resource(name: str) -> Mapping[str, Any]:
    resource = resources.files("auditable_nl2sql").joinpath("data").joinpath(name)
    try:
        payload = json.loads(
            resource.read_text(encoding="utf-8"),
            parse_constant=_reject_json_constant,
        )
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BusinessKnowledgeError(f"Could not load packaged knowledge: {name}") from exc
    except ValueError as exc:
        raise BusinessKnowledgeError(f"Knowledge is not strict JSON: {name}") from exc
    if not isinstance(payload, Mapping):
        raise BusinessKnowledgeError(f"Knowledge root must be an object: {name}")
    return payload


def _require_keys(value: object, expected: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise BusinessKnowledgeError(f"{label} must have exactly {sorted(expected)}")
    return value


def _require_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BusinessKnowledgeError(f"{label} must be non-empty text")
    return value.strip()


def _require_text_list(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise BusinessKnowledgeError(f"{label} must be a non-empty list")
    items = tuple(_require_text(item, label) for item in value)
    if len(set(items)) != len(items):
        raise BusinessKnowledgeError(f"{label} must not contain duplicates")
    return items


@lru_cache(maxsize=1)
def load_business_knowledge() -> BusinessKnowledge:
    """Load and strictly validate the two immutable packaged knowledge files."""

    term_payload = _require_keys(
        _read_resource("business_terms.json"),
        {"schema_version", "terms"},
        "business terms root",
    )
    if term_payload["schema_version"] != BUSINESS_TERMS_SCHEMA_VERSION:
        raise BusinessKnowledgeError("Unsupported business terms schema version")
    raw_terms = term_payload["terms"]
    if not isinstance(raw_terms, list) or len(raw_terms) != 10:
        raise BusinessKnowledgeError("Business terms must contain exactly 10 entries")

    terms: list[BusinessTerm] = []
    aliases: set[str] = set()
    for index, raw_term in enumerate(raw_terms):
        term_data = _require_keys(raw_term, _TERM_KEYS, f"term[{index}]")
        term = _require_text(term_data["term"], f"term[{index}].term")
        synonyms = _require_text_list(
            term_data["synonyms"],
            f"term[{index}].synonyms",
        )
        definition = _require_text(
            term_data["definition"],
            f"term[{index}].definition",
        )
        related_fields = _require_text_list(
            term_data["related_fields"],
            f"term[{index}].related_fields",
        )
        for alias in (term, *synonyms):
            normalized = alias.casefold()
            if normalized in aliases:
                raise BusinessKnowledgeError(f"Duplicate business term alias: {alias}")
            aliases.add(normalized)
        terms.append(
            BusinessTerm(
                term=term,
                synonyms=synonyms,
                definition=definition,
                related_fields=related_fields,
            )
        )

    field_payload = _require_keys(
        _read_resource("field_descriptions.json"),
        {"schema_version", "tables"},
        "field descriptions root",
    )
    if field_payload["schema_version"] != FIELD_DESCRIPTIONS_SCHEMA_VERSION:
        raise BusinessKnowledgeError("Unsupported field descriptions schema version")
    raw_tables = field_payload["tables"]
    if not isinstance(raw_tables, list) or not raw_tables:
        raise BusinessKnowledgeError("Field descriptions must contain tables")

    descriptions: list[FieldDescription] = []
    table_names: set[str] = set()
    field_references: set[str] = set()
    for table_index, raw_table in enumerate(raw_tables):
        table_data = _require_keys(raw_table, _TABLE_KEYS, f"table[{table_index}]")
        table_name = _require_text(table_data["name"], f"table[{table_index}].name")
        if table_name in table_names:
            raise BusinessKnowledgeError(f"Duplicate table description: {table_name}")
        table_names.add(table_name)
        table_description = _require_text(
            table_data["description"],
            f"table[{table_index}].description",
        )
        raw_fields = table_data["fields"]
        if not isinstance(raw_fields, list) or not raw_fields:
            raise BusinessKnowledgeError(f"{table_name}.fields must be non-empty")
        for field_index, raw_field in enumerate(raw_fields):
            field_data = _require_keys(
                raw_field,
                _FIELD_KEYS,
                f"{table_name}.fields[{field_index}]",
            )
            field_name = _require_text(
                field_data["name"],
                f"{table_name}.fields[{field_index}].name",
            )
            description = FieldDescription(
                table=table_name,
                table_description=table_description,
                field=field_name,
                description=_require_text(
                    field_data["description"],
                    f"{table_name}.{field_name}.description",
                ),
            )
            if description.reference in field_references:
                raise BusinessKnowledgeError(
                    f"Duplicate field description: {description.reference}"
                )
            field_references.add(description.reference)
            descriptions.append(description)

    unknown_references = sorted(
        {
            reference
            for term in terms
            for reference in term.related_fields
            if reference not in field_references
        }
    )
    if unknown_references:
        raise BusinessKnowledgeError(
            f"Business terms reference unknown fields: {unknown_references}"
        )
    return BusinessKnowledge(
        terms=tuple(terms),
        field_descriptions=tuple(descriptions),
    )


def _available_field_references(schema_snapshot: list[dict[str, Any]]) -> set[str]:
    available: set[str] = set()
    for table in schema_snapshot:
        if not isinstance(table, Mapping):
            raise BusinessKnowledgeError("Schema table must be an object")
        table_name = _require_text(table.get("name"), "schema table name")
        columns = table.get("columns")
        if not isinstance(columns, list):
            raise BusinessKnowledgeError(f"{table_name}.columns must be a list")
        for column in columns:
            if not isinstance(column, Mapping):
                raise BusinessKnowledgeError("Schema column must be an object")
            column_name = _require_text(column.get("name"), "schema column name")
            available.add(f"{table_name}.{column_name}")
    return available


def build_business_context(
    question: str,
    schema_snapshot: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return only question-matched terms and their available field notes."""

    normalized_question = _require_text(question, "question").casefold()
    knowledge = load_business_knowledge()
    available_fields = _available_field_references(schema_snapshot)
    matched_terms: list[dict[str, Any]] = []
    related_fields: set[str] = set()

    for term in knowledge.terms:
        matched_by = [
            alias
            for alias in (term.term, *term.synonyms)
            if alias.casefold() in normalized_question
        ]
        if not matched_by:
            continue
        matched_terms.append(
            {
                "term": term.term,
                "matched_by": matched_by,
                "definition": term.definition,
            }
        )
        related_fields.update(term.related_fields)

    notes_by_reference = {
        description.reference: description
        for description in knowledge.field_descriptions
    }
    field_notes = []
    for reference in sorted(related_fields & available_fields):
        description = notes_by_reference[reference]
        field_notes.append(
            {
                "table": description.table,
                "field": description.field,
                "description": description.description,
            }
        )

    return {
        "schema_version": BUSINESS_CONTEXT_SCHEMA_VERSION,
        "matched_terms": matched_terms,
        "field_notes": field_notes,
    }
