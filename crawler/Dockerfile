FROM python:3.12-slim

WORKDIR /app

# Dependências do sistema para Pillow e Scrapy
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev libssl-dev libjpeg-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
COPY crawler/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o pacote do crawler e a camada db/
# O contexto de build é a raiz do projecto (definido no docker-compose)
COPY crawler/ /app/crawler/
COPY db/ /app/db/

# Pastas de dados — serão montadas como volumes em produção
RUN mkdir -p /data/downloads /data/jobs

ENV IMAGES_STORE=/data/downloads
ENV DATABASE_URL=sqlite:////data/crawler.db
ENV SCRAPY_LOG_LEVEL=INFO
ENV PYTHONPATH=/app

WORKDIR /app/crawler

# Ponto de entrada — scrapy está no PATH porque foi instalado via pip
ENTRYPOINT ["python", "-m", "scrapy"]
CMD ["crawl", "hqporno"]
