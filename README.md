# Workout App — бэкенд

API для приложения тренировок: программы, дни, упражнения, расписание,
запись подходов и статистика. FastAPI + SQLAlchemy (async) + PostgreSQL.

## Быстрый старт

```bash
# 1. Настройки
cp .env.example .env          # затем впишите свой SECRET_KEY

# 2. База данных
docker compose up -d

# 3. Зависимости
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt

# 4. Миграции и запуск
cd backend
alembic upgrade head
uvicorn app.main:app --reload
```

Документация со всеми роутами: http://localhost:8000/docs

## Фронтенд

React + TypeScript, сборка через Vite. Лежит в папке `frontend/`.

Один раз установите Node.js (в терминале WSL):

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
source ~/.bashrc
nvm install 22
```

Затем в папке фронтенда:

```bash
cd frontend
npm install        # один раз, скачивает зависимости в node_modules
npm run dev        # запуск на http://localhost:5173
```

Фоновые сцены (статуи и колонны) лежат в `frontend/public/scenes`, а
какая сцена стоит на каком экране — в `frontend/src/components/Scene.tsx`.
Чтобы заменить картинку, положите новый файл с тем же именем или добавьте
сцену в список `SCENES`.

Бэкенд при этом должен работать на `localhost:8000`. Другой адрес можно
задать в `frontend/.env.local` (пример в `.env.example`).

Другие команды:

```bash
npm run typecheck  # проверить типы TypeScript
npm run build      # собрать готовую версию в frontend/dist
```

Устройство:

```
frontend/src/
  api/          запросы к бэкенду и типы ответов
  components/   общие элементы: кнопки, диалоги, графики, штанга с блинами
  lib/          даты, форматирование чисел, роутер, загрузка данных
  pages/        экраны приложения
  styles.css    все стили и цвета
