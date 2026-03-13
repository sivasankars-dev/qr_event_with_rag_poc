# Docker Setup (Cross-Platform: macOS/Linux/Windows)

## Prerequisites
- Docker Desktop installed
- On Windows: enable WSL2 backend in Docker Desktop

## 1) Configure environment
Edit `.env` and set at least:

- `API_KEY=<your_openai_api_key>`
- `SECRET_KEY=<your_secret_key>`
- `ALGORITHM=HS256`

Note: database-related values in `.env` are overridden in `docker-compose.yml` to use the internal `postgres` service.

## 2) Build and run
From the `qr_rag` folder:

```bash
docker compose up --build
```

PowerShell (Windows) uses the same command.

## 3) Open app
- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

## 4) Stop
```bash
docker compose down
```

To also remove persistent DB/Chroma volumes:

```bash
docker compose down -v
```
