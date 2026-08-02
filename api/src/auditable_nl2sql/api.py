"""Read-only HTTP projection over persisted workflow runs."""

from __future__ import annotations

from typing import Annotated, Any, Protocol

from fastapi import FastAPI, HTTPException, Query

from .workflow import RunNotFoundError


HEALTH_SCHEMA_VERSION = "health-v1"
SERVICE_VERSION = "0.1.0.dev0"


class RunReader(Protocol):
    """Minimum product interface exposed by the read-only HTTP surface."""

    def list_runs(self, *, limit: int, offset: int) -> dict[str, Any]: ...

    def get_run(self, run_id: str) -> dict[str, Any]: ...


def create_app(
    run_reader: RunReader | None = None,
    *,
    lifespan: Any | None = None,
) -> FastAPI:
    """Create an app that can only inspect existing workflow records."""
    app = FastAPI(
        title="Auditable NL2SQL read-only API",
        version=SERVICE_VERSION,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    if run_reader is not None:
        app.state.run_reader = run_reader

    def current_run_reader() -> RunReader:
        return app.state.run_reader

    @app.get("/api/v1/health", response_model=None)
    def health() -> dict[str, Any]:
        return {
            "schema_version": HEALTH_SCHEMA_VERSION,
            "status": "ok",
            "version": SERVICE_VERSION,
            "read_only": True,
        }

    @app.get("/api/v1/runs", response_model=None)
    def list_runs(
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        return current_run_reader().list_runs(limit=limit, offset=offset)

    @app.get("/api/v1/runs/{run_id}", response_model=None)
    def get_run(run_id: str) -> dict[str, Any]:
        try:
            return current_run_reader().get_run(run_id)
        except RunNotFoundError as exc:
            raise HTTPException(status_code=404, detail="run not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="invalid run_id") from exc

    return app
