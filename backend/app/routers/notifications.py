"""
WebSocket — Notificaciones en Tiempo Real

Hub de WebSocket para enviar notificaciones push al frontend:
- Eventos creados/actualizados
- Alertas financieras próximas
- Tareas completadas/vencidas
"""
import json
from datetime import datetime
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["Notificaciones WebSocket"])


class ConnectionManager:
    """Administra conexiones WebSocket activas."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"🔌 WebSocket conectado. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"🔌 WebSocket desconectado. Total: {len(self.active_connections)}")

    async def send_personal(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: dict):
        """Enviar mensaje a todos los clientes conectados."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            self.active_connections.remove(conn)


# Instancia global
manager = ConnectionManager()


@router.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket):
    """Endpoint WebSocket para notificaciones en tiempo real."""
    await manager.connect(websocket)
    try:
        # Enviar mensaje de bienvenida
        await manager.send_personal({
            "type": "connected",
            "message": "🧠 Conectado a Cerebro Operativo",
            "timestamp": datetime.utcnow().isoformat(),
        }, websocket)

        # Mantener conexión abierta y escuchar mensajes del cliente
        while True:
            data = await websocket.receive_text()
            # El cliente puede enviar pings o solicitudes
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await manager.send_personal({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat(),
                    }, websocket)
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        manager.disconnect(websocket)


# === Funciones para enviar notificaciones desde otros módulos ===

async def notify_task_created(task_data: dict):
    """Notificar que se creó una nueva tarea."""
    await manager.broadcast({
        "type": "task_created",
        "data": task_data,
        "timestamp": datetime.utcnow().isoformat(),
    })


async def notify_task_completed(task_data: dict):
    """Notificar que se completó una tarea."""
    await manager.broadcast({
        "type": "task_completed",
        "data": task_data,
        "timestamp": datetime.utcnow().isoformat(),
    })


async def notify_financial_alert(alert_data: dict):
    """Notificar alerta financiera próxima."""
    await manager.broadcast({
        "type": "financial_alert",
        "data": alert_data,
        "timestamp": datetime.utcnow().isoformat(),
    })


async def notify_event_reminder(event_data: dict):
    """Notificar recordatorio de evento."""
    await manager.broadcast({
        "type": "event_reminder",
        "data": event_data,
        "timestamp": datetime.utcnow().isoformat(),
    })
