"""
🧠 Motor de IA — Cerebro Operativo

Motor inteligente con soporte dual Google Gemini / OpenAI.
Funcionalidades:
- Procesamiento de comandos en lenguaje natural → acciones CRUD
- Sugerencias inteligentes basadas en contexto
- Memoria conversacional persistente
- Herramientas (tools) para interactuar con la base de datos
"""
import os
import json
from datetime import date, datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Modelos y DB
from app.models.task import Task
from app.models.task_list import TaskList
from app.models.tag import Tag
from app.models.event import Event, FinancialAlert
from app.models.conversation import Conversation


# =============================================================================
# CONFIGURACIÓN DEL LLM
# =============================================================================

def get_llm(provider: str = None):
    """
    Inicializa el LLM según la configuración.
    Prioridad: GEMINI_API_KEY → OPENAI_API_KEY → fallback local
    """
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    openai_key = os.getenv("OPENAI_API_KEY", "")

    if provider == "gemini" or (not provider and gemini_key):
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=gemini_key,
            temperature=0.3,
            max_output_tokens=1024,
        )
    elif provider == "openai" or (not provider and openai_key):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model="gpt-4o-mini",
            api_key=openai_key,
            temperature=0.3,
            max_tokens=1024,
        )
    else:
        return None


# =============================================================================
# SISTEMA DE PROMPT
# =============================================================================

SYSTEM_PROMPT = """Eres el asistente de IA de "Cerebro Operativo", un sistema de gestión de tareas personal.
Tu usuario es un Ingeniero de Sistemas y Analista de Datos. Responde siempre en español.

## Tus capacidades:
1. **Gestión de tareas**: Crear, editar, completar, eliminar y buscar tareas
2. **Calendario**: Crear eventos, consultar agenda
3. **Alertas financieras**: Gestionar pagos recurrentes
4. **Sugerencias**: Dar recomendaciones de productividad basadas en el contexto
5. **Análisis**: Resumir el estado actual de las tareas y prioridades

## Contexto actual:
- Fecha: {today}
- Tareas pendientes: {pending_tasks}
- Tareas de hoy: {today_tasks}
- Tareas vencidas: {overdue_tasks}
- Próximas alertas financieras: {financial_alerts}

## Reglas:
- Sé conciso y directo
- Usa emojis para claridad visual
- Si el usuario pide crear algo, hazlo y confirma
- Si no puedes hacer algo, sugiere alternativas
- Prioriza las tareas urgentes y vencidas en tus recomendaciones

## Formato de respuesta para acciones:
Cuando necesites ejecutar una acción, responde con el formato:
[ACTION:tipo_accion] seguido de tu confirmación.
Tipos: CREATE_TASK, COMPLETE_TASK, CREATE_EVENT, SUGGESTION, INFO
"""


# =============================================================================
# PROCESADOR DE CONTEXTO
# =============================================================================

def build_context(db: Session) -> dict:
    """Construye el contexto actual del sistema para el prompt."""
    today = date.today()
    today_str = today.isoformat()

    # Tareas pendientes
    pending = db.query(Task).filter(
        Task.status.in_(["pending", "in_progress"])
    ).all()

    # Tareas de hoy
    today_tasks = [t for t in pending if t.due_date and t.due_date.isoformat() == today_str]

    # Tareas vencidas
    overdue = [t for t in pending if t.due_date and t.due_date < today]

    # Alertas financieras activas (próximos 7 días)
    alerts = db.query(FinancialAlert).filter(
        FinancialAlert.is_active == True
    ).all()

    alerts_info = []
    for a in alerts:
        try:
            next_due = date(today.year, today.month, a.due_day_of_month)
            if next_due < today:
                if today.month == 12:
                    next_due = date(today.year + 1, 1, a.due_day_of_month)
                else:
                    next_due = date(today.year, today.month + 1, a.due_day_of_month)
            days = (next_due - today).days
            if days <= 7:
                alerts_info.append(f"{a.name} (vence en {days} días)")
        except ValueError:
            pass

    return {
        "today": today_str,
        "pending_tasks": len(pending),
        "today_tasks": len(today_tasks),
        "overdue_tasks": len(overdue),
        "financial_alerts": ", ".join(alerts_info) if alerts_info else "Ninguna próxima",
        # Datos crudos para el motor
        "_pending": pending,
        "_today": today_tasks,
        "_overdue": overdue,
        "_alerts": alerts,
    }


