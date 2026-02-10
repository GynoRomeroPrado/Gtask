# 🧠 Cerebro Operativo — Gestor de Tareas Inteligente

Sistema integral de gestión de tareas con IA que centraliza la productividad personal:
tareas, calendario, finanzas, emails, analítica y salud — orquestado por lenguaje natural.

## Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| **Backend** | FastAPI + Python 3.11+ |
| **Base de datos** | PostgreSQL 16 + SQLAlchemy 2.0 |
| **Frontend** | React/Next.js (PWA) |
| **IA** | LangChain + LlamaIndex + GPT-4o |
| **Voz** | Whisper Large V3 Turbo |
| **Google APIs** | Calendar, Tasks, Gmail, Sheets |
| **Notificaciones** | Firebase Cloud Messaging + WebSocket |

## Inicio Rápido

```bash
# 1. Crear entorno virtual
cd backend
python -m venv venv
venv\Scripts\activate  # Windows

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
copy .env.example .env
# Editar .env con tus credenciales

# 4. Ejecutar migraciones
alembic upgrade head

# 5. Iniciar servidor
uvicorn app.main:app --reload --port 8000
```

## Estructura del Proyecto

```
├── backend/          # API FastAPI
│   ├── app/          # Código fuente
│   ├── alembic/      # Migraciones de DB
│   └── tests/        # Tests
├── frontend/         # PWA React/Next.js
├── historial/        # Log de trabajo diario
└── docs/             # Documentación
```

## API Docs

Con el servidor corriendo: [http://localhost:8000/docs](http://localhost:8000/docs)
