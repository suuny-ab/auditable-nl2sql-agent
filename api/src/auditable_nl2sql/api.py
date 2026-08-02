"""Read-only HTTP projection over persisted workflow runs."""

from __future__ import annotations

from typing import Annotated, Any, Protocol

from fastapi import FastAPI, HTTPException, Query

from .workflow import RunNotFoundError


class RunReader(Protocol):
    """Minimum product interface exposed by the read-only HTTP surface."""

    def list_runs(self, *, limit: int, offset: int) -> dict[str, Any]: ...

    def get_run(self, run_id: str) -> dict[str, Any]: ...


def create_app(run_reader: RunReader) -> FastAPI:
    """Create an app that can only inspect existing workflow records."""
    app = FastAPI(
        title="Auditable NL2SQL read-only API",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.get("/api/v1/runs", response_model=None)
    def list_runs(
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        return run_reader.list_runs(limit=limit, offset=offset)

    @app.get("/api/v1/runs/{run_id}", response_model=None)
    def get_run(run_id: str) -> dict[str, Any]:
        try:
            return run_reader.get_run(run_id)
        except RunNotFoundError as exc:
            raise HTTPException(status_code=404, detail="run not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="invalid run_id") from exc

    return app
