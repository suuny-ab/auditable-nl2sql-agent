"""Deterministic draft business knowledge inferred from schema metadata only."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


SCHEMA_KNOWLEDGE_SCHEMA_VERSION = "schema-derived-knowledge-v2"
DESCRIPTION_SOURCE_NATIVE = "native"
DESCRIPTION_SOURCE_GENERATED = "generated"
DESCRIPTION_SOURCE_EMPTY = "empty"


class SchemaKnowledgeError(ValueError):
    """Raised when schema metadata cannot produce a safe deterministic draft."""


@dataclass(frozen=True)
class SchemaCandidateTerm:
    term: str
    synonyms: tuple[str, ...]
    definition: str
    related_fields: tuple[str, ...]


@dataclass(frozen=True)
class SchemaFieldDescription:
    table: str
    table_description: str
    table_description_source: str
    field: str
    description: str
    description_source: str

    @property
    def reference(self) -> str:
        return f"{self.table}.{self.field}"


@dataclass(frozen=True)
class SchemaDerivedKnowledge:
    schema_version: str
    candidate_terms: tuple[SchemaCandidateTerm, ...]
    field_descriptions: tuple[SchemaFieldDescription, ...]


@dataclass(frozen=True)
class _SchemaField:
    table: str
    table_roles: frozenset[str]
    name: str
    tokens: frozenset[str]
    declared_type: str
    primary_key_position: int
    foreign_key: tuple[str, str] | None
    native_table_description: str | None
    native_description: str | None

    @property
    def reference(self) -> str:
        return f"{self.table}.{self.name}"


_CUSTOMER_WORDS = frozenset({"buyer", "client", "customer", "purchaser"})
_PRODUCT_WORDS = frozenset(
    {"catalog", "goods", "item", "merchandise", "product", "sku"}
)
_ORDER_WORDS = frozenset(
    {"invoice", "order", "sale", "ticket", "transaction"}
)
_LINE_WORDS = frozenset({"detail", "item", "line", "row"})
_IDENTIFIER_WORDS = frozenset({"code", "id", "key", "no", "number", "sku"})


def _require_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaKnowledgeError(f"{label} must be non-empty text")
    return value.strip()


def _require_non_negative_integer(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise SchemaKnowledgeError(f"{label} must be a non-negative integer")
    return value


def _optional_description(value: object, label: str) -> str | None:
    if value is None:
        return None
    normalized = _require_text(value, label)
    if len(normalized) > 2_000:
        raise SchemaKnowledgeError(f"{label} is too long")
    return normalized


def merge_description_layers(
    native_description: str | None,
    generated_description: str | None,
) -> tuple[str | None, str]:
    """Resolve one description as native, generated, or explicitly empty."""

    native_description = _optional_description(
        native_description,
        "native description",
    )
    generated_description = _optional_description(
        generated_description,
        "generated description",
    )
    if native_description is not None:
        return native_description, DESCRIPTION_SOURCE_NATIVE
    if generated_description is not None:
        return generated_description, DESCRIPTION_SOURCE_GENERATED
    return None, DESCRIPTION_SOURCE_EMPTY


def _identifier_tokens(value: str) -> frozenset[str]:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value)
    return frozenset(
        token
        for token in re.split(r"[^a-z0-9]+", separated.casefold())
        if token
    )


def _table_roles(table_name: str) -> frozenset[str]:
    tokens = _identifier_tokens(table_name)
    roles: set[str] = set()
    if tokens & _CUSTOMER_WORDS:
        roles.add("customer")
    if tokens & _PRODUCT_WORDS:
        roles.add("product")
    if tokens & _ORDER_WORDS:
        roles.add("order")
    if tokens & _LINE_WORDS:
        roles.add("line")
    return frozenset(roles)


def _materialize_fields(
    schema_snapshot: list[dict[str, Any]],
) -> tuple[_SchemaField, ...]:
    if not isinstance(schema_snapshot, list) or not schema_snapshot:
        raise SchemaKnowledgeError("schema snapshot must contain tables")

    table_names: set[str] = set()
    raw_tables: list[
        tuple[str, frozenset[str], str | None, Mapping[str, Any]]
    ] = []
    for table_index, raw_table in enumerate(schema_snapshot):
        if not isinstance(raw_table, Mapping):
            raise SchemaKnowledgeError(f"table[{table_index}] must be an object")
        table_name = _require_text(raw_table.get("name"), f"table[{table_index}].name")
        if table_name in table_names:
            raise SchemaKnowledgeError(f"duplicate schema table: {table_name}")
        table_names.add(table_name)
        table_description = _optional_description(
            raw_table.get("description"),
            f"table[{table_index}].description",
        )
        raw_tables.append(
            (table_name, _table_roles(table_name), table_description, raw_table)
        )

    fields: list[_SchemaField] = []
    field_references: set[str] = set()
    foreign_keys_by_reference: dict[str, tuple[str, str]] = {}
    for table_name, _roles, _table_description_value, raw_table in raw_tables:
        raw_foreign_keys = raw_table.get("foreign_keys", [])
        if not isinstance(raw_foreign_keys, list):
            raise SchemaKnowledgeError(f"{table_name}.foreign_keys must be a list")
        for key_index, raw_key in enumerate(raw_foreign_keys):
            if not isinstance(raw_key, Mapping):
                raise SchemaKnowledgeError(
                    f"{table_name}.foreign_keys[{key_index}] must be an object"
                )
            column = _require_text(
                raw_key.get("column"),
                f"{table_name}.foreign_keys[{key_index}].column",
            )
            referenced_table = _require_text(
                raw_key.get("referenced_table"),
                f"{table_name}.foreign_keys[{key_index}].referenced_table",
            )
            referenced_column = _require_text(
                raw_key.get("referenced_column"),
                f"{table_name}.foreign_keys[{key_index}].referenced_column",
            )
            reference = f"{table_name}.{column}"
            if reference in foreign_keys_by_reference:
                raise SchemaKnowledgeError(f"duplicate foreign key: {reference}")
            foreign_keys_by_reference[reference] = (
                referenced_table,
                referenced_column,
            )

    for table_name, roles, table_description, raw_table in raw_tables:
        raw_columns = raw_table.get("columns")
        if not isinstance(raw_columns, list) or not raw_columns:
            raise SchemaKnowledgeError(f"{table_name}.columns must be non-empty")
        for column_index, raw_column in enumerate(raw_columns):
            if not isinstance(raw_column, Mapping):
                raise SchemaKnowledgeError(
                    f"{table_name}.columns[{column_index}] must be an object"
                )
            column_name = _require_text(
                raw_column.get("name"),
                f"{table_name}.columns[{column_index}].name",
            )
            reference = f"{table_name}.{column_name}"
            if reference in field_references:
                raise SchemaKnowledgeError(f"duplicate schema field: {reference}")
            field_references.add(reference)
            declared_type = raw_column.get("declared_type", "")
            if declared_type is None:
                declared_type = ""
            if not isinstance(declared_type, str):
                raise SchemaKnowledgeError(f"{reference}.declared_type must be text")
            primary_key_position = _require_non_negative_integer(
                raw_column.get("primary_key_position", 0),
                f"{reference}.primary_key_position",
            )
            column_description = _optional_description(
                raw_column.get("description"),
                f"{reference}.description",
            )
            fields.append(
                _SchemaField(
                    table=table_name,
                    table_roles=roles,
                    name=column_name,
                    tokens=_identifier_tokens(column_name),
                    declared_type=declared_type.strip().upper(),
                    primary_key_position=primary_key_position,
                    foreign_key=foreign_keys_by_reference.get(reference),
                    native_table_description=table_description,
                    native_description=column_description,
                )
            )

    for source, target in foreign_keys_by_reference.items():
        if source not in field_references:
            raise SchemaKnowledgeError(f"foreign key source is not a field: {source}")
        target_reference = f"{target[0]}.{target[1]}"
        if target_reference not in field_references:
            raise SchemaKnowledgeError(
                f"foreign key target is not a field: {target_reference}"
            )
    return tuple(fields)


def _field_roles(
    field: _SchemaField,
    table_roles_by_name: Mapping[str, frozenset[str]],
) -> frozenset[str]:
    tokens = field.tokens
    roles: set[str] = set()
    target_roles = (
        table_roles_by_name.get(field.foreign_key[0], frozenset())
        if field.foreign_key is not None
        else frozenset()
    )
    identifier = bool(tokens & _IDENTIFIER_WORDS) or field.primary_key_position > 0

    if tokens & {"date", "day", "occurred", "timestamp", "time"}:
        roles.add("order_date")
    if tokens & {"state", "status"}:
        roles.add("order_status")
    if tokens & {"channel", "source"}:
        roles.add("sales_channel")
    if tokens & {"qty", "quantity", "units"}:
        roles.add("quantity")
    if (
        "price" in tokens and tokens & {"actual", "paid", "sale", "unit"}
    ) or {"paid", "unit"} <= tokens:
        roles.add("unit_price")
    if "price" in tokens and tokens & {"catalog", "list", "msrp"}:
        roles.add("list_price")
    if tokens & {"region", "territory"} or (
        "customer" in field.table_roles and bool(tokens & {"area", "market"})
    ):
        roles.add("region")
    if "customer" in field.table_roles and tokens & {"class", "segment", "tier"}:
        roles.add("customer_segment")
    if "product" in field.table_roles and tokens & {"category", "department", "family"}:
        roles.add("product_category")

    if (tokens & _CUSTOMER_WORDS and identifier) or "customer" in target_roles:
        roles.add("customer_id")
    if (tokens & _PRODUCT_WORDS and identifier) or "product" in target_roles:
        roles.add("product_id")
    if tokens & _ORDER_WORDS and identifier:
        roles.add("order_id")
    elif "order" in field.table_roles and identifier and not roles & {
        "customer_id",
        "product_id",
    }:
        roles.add("order_id")

    if tokens & {"label", "name", "title"}:
        if "customer" in field.table_roles:
            roles.add("customer_name")
        if "product" in field.table_roles:
            roles.add("product_name")
    return frozenset(roles)


def _table_description(table_name: str, roles: frozenset[str]) -> str:
    if roles >= {"order", "line"}:
        return f"由 schema 名称推断的合成订单/交易明细表 {table_name}。"
    if "customer" in roles:
        return f"由 schema 名称推断的合成客户或买方主数据表 {table_name}。"
    if "product" in roles:
        return f"由 schema 名称推断的合成商品主数据表 {table_name}。"
    if "order" in roles:
        return f"由 schema 名称推断的合成订单或交易表 {table_name}。"
    return f"schema 元数据中的合成业务表 {table_name}。"


def _field_description(
    field: _SchemaField,
    roles: frozenset[str],
) -> str:
    role_descriptions = {
        "order_id": "订单或交易的标识；计数订单时通常应去重。",
        "customer_id": "客户或买方标识。",
        "customer_name": "客户或买方的展示名称。",
        "product_id": "商品标识。",
        "product_name": "商品展示名称。",
        "order_date": "订单或交易发生日期/时间。",
        "order_status": "订单或交易状态编码；用于识别取消等状态，实际存储值不能由字段名臆造。",
        "sales_channel": "销售渠道或来源编码；用于按渠道筛选或分组。",
        "quantity": "订单行的购买数量；与实际成交单价相乘可得到行金额。",
        "unit_price": "订单行的实际成交单价。",
        "list_price": "商品目录标价；不等于订单行实际成交单价。",
        "region": "客户或买方所属地区/市场区域。",
        "customer_segment": "客户或买方的业务分群/类别。",
        "product_category": "商品所属品类/部门。",
    }
    ordered_roles = (
        "order_id",
        "customer_id",
        "customer_name",
        "product_id",
        "product_name",
        "order_date",
        "order_status",
        "sales_channel",
        "quantity",
        "unit_price",
        "list_price",
        "region",
        "customer_segment",
        "product_category",
    )
    parts = [role_descriptions[role] for role in ordered_roles if role in roles]
    if "cents" in field.tokens and roles & {"unit_price", "list_price"}:
        parts.append("字段以整数分保存金额，换算元时除以 100。")
    if field.foreign_key is not None:
        parts.append(
            f"外键关联 {field.foreign_key[0]}.{field.foreign_key[1]}。"
        )
    if not parts:
        type_note = f"，声明类型为 {field.declared_type}" if field.declared_type else ""
        parts.append(f"由 schema 元数据生成的字段备注初稿{type_note}。")
    return "".join(parts)


def _candidate_terms(
    fields: tuple[_SchemaField, ...],
    roles_by_reference: Mapping[str, frozenset[str]],
) -> tuple[SchemaCandidateTerm, ...]:
    references_by_role: dict[str, list[str]] = {}
    for field in fields:
        for role in roles_by_reference[field.reference]:
            references_by_role.setdefault(role, []).append(field.reference)
    for references in references_by_role.values():
        references.sort()

    def refs(*roles: str) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    reference
                    for role in roles
                    for reference in references_by_role.get(role, [])
                }
            )
        )

    def add(
        output: list[SchemaCandidateTerm],
        term: str,
        synonyms: tuple[str, ...],
        definition: str,
        related_fields: tuple[str, ...],
        *,
        required_roles: tuple[str, ...],
    ) -> None:
        if all(references_by_role.get(role) for role in required_roles):
            output.append(
                SchemaCandidateTerm(
                    term=term,
                    synonyms=synonyms,
                    definition=definition,
                    related_fields=related_fields,
                )
            )

    amount_scale = (
        "；金额字段以整数分保存，汇总后除以 100 换算元"
        if any(
            "cents" in field.tokens
            for field in fields
            if "unit_price" in roles_by_reference[field.reference]
        )
        else ""
    )
    terms: list[SchemaCandidateTerm] = []
    add(
        terms,
        "销售额",
        ("营收", "收入", "GMV"),
        "候选口径为订单行数量乘以实际成交单价后求和"
        f"{amount_scale}；是否排除取消记录由状态字段决定。",
        refs("quantity", "unit_price", "order_id", "order_status"),
        required_roles=("quantity", "unit_price"),
    )
    add(
        terms,
        "非取消订单",
        ("有效订单", "剔除取消订单"),
        "候选口径为通过订单/交易状态字段排除取消记录；实际状态存储值必须以可用元数据为准。",
        refs("order_id", "order_status"),
        required_roles=("order_status",),
    )
    add(
        terms,
        "订单",
        ("销售订单", "订单笔数"),
        "候选订单标识来自 schema 推断的订单/交易编号；明细表中统计订单数应对该标识去重。",
        refs("order_id", "order_date", "order_status", "customer_id"),
        required_roles=("order_id",),
    )
    add(
        terms,
        "订单商品明细",
        ("订单明细", "行项目", "订单行", "行金额"),
        "候选订单行由订单标识与商品标识关联；行金额由数量乘实际成交单价得到。",
        refs("order_id", "product_id", "quantity", "unit_price"),
        required_roles=("order_id", "quantity", "unit_price"),
    )
    add(
        terms,
        "商品",
        ("产品", "SKU"),
        "候选商品主数据由商品标识与展示名称描述，目录标价不等于实际成交单价。",
        refs("product_id", "product_name", "product_category", "list_price"),
        required_roles=("product_id",),
    )
    add(
        terms,
        "销售渠道",
        ("渠道", "下单渠道"),
        "候选销售渠道来自 schema 推断的渠道/来源字段。",
        refs("sales_channel", "order_id"),
        required_roles=("sales_channel",),
    )
    add(
        terms,
        "客户",
        ("买家", "购买客户"),
        "候选客户由客户/买方标识和展示名称描述，并通过外键与订单或交易关联。",
        refs("customer_id", "customer_name"),
        required_roles=("customer_id",),
    )
    add(
        terms,
        "区域",
        ("地区", "大区"),
        "候选区域来自客户/买方的地区或市场区域字段。",
        refs("region", "customer_id"),
        required_roles=("region",),
    )
    add(
        terms,
        "客户分群",
        ("客户类型", "客群"),
        "候选客户分群来自客户/买方的分类、分群或层级字段。",
        refs("customer_segment", "customer_id"),
        required_roles=("customer_segment",),
    )
    add(
        terms,
        "客单价",
        ("平均订单金额", "AOV"),
        "候选口径为非取消销售额除以去重订单数"
        f"{amount_scale}。",
        refs("quantity", "unit_price", "order_id", "order_status"),
        required_roles=("quantity", "unit_price", "order_id"),
    )
    add(
        terms,
        "成交单价",
        ("实际成交价", "成交价", "最低成交单价", "优惠"),
        "候选实际成交价来自订单行单价字段；与目录标价比较可计算单件优惠。",
        refs("unit_price", "list_price", "product_id", "order_status"),
        required_roles=("unit_price",),
    )
    add(
        terms,
        "标价",
        ("目录价", "目录标价", "catalog price"),
        "候选标价来自商品目录价格字段，不代表实际成交单价。",
        refs("list_price", "product_id", "product_name"),
        required_roles=("list_price",),
    )
    add(
        terms,
        "数量",
        ("购买数量", "件数", "quantity", "units"),
        "候选数量来自订单行数量字段；与实际成交单价相乘可计算行金额。",
        refs("quantity", "unit_price", "order_id", "product_id"),
        required_roles=("quantity",),
    )
    return tuple(terms)


def build_schema_knowledge(
    schema_snapshot: list[dict[str, Any]],
) -> SchemaDerivedKnowledge:
    """Generate deterministic draft field notes and candidate terms without an LLM."""

    fields = _materialize_fields(schema_snapshot)
    table_roles_by_name = {field.table: field.table_roles for field in fields}
    roles_by_reference = {
        field.reference: _field_roles(field, table_roles_by_name)
        for field in fields
    }
    descriptions: list[SchemaFieldDescription] = []
    for field in fields:
        table_description, table_source = merge_description_layers(
            field.native_table_description,
            _table_description(field.table, field.table_roles),
        )
        description, description_source = merge_description_layers(
            field.native_description,
            _field_description(field, roles_by_reference[field.reference]),
        )
        if table_description is None or description is None:
            raise SchemaKnowledgeError("generated schema descriptions must not be empty")
        descriptions.append(
            SchemaFieldDescription(
                table=field.table,
                table_description=table_description,
                table_description_source=table_source,
                field=field.name,
                description=description,
                description_source=description_source,
            )
        )
    return SchemaDerivedKnowledge(
        schema_version=SCHEMA_KNOWLEDGE_SCHEMA_VERSION,
        candidate_terms=_candidate_terms(fields, roles_by_reference),
        field_descriptions=tuple(descriptions),
    )
