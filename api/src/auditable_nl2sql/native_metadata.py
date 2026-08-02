"""Conservative extraction of adjacent comments from SQLite CREATE TABLE SQL."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class NativeCommentMetadata:
    """Native descriptions recovered from one SQLite CREATE TABLE statement."""

    table_description: str | None
    column_descriptions: dict[str, str]


@dataclass(frozen=True)
class _Token:
    kind: str
    start: int
    end: int
    text: str


def _tokens(sql: str) -> tuple[_Token, ...]:
    output: list[_Token] = []
    index = 0
    while index < len(sql):
        character = sql[index]
        if character.isspace():
            index += 1
            continue
        if sql.startswith("--", index):
            end = sql.find("\n", index + 2)
            if end < 0:
                end = len(sql)
            output.append(_Token("comment", index, end, sql[index:end]))
            index = end
            continue
        if sql.startswith("/*", index):
            marker = sql.find("*/", index + 2)
            end = len(sql) if marker < 0 else marker + 2
            output.append(_Token("comment", index, end, sql[index:end]))
            index = end
            continue
        if character in "'\"`":
            quote = character
            end = index + 1
            while end < len(sql):
                if sql[end] == quote:
                    if end + 1 < len(sql) and sql[end + 1] == quote:
                        end += 2
                        continue
                    end += 1
                    break
                end += 1
            output.append(
                _Token(
                    "string" if quote == "'" else "identifier",
                    index,
                    end,
                    sql[index:end],
                )
            )
            index = end
            continue
        if character == "[":
            end = index + 1
            while end < len(sql):
                if sql[end] == "]":
                    if end + 1 < len(sql) and sql[end + 1] == "]":
                        end += 2
                        continue
                    end += 1
                    break
                end += 1
            output.append(_Token("identifier", index, end, sql[index:end]))
            index = end
            continue
        if character in "(),.;":
            output.append(_Token("punctuation", index, index + 1, character))
            index += 1
            continue

        end = index + 1
        while end < len(sql):
            if sql[end].isspace() or sql[end] in "'\"`[](),.;":
                break
            if sql.startswith("--", end) or sql.startswith("/*", end):
                break
            end += 1
        output.append(_Token("word", index, end, sql[index:end]))
        index = end
    return tuple(output)


def _identifier(token: _Token) -> str | None:
    if token.kind == "word":
        return token.text
    if token.kind != "identifier" or len(token.text) < 2:
        return None
    if token.text[0] == "[":
        return token.text[1:-1].replace("]]", "]")
    quote = token.text[0]
    return token.text[1:-1].replace(quote * 2, quote)


def _normalize_comments(comments: list[_Token]) -> str | None:
    parts: list[str] = []
    for comment in comments:
        text = comment.text
        if text.startswith("--"):
            text = text[2:]
        elif text.startswith("/*"):
            text = text[2:-2] if text.endswith("*/") else text[2:]
        lines = [re.sub(r"^\s*\*?\s?", "", line).strip() for line in text.splitlines()]
        normalized = " ".join(line for line in lines if line)
        if normalized:
            parts.append(normalized)
    combined = " ".join(parts).strip()
    return combined or None


def _body_segments(
    tokens: tuple[_Token, ...],
    opening_index: int,
) -> tuple[tuple[_Token, ...], ...]:
    depth = 1
    start = opening_index + 1
    segments: list[tuple[_Token, ...]] = []
    for index in range(opening_index + 1, len(tokens)):
        token = tokens[index]
        if token.kind != "punctuation":
            continue
        if token.text == "(":
            depth += 1
        elif token.text == ")":
            depth -= 1
            if depth == 0:
                segments.append(tokens[start:index])
                return tuple(segments)
        elif token.text == "," and depth == 1:
            segments.append(tokens[start:index])
            start = index + 1
    return ()


def extract_sqlite_ddl_comments(
    create_sql: str | None,
    *,
    table_name: str,
    column_names: tuple[str, ...],
) -> NativeCommentMetadata:
    """Extract only comments adjacent to the table or a real column identifier.

    SQLite exposes the original CREATE statement through ``sqlite_schema.sql`` but
    has no dedicated description field. Unknown or ambiguous syntax therefore
    returns no description instead of guessing from comments elsewhere in the DDL.
    """

    if not create_sql:
        return NativeCommentMetadata(None, {})
    tokens = _tokens(create_sql)
    opening_index = next(
        (
            index
            for index, token in enumerate(tokens)
            if token.kind == "punctuation" and token.text == "("
        ),
        None,
    )
    if opening_index is None:
        return NativeCommentMetadata(None, {})

    name_index = next(
        (
            index
            for index in range(opening_index - 1, -1, -1)
            if tokens[index].kind != "comment"
        ),
        None,
    )
    table_description = None
    if name_index is not None and _identifier(tokens[name_index]) == table_name:
        between = list(tokens[name_index + 1 : opening_index])
        if all(token.kind == "comment" for token in between):
            table_description = _normalize_comments(between)

    real_columns = set(column_names)
    descriptions: dict[str, str] = {}
    for segment in _body_segments(tokens, opening_index):
        identifier_index = next(
            (
                index
                for index, token in enumerate(segment)
                if token.kind != "comment"
            ),
            None,
        )
        if identifier_index is None:
            continue
        column_name = _identifier(segment[identifier_index])
        if column_name not in real_columns:
            continue
        adjacent_comments = [
            token for token in segment[:identifier_index] if token.kind == "comment"
        ]
        for token in segment[identifier_index + 1 :]:
            if token.kind != "comment":
                break
            adjacent_comments.append(token)
        description = _normalize_comments(adjacent_comments)
        if description is not None:
            descriptions[column_name] = description
    return NativeCommentMetadata(table_description, descriptions)
