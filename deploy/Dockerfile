ARG PYTHON_IMAGE=python:3.13-slim-bookworm@sha256:9d7f287598e1a5a978c015ee176d8216435aaf335ed69ac3c38dd1bbb10e8d64

FROM ${PYTHON_IMAGE} AS dependencies
WORKDIR /build
COPY api/requirements-base.lock ./requirements-base.lock
RUN python -m pip install --disable-pip-version-check --no-cache-dir --no-deps \
    --require-hashes --prefix=/install --requirement requirements-base.lock

FROM ${PYTHON_IMAGE} AS fixture
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/api/src
WORKDIR /app
COPY --from=dependencies /install /usr/local
COPY api/src /app/api/src
COPY deploy/create_synthetic_fixture.py /build/create_synthetic_fixture.py
RUN python /build/create_synthetic_fixture.py --output /fixture

FROM ${PYTHON_IMAGE} AS runtime
ARG VCS_REF=local
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/api/src
WORKDIR /app
RUN groupadd --gid 10001 auditable \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin auditable
COPY --from=dependencies /install /usr/local
COPY --chown=10001:10001 api/src /app/api/src
COPY --from=fixture --chown=10001:10001 /fixture /opt/auditable-nl2sql/data
COPY --chown=10001:10001 --chmod=0555 deploy/container-entrypoint.sh /app/container-entrypoint.sh
LABEL org.opencontainers.image.source="https://github.com/suuny-ab/auditable-nl2sql-agent" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.title="auditable-nl2sql-read-only-api"
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=6 \
  CMD ["python", "-c", "import json,urllib.request; data=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health',timeout=2)); assert data['schema_version']=='health-v1' and data['status']=='ok' and data['read_only'] is True"]
CMD ["/app/container-entrypoint.sh"]
