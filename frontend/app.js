/**
 * 🧠 Cerebro Operativo — Frontend Application (Fase 2)
 * Gestión de tareas + Calendario + Alertas Financieras + WebSocket
 */

const API_BASE = 'http://localhost:8000/api';
const WS_URL = 'ws://localhost:8000/ws/notifications';

// === Estado de la aplicación ===
const state = {
    tasks: [],
    lists: [],
    tags: [],
    events: [],
    financialAlerts: [],
    currentView: 'all',
    currentListId: null,
    activePriorityFilter: null,
    searchQuery: '',
    selectedTagIds: new Set(),
    calendarMonth: new Date().getMonth(),
    calendarYear: new Date().getFullYear(),
    ws: null,
};

// =============================================================================
// INICIALIZACIÓN
// =============================================================================

document.addEventListener('DOMContentLoaded', async () => {
    await loadInitialData();
    setupKeyboardShortcuts();
    setupResponsive();
    connectWebSocket();
});

async function loadInitialData() {
    try {
        const [lists, tags, tasks, financials] = await Promise.all([
            apiFetch('/lists/'),
            apiFetch('/tags/'),
            apiFetch('/tasks/?include_completed=true&limit=200'),
            apiFetch('/financial-alerts/'),
        ]);
        state.lists = lists;
        state.tags = tags;
        state.tasks = tasks;
        state.financialAlerts = financials;

        renderSidebarLists();
        renderTaskTagsInModal();
        renderListOptions();
        renderTasks();
        updateBadges();
    } catch (err) {
        showToast('Error al conectar con el servidor', 'error');
        console.error('Init error:', err);
    }
}

// =============================================================================
// API
// =============================================================================

async function apiFetch(path, options = {}) {
    const url = API_BASE + path;
    const config = {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    };
    const res = await fetch(url, config);
    if (!res.ok) {
        const error = await res.text();
        throw new Error(`API Error ${res.status}: ${error}`);
    }
    if (res.status === 204) return null;
    return res.json();
}

// =============================================================================
// WebSocket
// =============================================================================

function connectWebSocket() {
    try {
        state.ws = new WebSocket(WS_URL);
        state.ws.onopen = () => {
            console.log('🔌 WebSocket conectado');
            const indicator = document.getElementById('notif-indicator');
            if (indicator) indicator.style.display = 'flex';
        };
        state.ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                handleWSMessage(msg);
            } catch { /* ignore */ }
        };
        state.ws.onclose = () => {
            console.log('🔌 WebSocket desconectado. Reconectando en 5s...');
            const indicator = document.getElementById('notif-indicator');
            if (indicator) indicator.style.display = 'none';
            setTimeout(connectWebSocket, 5000);
        };
        state.ws.onerror = () => { /* silently handle */ };
    } catch { /* WebSocket not available */ }
}

function handleWSMessage(msg) {
    switch (msg.type) {
        case 'connected':
            showToast(msg.message, 'info');
            break;
        case 'task_completed':
            showToast(`✅ Tarea completada: ${msg.data?.title}`, 'success');
            break;
        case 'financial_alert':
            showToast(`💳 Alerta: ${msg.data?.name}`, 'info');
            break;
        case 'event_reminder':
            showToast(`🔔 Recordatorio: ${msg.data?.title}`, 'info');
            break;
    }
}

// =============================================================================
// RENDERIZADO — SIDEBAR
// =============================================================================

function renderSidebarLists() {
    const container = document.getElementById('nav-lists');
    container.innerHTML = state.lists.map(list => `
        <li>
            <button class="sidebar-item ${state.currentView === 'list-' + list.id ? 'active' : ''}"
                    data-view="list-${list.id}"
                    onclick="switchToList('${list.id}', '${list.icon} ${list.name}')">
                <span class="list-color-dot" style="background:${list.color}"></span>
                ${list.icon} ${list.name}
                <span class="badge">${list.task_count}</span>
            </button>
        </li>
    `).join('');
}

function renderListOptions() {
    const select = document.getElementById('task-list');
    select.innerHTML = '<option value="">Sin lista</option>' +
        state.lists.map(l => `<option value="${l.id}">${l.icon} ${l.name}</option>`).join('');
}

function renderTaskTagsInModal() {
    const container = document.getElementById('task-tags-container');
    container.innerHTML = state.tags.map(tag => `
        <button type="button"
                class="form-tag-chip ${state.selectedTagIds.has(tag.id) ? 'selected' : ''}"
                data-tag-id="${tag.id}"
                style="${state.selectedTagIds.has(tag.id) ? 'background:' + tag.color : ''}"
                onclick="toggleTagSelection('${tag.id}', '${tag.color}')">
            ${tag.name}
        </button>
    `).join('');

    if (state.tags.length === 0) {
        container.innerHTML = '<span style="font-size:0.78rem;color:var(--text-muted)">Sin tags — crea uno desde la API</span>';
    }
}

// =============================================================================
// RENDERIZADO — TAREAS
// =============================================================================

