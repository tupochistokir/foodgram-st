## Быстрый старт

1. Клонируйте репозиторий:

   ```bash
   git clone 
   cd infra
   ```

2. Соберите и запустите контейнеры:

   ```bash
    docker-compose up --build
   ```

3. Откройте в браузере:

   * API: `http://localhost:8000/api/`
   * Документация (Swagger/OpenAPI): `http://localhost:8000/api/docs/`

## Остановка и очистка

* Остановить все контейнеры и удалить их:

  ```bash
  docker-compose down -v
  ```


## Полезные команды

* Просмотр логов:

  ```bash
  docker-compose logs -f backend
  docker-compose logs -f db
  docker-compose logs -f proxy
  ```


## Структура проекта

```
├── api/               # Главный модуль с маршрутами и утилитами
├── users/             # Приложение пользователей и подписок
├── recipes/           # Приложение рецептов и ингредиентов
├── add_components/    # Дополнительные пакеты и плагины
├── Dockerfile         # Сборка backend-контейнера
├── docker-compose.yml # Описание сервисов: proxy, db, backend
├── .env.example       # Пример файла окружения
├── manage.py
└── README.md
```