# =============================================================================
# PROCESADOR DE COMANDOS NLP
# =============================================================================

def parse_intent(message: str) -> dict:
    """
    Detecta la intención del mensaje del usuario (heurística rápida).
    Se usa como pre-procesamiento antes del LLM para acciones directas.
    """
    msg = message.lower().strip()

    # Crear tarea
    create_keywords = ["crea", "crear", "nueva tarea", "agrega", "agregar", "añade", "añadir"]
    if any(kw in msg for kw in create_keywords) and ("tarea" in msg or "task" in msg):
        return {"intent": "create_task", "raw": message}

    # Completar tarea
    complete_keywords = ["completa", "completar", "termina", "terminar", "done", "hecho", "listo"]
    if any(kw in msg for kw in complete_keywords):
        return {"intent": "complete_task", "raw": message}

    # Crear evento
    if any(kw in msg for kw in create_keywords) and ("evento" in msg or "reunión" in msg or "cita" in msg):
        return {"intent": "create_event", "raw": message}

    # Resumen / estado
    summary_keywords = ["resumen", "estado", "cómo voy", "qué tengo", "pendientes", "status"]
    if any(kw in msg for kw in summary_keywords):
        return {"intent": "summary", "raw": message}

    # Sugerencias
    suggest_keywords = ["sugiere", "sugerir", "recomienda", "qué hago", "priorizar", "ayuda"]
    if any(kw in msg for kw in suggest_keywords):
        return {"intent": "suggest", "raw": message}

    # Genérico
    return {"intent": "general", "raw": message}


# =============================================================================
# EJECUTOR DE ACCIONES
# =============================================================================

def execute_action(intent: dict, message: str, db: Session) -> Optional[str]:
    """
    Ejecuta acciones CRUD directas basadas en la intención detectada.
    Retorna None si el LLM debe manejar la respuesta.
    """
    if intent["intent"] == "summary":
        return generate_summary(db)

    if intent["intent"] == "suggest":
        return generate_suggestions(db)

    if intent["intent"] == "create_task":
        return try_create_task_from_nlp(message, db)

    return None  # Dejar que el LLM maneje


def generate_summary(db: Session) -> str:
    """Genera un resumen del estado actual."""
    ctx = build_context(db)
    pending = ctx["_pending"]
    overdue = ctx["_overdue"]
    today_tasks = ctx["_today"]

    lines = [f"## 📊 Resumen — {date.today().strftime('%d/%m/%Y')}\n"]

    # Tareas vencidas (urgente)
    if overdue:
        lines.append(f"### ⚠️ Tareas vencidas ({len(overdue)})")
        for t in overdue[:5]:
            lines.append(f"- 🔴 **{t.title}** — venció el {t.due_date}")
        lines.append("")

    # Tareas de hoy
    if today_tasks:
        lines.append(f"### 📅 Hoy ({len(today_tasks)})")
        for t in today_tasks:
            prio = {1: "🔴", 2: "🟡", 3: "🔵", 4: "⚪"}.get(t.priority, "⚪")
            lines.append(f"- {prio} {t.title}")
        lines.append("")

    # Resumen general
    by_priority = {}
    for t in pending:
        p = t.priority or 3
        by_priority[p] = by_priority.get(p, 0) + 1

    lines.append(f"### 📋 Total pendientes: {len(pending)}")
    prio_labels = {1: "🔴 Urgentes", 2: "🟡 Alta", 3: "🔵 Media", 4: "⚪ Baja"}
    for p in [1, 2, 3, 4]:
        if p in by_priority:
            lines.append(f"- {prio_labels[p]}: {by_priority[p]}")

    # Alertas financieras
    alerts = ctx["_alerts"]
    if alerts:
        lines.append(f"\n### 💰 Alertas financieras activas: {len(alerts)}")

    return "\n".join(lines)


