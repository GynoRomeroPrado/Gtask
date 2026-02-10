"""
🧠 Cerebro Operativo — Entry Point FastAPI

Servidor principal que actúa como hub central del sistema:
1. API REST para gestión de tareas, listas y tags
2. (Fase 2) WebSocket para notificaciones en tiempo real
3. (Fase 2) Webhooks para Google Calendar / Gmail
4. (Fase 3) Procesamiento de comandos con LLM
"""
import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import get_settings
from app.database import engine, Base
from app.routers import health, tasks, task_lists, tags, events, financial_alerts, notifications, ai_chat, integrations, dashboard


settings = get_settings()

# Directorio del frontend
FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle del servidor:
    - Startup: Crea tablas si no existen (dev only)
    - Shutdown: Cierra conexiones
    """
    # --- Startup ---
    if settings.app_env == "development":
        Base.metadata.create_all(bind=engine)
        print("🧠 Cerebro Operativo iniciado [modo desarrollo]")
        print(f"📊 Base de datos: {settings.database_url.split('@')[-1]}")
        print(f"🌐 Frontend: {FRONTEND_DIR}")
    else:
        print("🧠 Cerebro Operativo iniciado [modo producción]")

    yield  # App running

    # --- Shutdown ---
    engine.dispose()
    print("🧠 Cerebro Operativo detenido")


# === Aplicación FastAPI ===

app = FastAPI(
    title="🧠 Cerebro Operativo",
    description=(
        "Sistema integral de gestión de tareas con IA. "
        "Centraliza productividad: tareas, calendario, finanzas, emails y salud."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# === Middleware CORS ===

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Desarrollo — restringir en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Registrar Routers ===

app.include_router(health.router, prefix="/api")
app.include_router(task_lists.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(tags.router, prefix="/api")
app.include_router(events.router, prefix="/api")
app.include_router(financial_alerts.router, prefix="/api")
app.include_router(notifications.router)
app.include_router(ai_chat.router, prefix="/api")
app.include_router(integrations.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")


# === Frontend estático ===

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", tags=["Root"])
def root():
    """Sirve el frontend o muestra info de la API."""
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "nombre": "🧠 Cerebro Operativo",
        "version": "0.1.0",
        "estado": "activo",
        "docs": "/docs",
    }