```

## Тесты

```bash
cd backend
pytest
```

Тесты работают с отдельной базой `workout_db_test`: она создаётся сама,
а таблицы в ней очищаются перед каждым тестом. Основная база не
затрагивается. Нужен только запущенный контейнер с PostgreSQL.

Полезные варианты запуска:

```bash
pytest -v                          # подробный список тестов
pytest tests/test_workout_sets.py  # один файл
pytest -k private                  # только проверки доступа к чужим данным
pytest -x                          # остановиться на первой ошибке
```

## Настройки (.env в корне проекта)

| Переменная | Обязательна | По умолчанию | Что делает |
|---|---|---|---|
| `DATABASE_URL` | да | — | Подключение к PostgreSQL |
| `SECRET_KEY` | да | — | Секрет подписи токенов, от 16 символов |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | нет | 30 | Срок жизни access-токена |
| `REFRESH_TOKEN_EXPIRE_DAYS` | нет | 30 | Срок жизни refresh-токена |
| `CORS_ORIGINS` | нет | `localhost:3000`, `localhost:5173` | Адреса фронтенда, JSON-список |
| `COACH_EMAILS` | нет | пусто | Email-адреса тренеров через запятую |
| `SQL_ECHO` | нет | false | Печатать SQL-запросы в консоль |

## Аккаунт тренера

Тренер видит раздел «Тренер»: список всех пользователей с активностью
за период и страницу каждого — сводку, объём по неделям, тренировки
и рекорды. Менять чужие данные тренер не может. Свой дневник у него
работает как у всех.

1. Зарегистрируйте аккаунт тренера обычным способом.
2. Добавьте его email в переменную `COACH_EMAILS`
   (несколько — через запятую): `COACH_EMAILS=coach@example.com`.
3. Перезапустите бэкенд. Роли выставляются при каждом запуске, при
   регистрации и при смене email. Чтобы снять роль, уберите email из
   списка и перезапустите.

Email в приложении не подтверждается, поэтому указывайте в списке только
уже зарегистрированные адреса — иначе их может занять кто-то другой.

## Авторизация

1. `POST /users` — регистрация.
2. `POST /auth/login` — возвращает `access_token` и `refresh_token`.
3. Все остальные запросы: заголовок `Authorization: Bearer <access_token>`.
4. Когда access-токен истёк: `POST /auth/refresh` с `refresh_token`
   возвращает новую пару.

## Обзор API

| Раздел | Роуты |
|---|---|
| Аккаунт | `GET /auth/me`, `PATCH /users/me`, `POST /users/me/password`, `DELETE /users/me` |
| Упражнения | CRUD `/exercises`, фильтры `search`, `muscle_group`, `equipment` |
| Программы | CRUD `/programs`, `GET /programs/{id}` отдаёт дни и упражнения |
| Дни | CRUD `/programs/{id}/days`, `POST .../days/reorder` |
| Упражнения дня | CRUD `/programs/{id}/days/{id}/exercises`, `POST .../exercises/reorder` |
| Расписание | CRUD `/scheduled-workouts`, фильтры `date_from`, `date_to`, `status`, `program_id` |
| Автоплан | `POST /scheduled-workouts/generate` |
| Экран тренировки | `GET /scheduled-workouts/{id}/full` |
| Подходы | CRUD `/scheduled-workouts/{id}/sets` |
| Прогресс | `GET /exercises/{id}/history`, `GET /exercises/{id}/records` |
| Статистика | `GET /stats/summary`, `GET /stats/weekly-volume` |
| Тренер | `GET /coach/users`, `GET /coach/users/{id}` и `.../summary`, `.../weekly-volume`, `.../records`, `.../workouts` — только для роли `coach`, иначе `403` |

Правила, которые стоит знать фронтенду:

- Списки принимают `limit` (до 500, по умолчанию 100) и `offset`.
- `PUT` заменяет объект целиком, `PATCH` меняет только присланные поля.
- Статус тренировки: `planned`, `completed` или `skipped`.
- Упражнения без автора (`created_by_user_id: null`) общие и только для
  чтения. Свои упражнения видит и меняет только их автор.
- Чужие данные всегда отвечают `404`, конфликты уникальности — `409`,
  ошибки в данных — `422`.
- `order_index` уникален внутри программы (для дней) и внутри дня (для
  упражнений). Чтобы поменять порядок, используйте `reorder`.

## Деплой на Render (бесплатно)

Нужны три сервиса Render: база PostgreSQL, бэкенд и фронтенд.
Бесплатная база живёт 30 дней, после этого её нужно перевести на платный
тариф или создать заново. Бесплатный бэкенд засыпает после 15 минут без
запросов, первый запрос после этого ждёт около минуты.

1. Выложите проект на GitHub (файл `.env` туда не попадёт, он в `.gitignore`).
2. Render → New → Postgres, тариф Free. После создания скопируйте
   Internal Database URL.
3. Render → New → Web Service → ваш репозиторий:
   - Root Directory: `backend`, Language: Docker, тариф Free;
   - переменные: `DATABASE_URL` = Internal Database URL из шага 2,
     `SECRET_KEY` = длинная случайная строка;
   - после деплоя запишите адрес сервиса, например
     `https://workout-api.onrender.com`. Проверка: `/health`.
4. Render → New → Static Site → тот же репозиторий:
   - Root Directory: `frontend`;
   - Build Command: `npm install && npm run build`;
   - Publish Directory: `dist`;
   - переменная `VITE_API_URL` = адрес бэкенда из шага 3.
5. В бэкенде добавьте переменную
   `CORS_ORIGINS` = `["https://<адрес-фронтенда>.onrender.com"]`
   и сохраните — сервис перезапустится.
6. Тренер: зарегистрируйтесь на сайте, затем добавьте в бэкенд
   переменную `COACH_EMAILS` с этим email и сохраните.

Миграции и справочник упражнений применяются автоматически при каждом
запуске бэкенда.

## Всё в Docker

```bash
docker compose --profile full up -d --build
```

Поднимет базу и бэкенд на порту 8000, миграции применятся при старте.
Обычный `docker compose up -d` запускает только базу.

## Структура

```
frontend/       React-приложение (см. раздел «Фронтенд»)
backend/
  app/
    api/        роуты
    core/       токены, текущий пользователь, обработка ошибок базы
    database/   подключение и сессия
    models/     таблицы
    schemas/    проверка входных данных и формат ответов
  alembic/      миграции
  tests/        тесты
```
