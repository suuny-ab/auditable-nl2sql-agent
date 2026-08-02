"""Build the fixed synthetic, read-only container demonstration fixture."""

from __future__ import annotations

import argparse
from pathlib import Path

from auditable_nl2sql import CANONICAL_QUESTION, WorkflowRunner
from auditable_nl2sql.demo import create_demo_database


CONTAINER_DEMO_RUN_ID = "container-demo-run"


def create_synthetic_fixture(output_directory: str | Path) -> tuple[Path, Path]:
    """Create one business database and one completed workflow checkpoint."""
    output = Path(output_directory).resolve()
    output.mkdir(parents=True, exist_ok=False)
    business_database = create_demo_database(output / "business.sqlite3")
    checkpoint_database = output / "workflow.sqlite3"
    with WorkflowRunner(business_database, checkpoint_database) as runner:
        record = runner.run(
            run_id=CONTAINER_DEMO_RUN_ID,
            question=CANONICAL_QUESTION,
        )
    if record["status"] != "completed":
        raise RuntimeError("container demo run did not complete")
    return business_database, checkpoint_database


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create the fixed synthetic container fixture.",
    )
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    business_database, checkpoint_database = create_synthetic_fixture(
        arguments.output,
    )
    print(f"business_database={business_database}")
    print(f"checkpoint_database={checkpoint_database}")
    print(f"run_id={CONTAINER_DEMO_RUN_ID}")


if __name__ == "__main__":
    main()