function renderTasks() {
    const container = document.getElementById('task-container');
    const filtered = getFilteredTasks();

    document.getElementById('task-count').textContent = `${filtered.length} tarea${filtered.length !== 1 ? 's' : ''}`;

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="icon">${getEmptyIcon()}</div>
                <h3>${getEmptyTitle()}</h3>
                <p>${getEmptyDescription()}</p>
            </div>
        `;
        return;
    }

    const groups = {};
    const priorityLabels = { 1: '🔴 Urgente', 2: '🟡 Alta prioridad', 3: '🔵 Prioridad media', 4: '⚪ Baja prioridad' };

    filtered.forEach(task => {
        const p = task.priority || 3;
        if (!groups[p]) groups[p] = [];
        groups[p].push(task);
    });

    let html = '';
    for (const priority of [1, 2, 3, 4]) {
        const tasks = groups[priority];
        if (!tasks || tasks.length === 0) continue;
        html += `<div class="task-group">`;
        html += `<div class="task-group-title">${priorityLabels[priority]} (${tasks.length})</div>`;
        tasks.forEach(task => { html += renderTaskCard(task); });
        html += `</div>`;
    }
    container.innerHTML = html;
}

function renderTaskCard(task) {
    const isCompleted = task.status === 'completed';
    const dueClass = getDueDateClass(task.due_date);
    const dueLabel = formatDueDate(task.due_date);
    const listInfo = getListInfo(task.list_id);

    return `
        <div class="task-card ${isCompleted ? 'completed' : ''}" data-task-id="${task.id}">
            <div class="task-priority priority-${task.priority || 3}"></div>
            <div class="task-checkbox ${isCompleted ? 'checked' : ''}"
                 onclick="event.stopPropagation(); toggleTaskComplete('${task.id}', ${isCompleted})"></div>
            <div class="task-body" onclick="openEditTaskModal('${task.id}')">
                <div class="task-title">${escapeHtml(task.title)}</div>
                ${task.description ? `<div class="task-description">${escapeHtml(task.description)}</div>` : ''}
                <div class="task-meta">
                    ${task.due_date ? `<span class="task-due ${dueClass}">📅 ${dueLabel}</span>` : ''}
                    ${listInfo ? `<span class="task-tag" style="background:${listInfo.color}">${listInfo.icon} ${listInfo.name}</span>` : ''}
                    ${(task.tags || []).map(t => `<span class="task-tag" style="background:${t.color}">${t.name}</span>`).join('')}
                </div>
            </div>
            <div class="task-actions">
                <button class="task-action-btn" onclick="event.stopPropagation(); openEditTaskModal('${task.id}')" title="Editar">✏️</button>
                <button class="task-action-btn delete" onclick="event.stopPropagation(); deleteTask('${task.id}')" title="Eliminar">🗑️</button>
            </div>
        </div>
    `;
}

// =============================================================================
// RENDERIZADO — CALENDARIO
// =============================================================================

async function renderCalendar() {
    const container = document.getElementById('calendar-container');
    const year = state.calendarYear;
    const month = state.calendarMonth;
    const monthNames = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
    const dayNames = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];

    try {
        state.events = await apiFetch(`/events/?month=${month + 1}&year=${year}`);
    } catch { state.events = []; }

    // Tareas con fecha de este mes
    const monthTasks = state.tasks.filter(t => {
        if (!t.due_date) return false;
        const d = new Date(t.due_date + 'T00:00:00');
        return d.getMonth() === month && d.getFullYear() === year;
    });

    // Alertas financieras este mes
    const monthAlerts = state.financialAlerts.filter(a => {
        if (!a.next_due_date) return false;
        const d = new Date(a.next_due_date);
        return d.getMonth() === month && d.getFullYear() === year;
    });

    // Construir grilla del calendario
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startDow = (firstDay.getDay() + 6) % 7; // Lunes = 0
    const totalDays = lastDay.getDate();
    const today = new Date();

    let html = `
        <div class="calendar-header-nav">
            <button class="btn btn-ghost btn-icon" onclick="changeMonth(-1)">◀</button>
            <h2 class="calendar-month-title">${monthNames[month]} ${year}</h2>
            <button class="btn btn-ghost btn-icon" onclick="changeMonth(1)">▶</button>
            <button class="btn btn-ghost btn-sm" onclick="goToToday()" style="margin-left:12px;">Hoy</button>
        </div>
        <div class="calendar-grid">
    `;

    // Encabezados de día
    dayNames.forEach(d => {
        html += `<div class="calendar-day-header">${d}</div>`;
    });

    // Celdas vacías antes del primer día
    for (let i = 0; i < startDow; i++) {
        html += `<div class="calendar-cell empty"></div>`;
    }

    // Días del mes
    for (let day = 1; day <= totalDays; day++) {
        const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        const isToday = today.getDate() === day && today.getMonth() === month && today.getFullYear() === year;

        // Eventos de este día
        const dayEvents = state.events.filter(e => e.event_date === dateStr);
        const dayTasks = monthTasks.filter(t => t.due_date === dateStr);
        const dayAlerts = monthAlerts.filter(a => a.next_due_date === dateStr || a.next_alert_date === dateStr);

        const hasItems = dayEvents.length > 0 || dayTasks.length > 0 || dayAlerts.length > 0;

        html += `<div class="calendar-cell ${isToday ? 'today' : ''} ${hasItems ? 'has-items' : ''}">`;
        html += `<div class="calendar-day-number">${day}</div>`;
        html += `<div class="calendar-cell-items">`;

        // Dot indicators
        dayEvents.forEach(e => {
            const typeIcons = { meeting: '👥', gym: '🏋️', reminder: '🔔', financial_alert: '💳', custom: '📌', health: '🩺' };
            html += `<div class="calendar-item" style="background:${e.color}20;border-left:3px solid ${e.color};" title="${escapeHtml(e.title)}">
                <span>${typeIcons[e.event_type] || '📅'}</span>
                <span class="calendar-item-text">${escapeHtml(e.title.substring(0, 18))}</span>
            </div>`;
        });

        dayTasks.forEach(t => {
            const pColors = { 1: '#EF4444', 2: '#F59E0B', 3: '#3B82F6', 4: '#6B6B80' };
            html += `<div class="calendar-item" style="background:${pColors[t.priority]}20;border-left:3px solid ${pColors[t.priority]};" title="${escapeHtml(t.title)}">
                <span>${t.status === 'completed' ? '✅' : '📝'}</span>
                <span class="calendar-item-text">${escapeHtml(t.title.substring(0, 18))}</span>
            </div>`;
        });

        dayAlerts.forEach(a => {
            html += `<div class="calendar-item" style="background:#F59E0B20;border-left:3px solid #F59E0B;" title="${escapeHtml(a.name)}">
                <span>💳</span>
                <span class="calendar-item-text">${escapeHtml(a.name.substring(0, 18))}</span>
            </div>`;
        });

        html += `</div></div>`;
    }

    html += `</div>`;

    // Resumen del día de hoy
    const todayStr = today.toISOString().split('T')[0];
    const todayTasks = state.tasks.filter(t => t.due_date === todayStr && t.status !== 'completed');
    if (todayTasks.length > 0) {
        html += `<div class="today-summary">
            <h3>📅 Hoy — ${todayTasks.length} tarea${todayTasks.length > 1 ? 's' : ''} pendiente${todayTasks.length > 1 ? 's' : ''}</h3>
            <div class="today-tasks">`;
        todayTasks.forEach(t => {
            html += `<div class="today-task-item">
                <span class="priority-dot priority-${t.priority}"></span>
                ${escapeHtml(t.title)}
            </div>`;
        });
        html += `</div></div>`;
    }

    container.innerHTML = html;
    document.getElementById('task-count').textContent = `${state.events.length} eventos`;
}

function changeMonth(delta) {
    state.calendarMonth += delta;
    if (state.calendarMonth > 11) { state.calendarMonth = 0; state.calendarYear++; }
    if (state.calendarMonth < 0) { state.calendarMonth = 11; state.calendarYear--; }
    renderCalendar();
}

function goToToday() {
    state.calendarMonth = new Date().getMonth();
    state.calendarYear = new Date().getFullYear();
    renderCalendar();
}

// =============================================================================
// RENDERIZADO — ALERTAS FINANCIERAS
// =============================================================================

async function renderFinancialAlerts() {
    const container = document.getElementById('financial-container');

    try {
        state.financialAlerts = await apiFetch('/financial-alerts/');
    } catch { state.financialAlerts = []; }

    if (state.financialAlerts.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="icon">💰</div>
                <h3>Sin alertas financieras</h3>
                <p>Configura tus pagos recurrentes (tarjetas, servicios) para recibir alertas antes del vencimiento.</p>
            </div>
        `;
        return;
    }

    let html = `<div class="financial-grid">`;

    state.financialAlerts.forEach(alert => {
        const urgencyClass = alert.days_until_due <= 3 ? 'urgent' : alert.days_until_due <= 7 ? 'warning' : 'normal';
        const categoryIcons = {
            tarjeta_credito: '💳', servicio: '🔌', prestamo: '🏦',
            suscripcion: '📱', otro: '📄'
        };
        const icon = categoryIcons[alert.category] || '💰';
        const paidThisMonth = alert.last_paid_date && isCurrentMonth(alert.last_paid_date);

        html += `
            <div class="financial-card ${urgencyClass} ${paidThisMonth ? 'paid' : ''}">
                <div class="financial-card-header">
                    <span class="financial-icon">${icon}</span>
                    <div class="financial-info">
                        <div class="financial-name">${escapeHtml(alert.name)}</div>
                        <div class="financial-category">${alert.category.replace('_', ' ')}</div>
                    </div>
                    <div class="financial-status">
                        ${paidThisMonth
                ? '<span class="financial-badge paid">✅ Pagado</span>'
                : `<span class="financial-badge ${urgencyClass}">${alert.days_until_due}d</span>`
            }
                    </div>
                </div>
                <div class="financial-card-body">
                    <div class="financial-detail">
                        <span>📅 Vencimiento</span>
                        <strong>Día ${alert.due_day_of_month} de cada mes</strong>
                    </div>
                    <div class="financial-detail">
                        <span>⏰ Próximo vencimiento</span>
                        <strong>${formatDate(alert.next_due_date)}</strong>
                    </div>
                    <div class="financial-detail">
                        <span>🔔 Próxima alerta</span>
                        <strong>${formatDate(alert.next_alert_date)}</strong>
                    </div>
                    ${alert.amount ? `
                    <div class="financial-detail">
                        <span>💵 Monto</span>
                        <strong>${alert.currency} ${alert.amount}</strong>
                    </div>` : ''}
                </div>
                <div class="financial-card-actions">
                    ${!paidThisMonth ? `
                    <button class="btn btn-success btn-sm" onclick="markAsPaid('${alert.id}')">
                        ✅ Marcar pagado
                    </button>` : ''}
                    <button class="btn btn-danger btn-sm" onclick="deleteFinancialAlert('${alert.id}')">
                        🗑️ Eliminar
                    </button>
                </div>
            </div>
        `;
    });

    html += `</div>`;

    // Botón para generar eventos
    html += `
        <div style="text-align:center;margin-top:20px;">
            <button class="btn btn-ghost" onclick="generateFinancialEvents()">
                📅 Generar eventos en calendario
            </button>
        </div>
    `;

    container.innerHTML = html;
    document.getElementById('task-count').textContent = `${state.financialAlerts.length} alerta${state.financialAlerts.length > 1 ? 's' : ''}`;
    document.getElementById('badge-financial').textContent = state.financialAlerts.filter(a => a.days_until_due <= 7).length;
}