def generate_suggestions(db: Session) -> str:
    """Genera sugerencias inteligentes basadas en el contexto."""
    ctx = build_context(db)
    overdue = ctx["_overdue"]
    today_tasks = ctx["_today"]
    pending = ctx["_pending"]

    lines = ["## 💡 Sugerencias\n"]

    # Tareas vencidas
    if overdue:
        lines.append("### ⚡ Acción inmediata")
        lines.append(f"Tienes **{len(overdue)} tarea(s) vencida(s)**. Sugiero:")
        for t in overdue[:3]:
            lines.append(f"- Completar o reprogramar: **{t.title}**")
        lines.append("")

    # Tareas urgentes sin fecha
    urgent_no_date = [t for t in pending if t.priority == 1 and not t.due_date]
    if urgent_no_date:
        lines.append("### 📌 Urgentes sin fecha")
        lines.append("Estas tareas urgentes no tienen fecha límite. ¡Ponles una!")
        for t in urgent_no_date[:3]:
            lines.append(f"- **{t.title}**")
        lines.append("")

    # Balance de carga
    if today_tasks and len(today_tasks) > 5:
        lines.append("### ⚖️ Sobrecarga")
        lines.append(f"Tienes {len(today_tasks)} tareas para hoy. Considera postergar algunas de baja prioridad.")
        lines.append("")

    # Productividad
    if len(pending) == 0:
        lines.append("### 🏆 ¡Excelente!")
        lines.append("No tienes tareas pendientes. ¡Hora de planificar algo nuevo!")
    elif len(pending) < 5:
        lines.append("### ✅ Buen ritmo")
        lines.append("Tienes pocas tareas pendientes. Sigue así.")
    elif len(pending) > 15:
        lines.append("### 📋 Muchas tareas")
        lines.append(f"Tienes {len(pending)} tareas pendientes. Considera agruparlas por prioridad y enfocarte en las top 3.")

    return "\n".join(lines)


