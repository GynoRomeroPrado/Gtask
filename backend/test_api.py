"""
Test de integración — Verifica que todos los endpoints CRUD funcionan correctamente.
Ejecuta: python test_api.py (con el servidor corriendo en localhost:8000)
"""
import httpx
import json

BASE = "http://localhost:8000/api"


def test_full_crud():
    """Test completo de CRUD: Listas → Tags → Tareas."""
    client = httpx.Client(timeout=10.0)
    print("=" * 60)
    print("🧪 TEST DE INTEGRACIÓN — Cerebro Operativo")
    print("=" * 60)

    # === 1. Health Check ===
    print("\n--- 1. Health Check ---")
    r = client.get(f"{BASE}/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    print(f"✅ Health: {data}")

    # === 2. Crear Listas ===
    print("\n--- 2. Crear Listas de Tareas ---")
    listas = [
        {"name": "Trabajo", "color": "#EF4444", "icon": "💼"},
        {"name": "INTIMIQ", "color": "#8B5CF6", "icon": "🚀"},
        {"name": "Salud", "color": "#10B981", "icon": "🏋️"},
        {"name": "Personal", "color": "#3B82F6", "icon": "🏠"},
    ]
    list_ids = {}
    for lista in listas:
        r = client.post(f"{BASE}/lists/", json=lista)
        assert r.status_code == 201, f"Error creando lista: {r.text}"
        data = r.json()
        list_ids[lista["name"]] = data["id"]
        print(f"  ✅ Lista creada: {data['icon']} {data['name']} (id: {data['id'][:8]}...)")

    # === 3. Listar todas las listas ===
    print("\n--- 3. Listar todas las listas ---")
    r = client.get(f"{BASE}/lists/")
    assert r.status_code == 200
    all_lists = r.json()
    print(f"  ✅ {len(all_lists)} listas encontradas")

    # === 4. Crear Tags ===
    print("\n--- 4. Crear Tags ---")
    tags = [
        {"name": "urgente", "color": "#EF4444"},
        {"name": "financiero", "color": "#F59E0B"},
        {"name": "BBVA", "color": "#1D4ED8"},
        {"name": "Newmont", "color": "#059669"},
    ]
    tag_ids = {}
    for tag in tags:
        r = client.post(f"{BASE}/tags/", json=tag)
        assert r.status_code == 201, f"Error creando tag: {r.text}"
        data = r.json()
        tag_ids[tag["name"]] = data["id"]
        print(f"  ✅ Tag creado: {data['name']} ({data['color']})")

    # === 5. Crear Tareas ===
    print("\n--- 5. Crear Tareas ---")
    tareas = [
        {
            "title": "Revisar reporte mensual de Newmont",
            "description": "Analizar métricas Q4 2025 y preparar resumen",
            "priority": 2,
            "due_date": "2026-02-12",
            "list_id": list_ids["Trabajo"],
            "tag_ids": [tag_ids["Newmont"]],
        },
        {
            "title": "Pagar tarjeta BBVA",
            "description": "Vencimiento día 2 del mes — pagar antes",
            "priority": 1,
            "due_date": "2026-03-02",
            "list_id": list_ids["Personal"],
            "tag_ids": [tag_ids["urgente"], tag_ids["financiero"], tag_ids["BBVA"]],
        },
        {
            "title": "Sesión de gym — Pierna",
            "description": "Sentadilla, prensa, extensión, curl",
            "priority": 3,
            "due_date": "2026-02-10",
            "list_id": list_ids["Salud"],
        },
        {
            "title": "Diseñar landing page INTIMIQ",
            "description": "Wireframe + paleta de colores",
            "priority": 2,
            "due_date": "2026-02-14",
            "list_id": list_ids["INTIMIQ"],
        },
    ]
    task_ids = []
    for tarea in tareas:
        r = client.post(f"{BASE}/tasks/", json=tarea)
        assert r.status_code == 201, f"Error creando tarea: {r.text}"
        data = r.json()
        task_ids.append(data["id"])
        tags_str = ", ".join([t["name"] for t in data.get("tags", [])])
        print(f"  ✅ Tarea: '{data['title']}' | P{data['priority']} | Tags: [{tags_str}]")

    # === 6. Filtrar tareas ===
    print("\n--- 6. Filtrar tareas ---")

    # Por lista
    r = client.get(f"{BASE}/tasks/", params={"list_id": list_ids["Trabajo"]})
    assert r.status_code == 200
    print(f"  ✅ Tareas en 'Trabajo': {len(r.json())}")

    # Por prioridad urgente
    r = client.get(f"{BASE}/tasks/", params={"priority": 1})
    assert r.status_code == 200
    print(f"  ✅ Tareas urgentes: {len(r.json())}")

    # Búsqueda por texto
    r = client.get(f"{BASE}/tasks/", params={"search": "Newmont"})
    assert r.status_code == 200
    print(f"  ✅ Búsqueda 'Newmont': {len(r.json())} resultados")

    # === 7. Completar una tarea ===
    print("\n--- 7. Completar tarea ---")
    r = client.post(f"{BASE}/tasks/{task_ids[2]}/complete")
    assert r.status_code == 200
    data = r.json()
    print(f"  ✅ Tarea completada: '{data['title']}' | status={data['status']} | completed_at={data['completed_at']}")

    # === 8. Postergar una tarea ===
    print("\n--- 8. Postergar tarea ---")
    r = client.post(f"{BASE}/tasks/{task_ids[0]}/defer", params={"new_due_date": "2026-02-15"})
    assert r.status_code == 200
    data = r.json()
    print(f"  ✅ Tarea postergada: '{data['title']}' | nuevo due_date={data['due_date']}")

    # === 9. Obtener tarea con detalle ===
    print("\n--- 9. Detalle de tarea ---")
    r = client.get(f"{BASE}/tasks/{task_ids[1]}")
    assert r.status_code == 200
    data = r.json()
    print(f"  ✅ Tarea: '{data['title']}'")
    print(f"     Status: {data['status']} | Priority: {data['priority']}")
    print(f"     Due: {data['due_date']} | Tags: {[t['name'] for t in data['tags']]}")

    # === Resumen ===
    print("\n" + "=" * 60)
    print("✅ TODOS LOS TESTS PASARON EXITOSAMENTE")
    print("=" * 60)
    print(f"  📋 Listas creadas: {len(list_ids)}")
    print(f"  🏷️  Tags creados: {len(tag_ids)}")
    print(f"  📝 Tareas creadas: {len(task_ids)}")
    print(f"  ✅ Tarea completada: 1")
    print(f"  ⏩ Tarea postergada: 1")
    print(f"  🔍 Filtros probados: lista, prioridad, búsqueda")

    client.close()


if __name__ == "__main__":
    test_full_crud()
