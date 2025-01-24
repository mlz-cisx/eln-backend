FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY . .

# install weasyprint and dependencies
RUN apt-get update && \
    apt-get install -y \
    weasyprint \
    python3-pip \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# install python dependencies
RUN pip install --no-cache-dir -r requirements.txt &&\
    pip install --no-cache-dir psycopg2-binary weasyprint

# configure env variables
RUN mv /app/docker-env.py /app/joeseln_backend/conf/base_conf.py

# data directory for pictures and files
RUN mkdir /data
VOLUME ["/data"]

# backend port
EXPOSE 8010

# start backend application
WORKDIR /app/joeseln_backend
CMD ["uvicorn", "main:app", "--reload", "--port", "8010", "--host", "0.0.0.0", "--loop", "asyncio"]


