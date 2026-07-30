FROM ghcr.io/astral-sh/uv:0.9.18 AS uv
FROM python:3.13-slim-trixie

RUN --mount=from=uv,source=/uv,target=./uv \
  ./uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

# skip playwright browser download — browsers run in a separate container
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

RUN --mount=type=cache,target=/root/.cache/uv \
  --mount=from=uv,source=/uv,target=./uv \
  ./uv pip install  -r requirements.txt

RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils \
  && rm -rf /var/lib/apt/lists/*

# Copy the rest of the application files
COPY . .

RUN mkdir -p /data

# Data directory for pictures and files
VOLUME ["/data"]

# Backend port
EXPOSE 8010