def try_create_task_from_nlp(message: str, db: Session) -> Optional[str]:
    """
    Intenta extraer datos de tarea del mensaje y crearla.
    Formato esperado: 'Crear tarea: <título>' o similar
    """
    import re
    # Extraer título después de "tarea" o ":"
    patterns = [
        r'(?:crear|crea|nueva|agrega|añade)\s+(?:una?\s+)?tarea:?\s*(.+)',
        r'(?:crear|crea|nueva|agrega|añade)\s+tarea\s+(?:llamada|de|para|que diga)?\s*(.+)',
    ]

    title = None
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            title = match.group(1).strip().strip('"\'')
            break

    if not title:
        return None  # Dejar al LLM

    # Detectar prioridad
    priority = 3
    if any(w in message.lower() for w in ["urgente", "crítica", "crítico", "asap"]):
        priority = 1
    elif any(w in message.lower() for w in ["importante", "alta"]):
        priority = 2
    elif any(w in message.lower() for w in ["baja", "cuando pueda"]):
        priority = 4

    # Detectar fecha
    due_date = None
    if "hoy" in message.lower():
        due_date = date.today()
    elif "mañana" in message.lower():
        due_date = date.today() + timedelta(days=1)
    elif "semana" in message.lower():
        due_date = date.today() + timedelta(days=7)

    # Crear la tarea
    import uuid
    task = Task(
        id=str(uuid.uuid4()),
        title=title,
        priority=priority,
        due_date=due_date,
        status="pending",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    prio_labels = {1: "🔴 Urgente", 2: "🟡 Alta", 3: "🔵 Media", 4: "⚪ Baja"}
    date_str = f" — vence {due_date}" if due_date else ""
    return f"✅ Tarea creada: **{title}**\n• Prioridad: {prio_labels[priority]}{date_str}\n\n*La tarea aparecerá en tu lista al refrescar.*"


# =============================================================================
# CHAT CON LLM
# =============================================================================

def chat_with_ai(message: str, session_id: str, db: Session) -> str:
    """
    Procesa un mensaje del usuario y genera una respuesta.
    1. Detecta intención (heurística rápida)
    2. Si es una acción directa, la ejecuta
    3. Si no, usa el LLM con contexto
    4. Guarda en memoria conversacional
    """
    # Guardar mensaje del usuario
    save_message(db, session_id, "user", message)

    # 1. Detectar intención
    intent = parse_intent(message)

    # 2. Intentar acción directa
    direct_response = execute_action(intent, message, db)
    if direct_response:
        save_message(db, session_id, "assistant", direct_response)
        return direct_response

    # 3. Usar LLM
    llm = get_llm()
    if not llm:
        # Sin LLM configurado — usar respuesta inteligente local
        response = generate_fallback_response(message, intent, db)
        save_message(db, session_id, "assistant", response)
        return response

    # 4. Construir prompt con contexto
    ctx = build_context(db)
    system = SYSTEM_PROMPT.format(**{k: v for k, v in ctx.items() if not k.startswith("_")})

    # Cargar historial reciente
    history = get_recent_messages(db, session_id, limit=10)
    messages = [SystemMessage(content=system)]
    for msg in history[:-1]:  # Excluir el último (es el mensaje actual)
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            messages.append(AIMessage(content=msg.content))
    messages.append(HumanMessage(content=message))

    try:
        response = llm.invoke(messages)
        response_text = response.content
    except Exception as e:
        response_text = f"⚠️ Error al consultar el modelo: {str(e)[:100]}\n\nUsando respuesta local..."
        fallback = generate_fallback_response(message, intent, db)
        response_text += f"\n\n{fallback}"

    save_message(db, session_id, "assistant", response_text)
    return response_text


# =============================================================================
# MEMORIA CONVERSACIONAL
# =============================================================================

def save_message(db: Session, session_id: str, role: str, content: str):
    """Guarda un mensaje en la DB."""
    msg = Conversation(session_id=session_id, role=role, content=content)
    db.add(msg)
    db.commit()


def get_recent_messages(db: Session, session_id: str, limit: int = 20):
    """Obtiene los mensajes recientes de una sesión."""
    return (
        db.query(Conversation)
        .filter(Conversation.session_id == session_id)
        .order_by(Conversation.created_at.desc())
        .limit(limit)
        .all()
    )[::-1]  # Revertir para orden cronológico


# =============================================================================
# RESPUESTA FALLBACK (sin LLM)
# =============================================================================

def generate_fallback_response(message: str, intent: dict, db: Session) -> str:
    """
    Genera una respuesta útil sin LLM.
    Usa el motor de sugerencias y resumen como base.
    """
    if intent["intent"] in ["summary", "suggest"]:
        # Ya manejados por execute_action
        return generate_summary(db) + "\n\n" + generate_suggestions(db)

    # Para crear tareas, intentar extraer
    if intent["intent"] == "create_task":
        result = try_create_task_from_nlp(message, db)
        if result:
            return result

    # Respuesta genérica informativa
    ctx = build_context(db)
    lines = [
        "🧠 **Cerebro Operativo** — Modo local (sin LLM configurado)\n",
        "Puedo ayudarte con:",
        "• **\"resumen\"** — Ver estado actual de tus tareas",
        "• **\"sugerencias\"** — Obtener recomendaciones",
        "• **\"crear tarea: <título>\"** — Crear una tarea rápidamente",
        "",
        f"📊 Tienes **{ctx['pending_tasks']}** tareas pendientes, **{ctx['overdue_tasks']}** vencidas.",
        "",
        "💡 *Configura `GEMINI_API_KEY` o `OPENAI_API_KEY` en el archivo `.env` para respuestas inteligentes con IA.*",
    ]
    return "\n".join(lines)