function isCurrentMonth(dateStr) {
    if (!dateStr) return false;
    const d = new Date(dateStr);
    const now = new Date();
    return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
}

// =============================================================================
// FILTRADO
// =============================================================================

function getFilteredTasks() {
    let tasks = [...state.tasks];

    switch (state.currentView) {
        case 'all':
            tasks = tasks.filter(t => t.status !== 'completed' && t.status !== 'cancelled');
            break;
        case 'today':
            const today = new Date().toISOString().split('T')[0];
            tasks = tasks.filter(t => t.due_date === today && t.status !== 'completed');
            break;
        case 'upcoming':
            const now = new Date();
            const week = new Date(now);
            week.setDate(week.getDate() + 7);
            const todayStr = now.toISOString().split('T')[0];
            const weekStr = week.toISOString().split('T')[0];
            tasks = tasks.filter(t =>
                t.due_date && t.due_date >= todayStr && t.due_date <= weekStr &&
                t.status !== 'completed'
            );
            break;
        case 'completed':
            tasks = tasks.filter(t => t.status === 'completed');
            break;
        default:
            if (state.currentView.startsWith('list-')) {
                const listId = state.currentView.replace('list-', '');
                tasks = tasks.filter(t => t.list_id === listId && t.status !== 'completed');
            }
    }

    if (state.activePriorityFilter !== null) {
        tasks = tasks.filter(t => t.priority === state.activePriorityFilter);
    }

    if (state.searchQuery) {
        const q = state.searchQuery.toLowerCase();
        tasks = tasks.filter(t =>
            t.title.toLowerCase().includes(q) ||
            (t.description || '').toLowerCase().includes(q)
        );
    }

    return tasks;
}

