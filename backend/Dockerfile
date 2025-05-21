# ————————————————————————————————
# 1) Build & Collectstatic
FROM python:3.12-slim AS build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Системные зависимости
RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    build-essential gcc libpq-dev pkg-config \
    libcairo2-dev python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Копируем только то, что влияет на pip-install
COPY requirements.txt data/ ./

RUN pip install --no-cache-dir -r requirements.txt

# Копируем код и собираем статику
COPY backend/ ./backend/
WORKDIR /app/backend
RUN python manage.py collectstatic --noinput

# ————————————————————————————————
# 2) Runtime
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Системные зависимости нужны и здесь (для psycopg2/reportlab/pycairo)
RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    libpq-dev libcairo2-dev && \
    rm -rf /var/lib/apt/lists/*

# Переносим всё из build-шага
COPY --from=build /usr/local /usr/local
COPY --from=build /app/backend /app/backend

WORKDIR /app/backend

# Копируем entrypoint и сделаем его исполняемым
COPY backend/yandex_top.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

ENTRYPOINT ["./yandex_top.sh"]
