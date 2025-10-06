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
  ca-certificates \
  fonts-liberation \
  libappindicator3-1 \
  libasound2 \
  libatk-bridge2.0-0 \
  libatk1.0-0 \
  libc6 \
  libcairo2 \
  libcups2 \
  libdbus-1-3 \
  libexpat1 \
  libfontconfig1 \
  libgbm1 \
  libgcc1 \
  libglib2.0-0 \
  libgtk-3-0 \
  libnspr4 \
  libnss3 \
  libpango-1.0-0 \
  libx11-6 \
  libx11-xcb1 \
  libxcb1 \
  libxcomposite1 \
  libxcursor1 \
  libxdamage1 \
  libxext6 \
  libxfixes3 \
  libxi6 \
  libxrandr2 \
  libxrender1 \
  libxss1 \
  libxtst6 \
  lsb-release \
  wget \
  xdg-utils \
  && apt-get clean && \
  rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/uv \
  --mount=from=uv,source=/uv,target=./uv \
  ./uv pip install  -r requirements.txt

# Copy the rest of the application files
COPY . .

RUN cd joeseln_backend/export && npm install

# Configure env variables
RUN mv /app/docker-env.py /app/joeseln_backend/conf/base_conf.py &&\
  mkdir /data

# Data directory for pictures and files
VOLUME ["/data"]

# Backend port
EXPOSE 8010