function handleSearch() {
    state.searchQuery = document.getElementById('search-input').value;
    renderTasks();
}

function togglePriorityFilter(priority) {
    const chips = document.querySelectorAll('.filter-chip');
    if (state.activePriorityFilter === priority) {
        state.activePriorityFilter = null;
        chips.forEach(c => c.classList.remove('active'));
    } else {
        state.activePriorityFilter = priority;
        chips.forEach(c => {
            c.classList.toggle('active', parseInt(c.dataset.priority) === priority);
        });
    }
    renderTasks();
}

// =============================================================================
// NAVEGACIÓN
// =============================================================================

function switchView(view, title) {
    state.currentView = view;
    state.currentListId = null;
    document.getElementById('view-title').textContent = title;

    document.querySelectorAll('.sidebar-item').forEach(item => {
        item.classList.toggle('active', item.dataset.view === view);
    });

    // Toggle containers
    const isTaskView = !['calendar', 'financial'].includes(view);
    document.getElementById('task-container').style.display = isTaskView ? 'block' : 'none';
    document.getElementById('calendar-container').style.display = view === 'calendar' ? 'block' : 'none';
    document.getElementById('financial-container').style.display = view === 'financial' ? 'block' : 'none';
    document.getElementById('filter-bar-tasks').style.display = isTaskView ? 'flex' : 'none';

    // Toggle header buttons
    document.getElementById('btn-new-task').style.display = isTaskView ? 'inline-flex' : 'none';
    document.getElementById('btn-new-event').style.display = view === 'calendar' ? 'inline-flex' : 'none';
    document.getElementById('btn-new-alert').style.display = view === 'financial' ? 'inline-flex' : 'none';

    if (view === 'calendar') renderCalendar();
    else if (view === 'financial') renderFinancialAlerts();
    else renderTasks();
}

function switchToList(listId, title) {
    state.currentView = 'list-' + listId;
    state.currentListId = listId;
    document.getElementById('view-title').textContent = title;

    document.querySelectorAll('.sidebar-item').forEach(item => {
        item.classList.toggle('active', item.dataset.view === 'list-' + listId);
    });

    // Show task view
    document.getElementById('task-container').style.display = 'block';
    document.getElementById('calendar-container').style.display = 'none';
    document.getElementById('financial-container').style.display = 'none';
    document.getElementById('filter-bar-tasks').style.display = 'flex';
    document.getElementById('btn-new-task').style.display = 'inline-flex';
    document.getElementById('btn-new-event').style.display = 'none';
    document.getElementById('btn-new-alert').style.display = 'none';

    renderTasks();
}

// Setup sidebar view buttons
document.querySelectorAll('#nav-views [data-view]').forEach(btn => {
    const viewMap = {
        'all': '📋 Todas las tareas',
        'today': '📅 Hoy',
        'upcoming': '🗓️ Próximos 7 días',
        'completed': '✅ Completadas',
    };
    if (viewMap[btn.dataset.view]) {
        btn.addEventListener('click', () => switchView(btn.dataset.view, viewMap[btn.dataset.view]));
    }
});

// =============================================================================
// CRUD — TAREAS
// =============================================================================

function openNewTaskModal() {
    document.getElementById('task-edit-id').value = '';
    document.getElementById('modal-title').textContent = 'Nueva Tarea';
    document.getElementById('task-title').value = '';
    document.getElementById('task-description').value = '';
    document.getElementById('task-priority').value = '3';
    document.getElementById('task-due-date').value = '';
    document.getElementById('task-list').value = state.currentListId || '';
    state.selectedTagIds.clear();
    renderTaskTagsInModal();
    openModal('task-modal');
    setTimeout(() => document.getElementById('task-title').focus(), 200);
}

function openEditTaskModal(taskId) {
    const task = state.tasks.find(t => t.id === taskId);
    if (!task) return;

    document.getElementById('task-edit-id').value = task.id;
    document.getElementById('modal-title').textContent = 'Editar Tarea';
    document.getElementById('task-title').value = task.title;
    document.getElementById('task-description').value = task.description || '';
    document.getElementById('task-priority').value = task.priority || 3;
    document.getElementById('task-due-date').value = task.due_date || '';
    document.getElementById('task-list').value = task.list_id || '';

    state.selectedTagIds = new Set((task.tags || []).map(t => t.id));
    renderTaskTagsInModal();
    openModal('task-modal');
}

async function saveTask() {
    const editId = document.getElementById('task-edit-id').value;
    const title = document.getElementById('task-title').value.trim();
    if (!title) { showToast('El título es obligatorio', 'error'); return; }

    const data = {
        title,
        description: document.getElementById('task-description').value.trim() || null,
        priority: parseInt(document.getElementById('task-priority').value),
        due_date: document.getElementById('task-due-date').value || null,
        list_id: document.getElementById('task-list').value || null,
        tag_ids: Array.from(state.selectedTagIds),
    };

    try {
        if (editId) {
            const updated = await apiFetch(`/tasks/${editId}`, { method: 'PUT', body: JSON.stringify(data) });
            const idx = state.tasks.findIndex(t => t.id === editId);
            if (idx >= 0) state.tasks[idx] = updated;
            showToast('Tarea actualizada ✏️', 'success');
        } else {
            const created = await apiFetch('/tasks/', { method: 'POST', body: JSON.stringify(data) });
            state.tasks.unshift(created);
            showToast('Tarea creada 🎉', 'success');
        }
        closeTaskModal();
        renderTasks();
        updateBadges();
        refreshListCounts();
    } catch (err) {
        showToast('Error: ' + err.message, 'error');
    }
}

