# HQ Crawler

Sistema de crawling e gestão de galerias — **hqporno.net** e **superhq.net**.

## Arquitectura — separação total

```
hqcrawler/
├── db/              ← Camada partilhada (BD + modelos + crud)
├── crawler/         ← Container 1: Scrapy (independente)
├── web/             ← Container 2: Flask (independente)
└── docker-compose.yml
```

Cada camada pode ser substituída sem afectar as outras:

| Camada | Pode trocar por | Impacto |
|--------|----------------|---------|
| `db/` | PostgreSQL, MySQL | Só muda `DATABASE_URL` |
| `crawler/` | Playwright, requests | Zero impacto na web |
| `web/` | FastAPI, Django | Zero impacto no crawler |

---

## Uso local (sem Docker)

```bash
# Instalar
cd crawler && pip install -r requirements.txt
cd ../web  && pip install -r requirements.txt

# Crawler
cd crawler
scrapy crawl hqporno                                   # crawl completo
scrapy crawl superhq
scrapy crawl hqporno -s CLOSESPIDER_PAGECOUNT=10      # teste rápido
scrapy crawl hqporno -s JOBDIR=../jobs/hqporno        # com pausa/retomada

# Web
cd web
python run.py                        # http://127.0.0.1:5000
python run.py --host 0.0.0.0 --debug
```

## Uso com Docker

```bash
# Só a web
docker compose up web

# Crawler manual
docker compose run crawler scrapy crawl hqporno
docker compose run crawler scrapy crawl superhq

# Web em background + crawler
docker compose up -d web
docker compose run crawler scrapy crawl hqporno
```

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `DATABASE_URL` | `sqlite:///crawler.db` | BD — trocar para PostgreSQL em produção |
| `IMAGES_STORE` | `./downloads` | Pasta de imagens (Scrapy) |
| `DOWNLOADS_ROOT` | `./downloads` | Pasta de imagens (Web) |
| `SCRAPY_JOBDIR` | `""` | Pasta de pausa/retomada |

## Estrutura de downloads

```
downloads/
  hqporno/{slug}/cover.jpg + 01.jpg + 02.jpg ...
  superhq/{slug}/cover.jpg + 01.jpg + 02.jpg ...
```
# Scrallery
