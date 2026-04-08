# VoidRP Backend Stage 1

Первый этап реализации единой аккаунтной платформы VoidRP.

## Что входит в этап

- FastAPI foundation
- PostgreSQL + SQLAlchemy 2.0
- Alembic migration foundation
- Таблицы:
  - `users`
  - `player_accounts`
  - `refresh_sessions`
  - `email_tokens`
- Базовые endpoints:
  - `POST /api/v1/auth/register`
  - `POST /api/v1/auth/login`
  - `POST /api/v1/auth/refresh`
  - `POST /api/v1/auth/logout`
  - `GET /api/v1/me`
  - `GET /api/v1/health`
- Password hashing через `pwdlib` + Argon2
- Access token через JWT
- Refresh session как отдельный opaque token, хэшируемый в БД
- Email service abstraction c logging backend
- Базовые smoke tests на auth flow

## Почему так

- **Access token** короткоживущий и stateless.
- **Refresh token** хранится в БД как хэш, потому что его нужно отзывать, ротировать и привязывать к устройству.
- **Legacy auth** на этом этапе ещё не реализован в endpoint-логике, но поля под future migration уже заложены в `player_accounts`.
- **Nickname normalization** и **login/email normalization** вынесены отдельно, чтобы избежать дублей вроде `Yan`, `YAN`, `yan`.

## Запуск локально

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
```

Подними PostgreSQL и создай БД `voidrp_accounts`, затем примени миграцию:

```bash
alembic upgrade head
```

Запуск API:

```bash
uvicorn apps.api.app.main:app --reload
```

Swagger будет доступен по адресу:

```text
http://127.0.0.1:8000/docs
```

## Базовый auth flow

### Регистрация

```json
POST /api/v1/auth/register
{
  "site_login": "yann",
  "minecraft_nickname": "YannGotti",
  "email": "yann@example.com",
  "password": "StrongPassword123!",
  "password_repeat": "StrongPassword123!"
}
```

### Логин

```json
POST /api/v1/auth/login
{
  "login": "yann",
  "password": "StrongPassword123!",
  "device_name": "VoidRP Launcher Windows"
}
```

### Refresh

```json
POST /api/v1/auth/refresh
{
  "refresh_token": "<opaque-token>",
  "device_name": "VoidRP Launcher Windows"
}
```

### Logout

```json
POST /api/v1/auth/logout
{
  "refresh_token": "<opaque-token>"
}
```

## Важные проектные решения этого этапа

1. `site_login_normalized`, `email_normalized`, `minecraft_nickname_normalized` добавлены сразу.
2. `legacy_auth_enabled`, `legacy_password_hash`, `legacy_hash_algo` заложены уже в стартовую модель.
3. `nickname_locked` добавлен сразу: позже он понадобится, когда связь аккаунта и ника станет строго обязательной.
4. `email_tokens` унифицированы под разные цели: verification, password reset и дальнейшие flow.
5. Вынесен `create_app()`, чтобы потом было проще тестировать и подключать middleware/observability.
# VOIDRP-backend