async function toggleTaskComplete(taskId, isCurrentlyCompleted) {
    try {
        if (isCurrentlyCompleted) {
            const updated = await apiFetch(`/tasks/${taskId}`, {
                method: 'PUT', body: JSON.stringify({ status: 'pending' }),
            });
            const idx = state.tasks.findIndex(t => t.id === taskId);
            if (idx >= 0) state.tasks[idx] = updated;
            showToast('Tarea reabierta', 'info');
        } else {
            const updated = await apiFetch(`/tasks/${taskId}/complete`, { method: 'POST' });
            const idx = state.tasks.findIndex(t => t.id === taskId);
            if (idx >= 0) state.tasks[idx] = updated;
            showToast('¡Tarea completada! ✅', 'success');
        }
        renderTasks();
        updateBadges();
        refreshListCounts();
    } catch (err) { showToast('Error: ' + err.message, 'error'); }
}

async function deleteTask(taskId) {
    if (!confirm('¿Eliminar esta tarea?')) return;
    try {
        await apiFetch(`/tasks/${taskId}`, { method: 'DELETE' });
        state.tasks = state.tasks.filter(t => t.id !== taskId);
        showToast('Tarea eliminada 🗑️', 'success');
        renderTasks();
        updateBadges();
        refreshListCounts();
    } catch (err) { showToast('Error: ' + err.message, 'error'); }
}

// =============================================================================
// CRUD — LISTAS
// =============================================================================

function openNewListModal() {
    document.getElementById('list-name').value = '';
    document.getElementById('list-color').value = '#6366F1';
    document.getElementById('list-icon').value = '📋';
    openModal('list-modal');
    setTimeout(() => document.getElementById('list-name').focus(), 200);
}

async function saveList() {
    const name = document.getElementById('list-name').value.trim();
    if (!name) { showToast('El nombre es obligatorio', 'error'); return; }

    try {
        const created = await apiFetch('/lists/', {
            method: 'POST',
            body: JSON.stringify({
                name,
                color: document.getElementById('list-color').value,
                icon: document.getElementById('list-icon').value,
            }),
        });
        state.lists.push({ ...created, task_count: 0 });
        renderSidebarLists();
        renderListOptions();
        closeListModal();
        showToast(`Lista "${name}" creada 📋`, 'success');
    } catch (err) { showToast('Error: ' + err.message, 'error'); }
}

// =============================================================================
// CRUD — EVENTOS
// =============================================================================

function openNewEventModal() {
    document.getElementById('event-edit-id').value = '';
    document.getElementById('event-modal-title').textContent = 'Nuevo Evento';
    document.getElementById('event-title').value = '';
    document.getElementById('event-description').value = '';
    document.getElementById('event-type').value = 'custom';
    document.getElementById('event-date').value = new Date().toISOString().split('T')[0];
    document.getElementById('event-start-time').value = '';
    document.getElementById('event-end-time').value = '';
    document.getElementById('event-color').value = '#8B5CF6';
    document.getElementById('event-alert').value = '30';
    openModal('event-modal');
    setTimeout(() => document.getElementById('event-title').focus(), 200);
}

function closeEventModal() {
    document.getElementById('event-modal').classList.remove('open');
}

async function saveEvent() {
    const title = document.getElementById('event-title').value.trim();
    if (!title) { showToast('El título es obligatorio', 'error'); return; }

    const alertVal = document.getElementById('event-alert').value;
    const data = {
        title,
        description: document.getElementById('event-description').value.trim() || null,
        event_type: document.getElementById('event-type').value,
        event_date: document.getElementById('event-date').value,
        start_time: document.getElementById('event-start-time').value || null,
        end_time: document.getElementById('event-end-time').value || null,
        color: document.getElementById('event-color').value,
        alert_minutes_before: alertVal ? parseInt(alertVal) : null,
    };

    try {
        const editId = document.getElementById('event-edit-id').value;
        if (editId) {
            await apiFetch(`/events/${editId}`, { method: 'PUT', body: JSON.stringify(data) });
            showToast('Evento actualizado 📅', 'success');
        } else {
            await apiFetch('/events/', { method: 'POST', body: JSON.stringify(data) });
            showToast('Evento creado 📅', 'success');
        }
        closeEventModal();
        renderCalendar();
    } catch (err) { showToast('Error: ' + err.message, 'error'); }
}

// =============================================================================
// CRUD — ALERTAS FINANCIERAS
// =============================================================================

function openNewFinancialAlertModal() {
    document.getElementById('fin-name').value = '';
    document.getElementById('fin-description').value = '';
    document.getElementById('fin-due-day').value = '';
    document.getElementById('fin-alert-days').value = '3';
    document.getElementById('fin-amount').value = '';
    document.getElementById('fin-category').value = 'tarjeta_credito';
    document.getElementById('fin-currency').value = 'PEN';
    document.getElementById('fin-color').value = '#F59E0B';
    openModal('financial-modal');
    setTimeout(() => document.getElementById('fin-name').focus(), 200);
}

function closeFinancialModal() {
    document.getElementById('financial-modal').classList.remove('open');
}

async function saveFinancialAlert() {
    const name = document.getElementById('fin-name').value.trim();
    const dueDay = document.getElementById('fin-due-day').value;
    if (!name) { showToast('El nombre es obligatorio', 'error'); return; }
    if (!dueDay || dueDay < 1 || dueDay > 31) { showToast('Día de vencimiento inválido (1-31)', 'error'); return; }

    const data = {
        name,
        description: document.getElementById('fin-description').value.trim() || null,
        due_day_of_month: parseInt(dueDay),
        alert_days_before: parseInt(document.getElementById('fin-alert-days').value),
        amount: document.getElementById('fin-amount').value.trim() || null,
        category: document.getElementById('fin-category').value,
        currency: document.getElementById('fin-currency').value,
        color: document.getElementById('fin-color').value,
    };

    try {
        await apiFetch('/financial-alerts/', { method: 'POST', body: JSON.stringify(data) });
        showToast(`Alerta "${name}" creada 💳`, 'success');
        closeFinancialModal();
        renderFinancialAlerts();
    } catch (err) { showToast('Error: ' + err.message, 'error'); }
}

