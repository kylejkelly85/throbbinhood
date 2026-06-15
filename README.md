# Containerized Document Discovery Platform

A FastHTML + Crawlee + SQLAlchemy ASGI platform, powered by Python 3.12, Clean Architecture, and Docker Compose.

## Hardware Support
Engineered with lightweight images and async streaming for low-memory constraints (optimized for environments like Nvidia Jetson Orin Nano).

## Quickstart

```bash
docker compose up --build
```

Access the UI at: `http://localhost:8000`

## Architecture Highlights
- **FastHTML & HTMX**: Real-time polling without SPA overhead.
- **Crawlee**: Asynchronous Playwright web scraping.
- **Structlog**: Performant JSON logging.
- **Clean Architecture**: Strong boundary enforcement between DB, Services, and UI.
