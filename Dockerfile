# syntax=docker/dockerfile:1.7

FROM node:22.23.1-bookworm-slim AS frontend-build

WORKDIR /build

COPY package.json package-lock.json vite.config.js ./
RUN --mount=type=cache,target=/root/.npm npm ci

COPY frontend ./frontend
RUN npm run build


FROM python:3.13.14-slim-bookworm AS runtime

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        traceroute \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 servicepath \
    && useradd \
        --gid servicepath \
        --home-dir /nonexistent \
        --no-create-home \
        --no-log-init \
        --shell /usr/sbin/nologin \
        --uid 10001 \
        servicepath

WORKDIR /app

COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install -r requirements.txt

COPY --chown=servicepath:servicepath app.py ./
COPY --chown=servicepath:servicepath diagnostics ./diagnostics
COPY --chown=servicepath:servicepath servicepath ./servicepath
COPY --from=frontend-build --chown=servicepath:servicepath \
    /build/static/frontend ./static/frontend

USER servicepath:servicepath

EXPOSE 5050

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=1 \
    CMD ["python", "-c", "from urllib.request import urlopen; urlopen('http://127.0.0.1:5050/healthz', timeout=3).close()"]

CMD ["gunicorn", "--bind=0.0.0.0:5050", "--worker-class=gthread", "--workers=1", "--threads=4", "--worker-tmp-dir=/tmp", "--timeout=300", "--graceful-timeout=60", "--no-control-socket", "--access-logfile=-", "--error-logfile=-", "app:app"]