async function markAsPaid(alertId) {
    try {
        await apiFetch(`/financial-alerts/${alertId}/mark-paid`, { method: 'POST' });
        showToast('¡Pago registrado! ✅', 'success');
        renderFinancialAlerts();
    } catch (err) { showToast('Error: ' + err.message, 'error'); }
}

async function deleteFinancialAlert(alertId) {
    if (!confirm('¿Eliminar esta alerta financiera?')) return;
    try {
        await apiFetch(`/financial-alerts/${alertId}`, { method: 'DELETE' });
        showToast('Alerta eliminada 🗑️', 'success');
        renderFinancialAlerts();
    } catch (err) { showToast('Error: ' + err.message, 'error'); }
}

async function generateFinancialEvents() {
    try {
        const result = await apiFetch('/financial-alerts/generate-events', { method: 'POST' });
        showToast(`${result.message} 📅`, 'success');
        if (state.currentView === 'calendar') renderCalendar();
    } catch (err) { showToast('Error: ' + err.message, 'error'); }
}

// =============================================================================
// TAGS
// =============================================================================

function toggleTagSelection(tagId, color) {
    if (state.selectedTagIds.has(tagId)) {
        state.selectedTagIds.delete(tagId);
    } else {
        state.selectedTagIds.add(tagId);
    }
    renderTaskTagsInModal();
}

// =============================================================================
// MODALS
// =============================================================================

function openModal(modalId) {
    document.getElementById(modalId).classList.add('open');
}

function closeTaskModal() {
    document.getElementById('task-modal').classList.remove('open');
}

function closeListModal() {
    document.getElementById('list-modal').classList.remove('open');
}

document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) overlay.classList.remove('open');
    });
});

// =============================================================================
// UTILIDADES
// =============================================================================

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDueDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr + 'T00:00:00');
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const diff = Math.ceil((date - today) / (1000 * 60 * 60 * 24));
    if (diff === 0) return 'Hoy';
    if (diff === 1) return 'Mañana';
    if (diff === -1) return 'Ayer';
    if (diff < -1) return `Hace ${Math.abs(diff)} días`;
    if (diff <= 7) return `En ${diff} días`;
    return date.toLocaleDateString('es-PE', { month: 'short', day: 'numeric' });
}

function formatDate(dateStr) {
    if (!dateStr) return '—';
    const d = new Date(dateStr + 'T00:00:00');
    return d.toLocaleDateString('es-PE', { weekday: 'short', day: 'numeric', month: 'short' });
}

function getDueDateClass(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr + 'T00:00:00');
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const diff = Math.ceil((date - today) / (1000 * 60 * 60 * 24));
    if (diff < 0) return 'overdue';
    if (diff === 0) return 'today';
    if (diff <= 3) return 'upcoming';
    return '';
}

function getListInfo(listId) {
    if (!listId) return null;
    return state.lists.find(l => l.id === listId) || null;
}

function getEmptyIcon() {
    const icons = { all: '🎯', today: '☀️', upcoming: '🗓️', completed: '🏆' };
    return icons[state.currentView] || '📋';
}

function getEmptyTitle() {
    const titles = {
        all: 'No hay tareas pendientes',
        today: 'Sin tareas para hoy',
        upcoming: 'Nada para los próximos 7 días',
        completed: 'Sin tareas completadas',
    };
    return titles[state.currentView] || 'Lista vacía';
}

function getEmptyDescription() {
    return 'Crea tu primera tarea con el botón "+ Nueva tarea"';
}

function updateBadges() {
    const today = new Date().toISOString().split('T')[0];
    const active = state.tasks.filter(t => t.status !== 'completed' && t.status !== 'cancelled');
    const todayTasks = active.filter(t => t.due_date === today);
    document.getElementById('badge-all').textContent = active.length;
    document.getElementById('badge-today').textContent = todayTasks.length;
    const urgentFinancial = state.financialAlerts.filter(a => a.days_until_due <= 7);
    document.getElementById('badge-financial').textContent = urgentFinancial.length || '';
}

async function refreshListCounts() {
    try {
        const lists = await apiFetch('/lists/');
        state.lists = lists;
        renderSidebarLists();
    } catch { /* ignore */ }
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icons = { success: '✅', error: '❌', info: 'ℹ️' };
    toast.innerHTML = `<span>${icons[type] || ''}</span> ${message}`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// =============================================================================
// VISTA SWITCHING — Cambio entre vistas
// =============================================================================

function switchView(view, title) {
    state.currentView = view;

    // Actualizar título
    document.getElementById('view-title').textContent = title;

    // Ocultar todos los containers
    const containers = ['task-container', 'calendar-container', 'financial-container', 'dashboard-container', 'git-container'];
    containers.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });

    // Ocultar/mostrar botones de header según vista
    const btnNewTask = document.getElementById('btn-new-task');
    const btnNewEvent = document.getElementById('btn-new-event');
    const btnNewAlert = document.getElementById('btn-new-alert');
    const filterBar = document.getElementById('filter-bar-tasks');

    if (btnNewTask) btnNewTask.style.display = 'none';
    if (btnNewEvent) btnNewEvent.style.display = 'none';
    if (btnNewAlert) btnNewAlert.style.display = 'none';
    if (filterBar) filterBar.style.display = 'none';

    // Actualizar sidebar active
    document.querySelectorAll('.sidebar-item').forEach(btn => btn.classList.remove('active'));
    const activeBtn = document.querySelector(`.sidebar-item[data-view="${view}"]`);
    if (activeBtn) activeBtn.classList.add('active');

    // Mostrar container y botones según vista
    switch (view) {
        case 'all':
        case 'today':
        case 'upcoming':
        case 'completed':
            document.getElementById('task-container').style.display = '';
            if (btnNewTask) btnNewTask.style.display = '';
            if (filterBar) filterBar.style.display = '';
            renderTasks();
            break;
        case 'calendar':
            document.getElementById('calendar-container').style.display = '';
            if (btnNewEvent) btnNewEvent.style.display = '';
            renderCalendarView();
            break;
        case 'financial':
            document.getElementById('financial-container').style.display = '';
            if (btnNewAlert) btnNewAlert.style.display = '';
            renderFinancialAlerts();
            break;
        case 'dashboard':
            document.getElementById('dashboard-container').style.display = '';
            loadDashboard();
            break;
        case 'git':
            document.getElementById('git-container').style.display = '';
            loadGitStatus();
            break;
    }

    // Actualizar conteo del header
    document.getElementById('task-count').textContent =
        view === 'dashboard' ? 'Métricas de productividad' :
            view === 'git' ? 'Estado de repositorios' :
                view === 'calendar' ? 'Vista mensual' :
                    view === 'financial' ? `${state.financialAlerts.length} alertas` :
                        `${state.tasks.length} tareas`;
}

