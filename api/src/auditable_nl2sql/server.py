"""Independent process entry point for the read-only API."""

from __future__ import annotations

import argparse
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from .api import create_app
from .workflow import WorkflowRunReader


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def _existing_database(path: str | Path, *, label: str) -> Path:
    resolved = Path(path).resolve()
    if not resolved.is_file():
        raise ValueError(f"{label} database must already exist: {resolved}")
    return resolved


def create_runtime_app(
    business_database: str | Path,
    checkpoint_database: str | Path,
) -> FastAPI:
    """Bind the existing read-only reader to the ASGI application lifespan."""
    business_path = _existing_database(
        business_database,
        label="business",
    )
    checkpoint_path = _existing_database(
        checkpoint_database,
        label="checkpoint",
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        with WorkflowRunReader(business_path, checkpoint_path) as run_reader:
            app.state.run_reader = run_reader
            yield

    return create_app(lifespan=lifespan)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Start the auditable NL2SQL read-only API.",
    )
    parser.add_argument(
        "--business-database",
        required=True,
        help="Path to an existing synthetic business SQLite database.",
    )
    parser.add_argument(
        "--checkpoint-database",
        required=True,
        help="Path to an existing workflow checkpoint SQLite database.",
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    app = create_runtime_app(
        args.business_database,
        args.checkpoint_database,
    )
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
