FROM ghcr.io/astral-sh/uv:0.2.12 AS uv
FROM python:3.10-slim

RUN --mount=from=uv,source=/uv,target=./uv \
  ./uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  npm \
  nodejs \
  chromium \
  && apt-get clean && \
  rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/uv \
  --mount=from=uv,source=/uv,target=./uv \
  ./uv pip install  -r requirements.txt

# Copy the rest of the application files
COPY . .

# chromium package managed by apt
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
# for non-root user to launch chromium
ENV XDG_CONFIG_HOME=/tmp/.chromium
ENV XDG_CACHE_HOME=/tmp/.chromium
RUN cd joeseln_backend/export && npm install

# Configure env variables
RUN mv /app/docker-env.py /app/joeseln_backend/conf/base_conf.py &&\
  mkdir /data

# Data directory for pictures and files
VOLUME ["/data"]

# Backend port
EXPOSE 8010