// =============================================================================
// DASHBOARD — Métricas de productividad
// =============================================================================

async function loadDashboard() {
    const container = document.getElementById('dashboard-container');
    container.innerHTML = '<div class="loading-state"><div class="typing-dots"><span></span><span></span><span></span></div><p>Cargando métricas…</p></div>';

    try {
        const [overview, stats, streaks] = await Promise.all([
            apiFetch('/dashboard/overview'),
            apiFetch('/dashboard/task-stats?days=30'),
            apiFetch('/dashboard/streaks'),
        ]);
        renderDashboard(overview, stats, streaks);
    } catch (err) {
        container.innerHTML = `<div class="empty-state"><p>⚠️ Error: ${err.message}</p></div>`;
    }
}

function renderDashboard(overview, stats, streaks) {
    const container = document.getElementById('dashboard-container');
    const t = overview.tasks;

    container.innerHTML = `
        <div class="dashboard-grid">
            <!-- Fila 1: Métricas principales -->
            <div class="dash-card dash-card-accent">
                <div class="dash-card-icon">📋</div>
                <div class="dash-card-value">${t.pending}</div>
                <div class="dash-card-label">Pendientes</div>
            </div>
            <div class="dash-card dash-card-success">
                <div class="dash-card-icon">✅</div>
                <div class="dash-card-value">${t.completed}</div>
                <div class="dash-card-label">Completadas</div>
            </div>
            <div class="dash-card ${t.overdue > 0 ? 'dash-card-danger' : 'dash-card-muted'}">
                <div class="dash-card-icon">⏰</div>
                <div class="dash-card-value">${t.overdue}</div>
                <div class="dash-card-label">Vencidas</div>
            </div>
            <div class="dash-card dash-card-info">
                <div class="dash-card-icon">📊</div>
                <div class="dash-card-value">${t.completion_rate}%</div>
                <div class="dash-card-label">Tasa completado</div>
            </div>
        </div>

        <!-- Fila 2: Rachas y velocidad -->
        <div class="dashboard-grid dashboard-grid-3">
            <div class="dash-panel">
                <h3>🔥 Rachas</h3>
                <div class="dash-streak-row">
                    <div>
                        <span class="dash-streak-number">${streaks.current_streak}</span>
                        <span class="dash-streak-label">días seguidos</span>
                    </div>
                    <div>
                        <span class="dash-streak-number">${streaks.best_streak}</span>
                        <span class="dash-streak-label">mejor racha</span>
                    </div>
                    <div>
                        <span class="dash-streak-number">${streaks.completed_this_week}</span>
                        <span class="dash-streak-label">esta semana</span>
                    </div>
                </div>
            </div>
            <div class="dash-panel">
                <h3>⚡ Velocidad</h3>
                <div class="dash-velocity">
                    <span class="dash-velocity-number">${stats.velocity}</span>
                    <span>tareas/semana</span>
                </div>
                <div class="dash-velocity-detail">
                    ${stats.created} creadas · ${stats.completed} completadas (${stats.period_days} días)
                </div>
            </div>
            <div class="dash-panel">
                <h3>📅 Prioridades</h3>
                <div class="dash-priorities">
                    <div class="dash-priority-row"><span class="priority-dot p1"></span> Urgente <strong>${t.by_priority.urgent}</strong></div>
                    <div class="dash-priority-row"><span class="priority-dot p2"></span> Alta <strong>${t.by_priority.high}</strong></div>
                    <div class="dash-priority-row"><span class="priority-dot p3"></span> Media <strong>${t.by_priority.medium}</strong></div>
                    <div class="dash-priority-row"><span class="priority-dot p4"></span> Baja <strong>${t.by_priority.low}</strong></div>
                </div>
            </div>
        </div>

        <!-- Fila 3: Actividad por día -->
        <div class="dash-panel dash-panel-full">
            <h3>📈 Actividad semanal</h3>
            <div class="dash-chart">
                ${stats.day_activity.map(d => `
                    <div class="dash-bar-col">
                        <div class="dash-bar" style="height: ${Math.max(d.count * 20, 4)}px"></div>
                        <span class="dash-bar-label">${d.day}</span>
                        <span class="dash-bar-value">${d.count}</span>
                    </div>
                `).join('')}
            </div>
        </div>

        <!-- Integraciones -->
        <div class="dash-panel dash-panel-full">
            <h3>🔗 Integraciones</h3>
            <div class="dash-integrations">
                <div class="dash-integration">
                    <span>🤖</span>
                    <div>Sesiones IA: <strong>${overview.ai.total_sessions}</strong></div>
                </div>
                <div class="dash-integration">
                    <span>📅</span>
                    <div>Eventos hoy: <strong>${overview.events.today}</strong></div>
                </div>
                <div class="dash-integration">
                    <span>💰</span>
                    <div>Alertas activas: <strong>${overview.financial.active_alerts}</strong> ${overview.financial.urgent > 0 ? `(⚠️ ${overview.financial.urgent} urgentes)` : ''}</div>
                </div>
            </div>
        </div>
    `;
}

// =============================================================================
// GIT MONITOR — Estado de repositorios
// =============================================================================

