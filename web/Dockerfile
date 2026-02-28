FROM python:3.12-slim

WORKDIR /app

COPY web/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Contexto de build é a raiz do projecto
COPY web/ /app/web/
COPY db/   /app/db/

RUN mkdir -p /data/downloads

ENV DATABASE_URL=sqlite:////data/crawler.db
ENV DOWNLOADS_ROOT=/data/downloads
ENV PYTHONPATH=/app

EXPOSE 5000

# Trabalha a partir de /app para que "web.app" e "db" sejam encontrados
WORKDIR /app

CMD ["gunicorn", "web.app:create_app()", "--bind", "0.0.0.0:5000", "--workers", "2"]
