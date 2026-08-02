#!/bin/sh
set -eu

source_directory=/opt/auditable-nl2sql/data
runtime_directory=/tmp/auditable-nl2sql-data

mkdir -p "$runtime_directory"
cp "$source_directory/business.sqlite3" "$runtime_directory/business.sqlite3"
cp "$source_directory/workflow.sqlite3" "$runtime_directory/workflow.sqlite3"
chmod 0444 "$runtime_directory/business.sqlite3" "$runtime_directory/workflow.sqlite3"

exec python -m auditable_nl2sql.server \
  --business-database "$runtime_directory/business.sqlite3" \
  --checkpoint-database "$runtime_directory/workflow.sqlite3" \
  --host 0.0.0.0 \
  --port 8000