async function loadGitStatus() {
    const container = document.getElementById('git-container');
    container.innerHTML = '<div class="loading-state"><div class="typing-dots"><span></span><span></span><span></span></div><p>Escaneando repositorio…</p></div>';

    try {
        const repo = await apiFetch('/integrations/git/scan-current');
        renderGitStatus(repo);
    } catch (err) {
        container.innerHTML = `<div class="empty-state"><p>⚠️ Error: ${err.message}</p></div>`;
    }
}

function renderGitStatus(repo) {
    const container = document.getElementById('git-container');
    const statusClass = repo.status.clean ? 'git-clean' : 'git-dirty';
    const statusText = repo.status.clean ? '✅ Limpio' : '⚠️ Cambios sin commitear';

    container.innerHTML = `
        <div class="git-repo-card">
            <div class="git-repo-header">
                <div class="git-repo-name">
                    <span>📁</span>
                    <h3>${repo.name}</h3>
                    <span class="git-branch-badge">🔀 ${repo.active_branch}</span>
                </div>
                <span class="git-status-badge ${statusClass}">${statusText}</span>
            </div>

            ${!repo.status.clean ? `
            <div class="git-changes-section">
                <h4>📝 Cambios pendientes</h4>
                <div class="git-file-list">
                    ${repo.status.modified.map(f => `<div class="git-file modified">M ${f}</div>`).join('')}
                    ${repo.status.untracked.map(f => `<div class="git-file untracked">+ ${f}</div>`).join('')}
                    ${repo.status.staged.map(f => `<div class="git-file staged">S ${f}</div>`).join('')}
                </div>
            </div>
            ` : ''}

            <div class="git-commits-section">
                <h4>📜 Commits recientes</h4>
                <div class="git-commits-list">
                    ${repo.recent_commits.map(c => `
                        <div class="git-commit">
                            <code class="git-hash">${c.hash}</code>
                            <span class="git-commit-msg">${c.message}</span>
                            <span class="git-commit-date">${new Date(c.date).toLocaleDateString('es-PE')}</span>
                        </div>
                    `).join('')}
                </div>
            </div>

            <div class="git-meta">
                <span>📊 ${repo.weekly_commits} commits esta semana</span>
                <span>🌳 ${repo.branches.length} rama(s)</span>
                ${repo.remotes.map(r => `<span>🔗 ${r.name}: ${r.url}</span>`).join('')}
            </div>
        </div>
    `;
}

function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeTaskModal();
            closeListModal();
            closeEventModal();
            closeFinancialModal();
            // Cerrar chat si está abierto
            const panel = document.getElementById('ai-chat-panel');
            if (panel.classList.contains('open')) toggleChatPanel();
        }
        if (e.ctrlKey && e.key === 'n' && !document.querySelector('.modal-overlay.open')) {
            e.preventDefault();
            if (state.currentView === 'calendar') openNewEventModal();
            else if (state.currentView === 'financial') openNewFinancialAlertModal();
            else openNewTaskModal();
        }
        if (e.ctrlKey && e.key === 'k') {
            e.preventDefault();
            document.getElementById('search-input').focus();
        }
        // Ctrl+I — Abrir asistente IA
        if (e.ctrlKey && e.key === 'i') {
            e.preventDefault();
            toggleChatPanel();
        }
    });
}

function setupResponsive() {
    const mq = window.matchMedia('(max-width: 768px)');
    const menuBtn = document.querySelector('.mobile-menu');
    if (mq.matches && menuBtn) menuBtn.style.display = 'inline-flex';
    mq.addEventListener('change', (e) => {
        if (menuBtn) menuBtn.style.display = e.matches ? 'inline-flex' : 'none';
    });
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
}

// =============================================================================
// ASISTENTE IA — Chat Panel
// =============================================================================

let aiSessionId = null;

function toggleChatPanel() {
    const panel = document.getElementById('ai-chat-panel');
    const fab = document.getElementById('ai-chat-fab');
    panel.classList.toggle('open');
    fab.classList.toggle('hidden');
    if (panel.classList.contains('open')) {
        setTimeout(() => document.getElementById('ai-chat-input').focus(), 300);
    }
}

async function sendAIMessage() {
    const input = document.getElementById('ai-chat-input');
    const message = input.value.trim();
    if (!message) return;

    // Mostrar mensaje del usuario
    appendChatMessage('user', message);
    input.value = '';

    // Mostrar indicador de typing
    const typingEl = showTypingIndicator();

    try {
        const response = await apiFetch('/ai/chat', {
            method: 'POST',
            body: JSON.stringify({
                message,
                session_id: aiSessionId,
            }),
        });

        aiSessionId = response.session_id;
        removeTypingIndicator(typingEl);
        appendChatMessage('assistant', response.response);

        // Si se creó una tarea, refrescar la lista
        if (response.intent === 'create_task') {
            state.tasks = await apiFetch('/tasks/');
            renderTasks();
            updateBadges();
        }
    } catch (err) {
        removeTypingIndicator(typingEl);
        appendChatMessage('assistant', `⚠️ Error de conexión: ${err.message}`);
    }
}

function appendChatMessage(role, content) {
    const container = document.getElementById('ai-chat-messages');
    const div = document.createElement('div');
    div.className = `ai-message ${role}`;

    // Renderizar markdown básico
    const rendered = renderSimpleMarkdown(content);
    div.innerHTML = `<div class="ai-message-content">${rendered}</div>`;

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function renderSimpleMarkdown(text) {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/^## (.+)$/gm, '<h4>$1</h4>')
        .replace(/^### (.+)$/gm, '<h5>$1</h5>')
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
        .replace(/<\/ul>\s*<ul>/g, '')
        .replace(/\n/g, '<br>');
}

function showTypingIndicator() {
    const container = document.getElementById('ai-chat-messages');
    const div = document.createElement('div');
    div.className = 'ai-message assistant ai-typing';
    div.innerHTML = `
        <div class="ai-message-content">
            <div class="typing-dots">
                <span></span><span></span><span></span>
            </div>
        </div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return div;
}

function removeTypingIndicator(el) {
    if (el && el.parentNode) el.remove();
}

