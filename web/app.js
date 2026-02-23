/**
 * ============================================================================
 * BOLLYFLIX ADMIN - ADVANCED SPA ARCHITECTURE
 * ============================================================================
 * Pure Vanilla JS Single Page Application handling routing, dynamic Config
 * Editor parsing, live Log Terminal rendering, User Management, and Stats.
 * ============================================================================
 */

// ----------------------------------------------------------------------------
// STATE & UTILS
// ----------------------------------------------------------------------------

const AppState = {
    userId: null,
    role: null,
    currentTab: 'dashboard',
    users: {
        page: 1,
        limit: 50,
        query: '',
        totalPages: 1
    },
    config: {},
    logs: []
};

// Extracted headers for AIOHTTP REST calls
const getAuthHeaders = () => ({
    'X-User-Id': AppState.userId,
    'Content-Type': 'application/json'
});

const UI = {
    showToast: (message, type = 'success') => {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        let icon = 'info-circle';
        if (type === 'success') icon = 'check-circle';
        if (type === 'error') icon = 'exclamation-triangle';

        toast.innerHTML = `<i class="fa-solid fa-${icon}"></i> <span>${message}</span>`;
        container.appendChild(toast);

        // Trigger animation
        setTimeout(() => toast.classList.add('show'), 10);

        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },

    setServerStatus: (online) => {
        const dot = document.querySelector('.status-dot');
        const text = document.getElementById('server-status');
        if (online) {
            dot.className = 'status-dot online';
            text.textContent = 'Bot Online';
        } else {
            dot.className = 'status-dot offline';
            text.textContent = 'Bot Offline';
        }
    }
};

// ----------------------------------------------------------------------------
// INITIALIZATION
// ----------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Authenticate via URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const userIdRaw = urlParams.get('uid');

    if (!userIdRaw) {
        document.body.innerHTML = `
            <div style="display:flex; height:100vh; align-items:center; justify-content:center; flex-direction:column; background:#f8fafc;">
                <h1 style="color:#0f172a; font-family:Inter">🔒 Access Denied</h1>
                <p style="color:#64748b; font-family:Inter; margin-top:10px;">Missing Authentication Parameter. Please use the /admin_panel command in Telegram.</p>
            </div>
        `;
        return;
    }

    AppState.userId = userIdRaw;
    document.getElementById('current-user-id').textContent = `ID: ${AppState.userId}`;

    // 2. Setup Routing / Tabs
    setupTabs();

    // 3. Load Main Dashboard Data (This validates role internally)
    await loadDashboardStats();

    // 4. Setup Global Event Listeners
    setupGlobalListeners();
});

// ----------------------------------------------------------------------------
// ROUTING & TABS
// ----------------------------------------------------------------------------

function setupTabs() {
    const navItems = document.querySelectorAll('.nav-item');

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const targetTab = item.getAttribute('data-tab');
            if (targetTab === AppState.currentTab) return;

            // Highlight Nav
            navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');

            // Show Tab Pane
            document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
            document.getElementById(`tab-${targetTab}`).classList.add('active');

            // Update Topbar Title
            document.getElementById('active-tab-title').textContent = item.textContent.trim();

            AppState.currentTab = targetTab;

            // Triggers
            if (targetTab === 'dashboard') loadDashboardStats();
            if (targetTab === 'users') loadUsers();
            if (targetTab === 'config') loadConfigEditor();
            if (targetTab === 'logs') loadSystemLogs();
        });
    });
}

// ----------------------------------------------------------------------------
// DASHBOARD STATS
// ----------------------------------------------------------------------------

async function loadDashboardStats() {
    try {
        const response = await fetch('/api/stats', {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            UI.setServerStatus(false);
            if (response.status === 403 || response.status === 401) {
                UI.showToast('Unauthorized Access', 'error');
                return;
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        document.getElementById('stat-total-users').textContent = data.total_users || 0;
        document.getElementById('stat-total-downloads').textContent = data.total_downloads || 0;
        document.getElementById('stat-total-searches').textContent = data.total_searches || 0;
        document.getElementById('stat-active-24h').textContent = data.active_users_24h || 0;

        // Now that we know we have access, let's load role from API or assume from success
        // We'll fetch the actual role silently to restrict UI if needed
        validateRoleSilently();

        UI.setServerStatus(true);
    } catch (err) {
        console.error("Stats Error:", err);
        UI.setServerStatus(false);
        UI.showToast('Failed to load dashboard data.', 'error');
    }
}

async function validateRoleSilently() {
    // The backend /api/users returns role indirectly if we query ourselves,
    // but a cleaner way is verifying permissions when we hit config.
    // We already hide elements using .owner-only in CSS based on a class we add to body.

    try {
        // Ping config just to see if we get 403 (meaning not Owner)
        const res = await fetch('/api/config', { headers: getAuthHeaders() });
        const tbLogs = await fetch('/api/logs', { headers: getAuthHeaders() });

        if (res.ok) {
            AppState.role = 'owner';
            document.getElementById('current-user-role').textContent = 'Owner';
            document.getElementById('current-user-role').style.backgroundColor = 'rgba(16, 185, 129, 0.1)';
            document.getElementById('current-user-role').style.color = 'var(--success)';
            document.body.classList.add('is-owner');
        } else if (tbLogs.ok) {
            AppState.role = 'admin';
            document.getElementById('current-user-role').textContent = 'Admin';
            document.body.classList.add('is-admin');
            document.querySelectorAll('.owner-only').forEach(el => el.style.display = 'none');
        } else {
            AppState.role = 'manager';
            document.getElementById('current-user-role').textContent = 'Manager';
            document.querySelectorAll('.owner-only, .admin-only').forEach(el => el.style.display = 'none');
        }
    } catch (e) {
        // Ignore silent failure
    }
}

// ----------------------------------------------------------------------------
// USERS MANAGEMENT
// ----------------------------------------------------------------------------

async function loadUsers() {
    const tbody = document.getElementById('users-table-body');
    tbody.innerHTML = `<tr><td colspan="6" class="text-center"><i class="fa-solid fa-spinner fa-spin"></i> Loading...</td></tr>`;

    try {
        const response = await fetch(`/api/users?page=${AppState.users.page}&limit=${AppState.users.limit}&query=${encodeURIComponent(AppState.users.query)}`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) throw new Error('Failed to fetch users');

        const data = await response.json();

        tbody.innerHTML = '';

        if (data.users.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted">No users found matching '${AppState.users.query}'</td></tr>`;
        } else {
            data.users.forEach(user => {
                const tr = document.createElement('tr');

                const joined = user.joined_date ? new Date(user.joined_date).toLocaleDateString() : 'Unknown';
                const statusHtml = user.banned
                    ? `<span class="badge role-badge" style="background:#fecaca; color:#ef4444;">Banned</span>`
                    : `<span class="badge role-badge" style="background:#e0e7ff; color:#4f46e5;">Active</span>`;

                const reason = user.ban_reason ? `<br><small class="text-muted"><i class="fa-solid fa-circle-info"></i> ${user.ban_reason}</small>` : '';

                tr.innerHTML = `
                    <td style="font-family:monospace; color:var(--secondary)">${user.user_id}</td>
                    <td><strong>${user.first_name || 'N/A'}</strong> ${user.username ? `<span class="text-muted">(@${user.username})</span>` : ''}</td>
                    <td class="text-muted">${joined}</td>
                    <td>
                        <div style="font-size:0.85rem">
                            <i class="fa-solid fa-download text-muted"></i> ${user.total_downloads || 0} &nbsp;&nbsp; 
                            <i class="fa-solid fa-magnifying-glass text-muted"></i> ${user.total_searches || 0}
                        </div>
                    </td>
                    <td>${statusHtml}${reason}</td>
                    <td>
                        <button class="btn btn-sm btn-outline ban-btn" data-id="${user.user_id}" data-banned="${user.banned ? 'true' : 'false'}">
                            <i class="fa-solid fa-gavel"></i> Manage
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            // Attach event listeners to ban buttons
            document.querySelectorAll('.ban-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const uid = btn.getAttribute('data-id');
                    const isBanned = btn.getAttribute('data-banned') === 'true';
                    openBanModal(uid, isBanned);
                });
            });
        }

        // Pagination logic (if your API supports total_pages, use it. For now, basic implementation)
        const totalPages = data.total_pages || 1;
        document.getElementById('page-info').textContent = `Page ${AppState.users.page} of ${totalPages}`;
        document.getElementById('prev-page').disabled = AppState.users.page <= 1;
        document.getElementById('next-page').disabled = AppState.users.page >= totalPages;

    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">Error loading users.</td></tr>`;
        console.error(err);
    }
}

// User Search Event
let searchTimeout;
document.getElementById('user-search').addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        AppState.users.query = e.target.value;
        AppState.users.page = 1; // Reset to page 1 on search
        loadUsers();
    }, 500); // 500ms debounce
});

// User Pagination Events
document.getElementById('prev-page').addEventListener('click', () => {
    if (AppState.users.page > 1) {
        AppState.users.page--;
        loadUsers();
    }
});
document.getElementById('next-page').addEventListener('click', () => {
    AppState.users.page++;
    loadUsers();
});

// Modals
const banModal = document.getElementById('ban-modal');

function openBanModal(userId, isBanned) {
    document.getElementById('ban-user-id').value = userId;
    const actionSelect = document.getElementById('ban-action');
    const reasonInput = document.getElementById('ban-reason');

    if (isBanned) {
        actionSelect.value = 'unban';
        reasonInput.parentElement.style.display = 'none';
        document.getElementById('confirm-ban-btn').className = 'btn btn-primary';
        document.getElementById('confirm-ban-btn').innerHTML = 'Unban User';
    } else {
        actionSelect.value = 'ban';
        reasonInput.parentElement.style.display = 'block';
        reasonInput.value = '';
        document.getElementById('confirm-ban-btn').className = 'btn btn-danger';
        document.getElementById('confirm-ban-btn').innerHTML = 'Ban User';
    }

    banModal.style.display = 'flex';
}

document.querySelectorAll('.close-modal').forEach(el => {
    el.addEventListener('click', () => {
        banModal.style.display = 'none';
    });
});

document.getElementById('ban-action').addEventListener('change', (e) => {
    const reasonGroup = document.getElementById('ban-reason').parentElement;
    if (e.target.value === 'ban') {
        reasonGroup.style.display = 'block';
        document.getElementById('confirm-ban-btn').className = 'btn btn-danger';
        document.getElementById('confirm-ban-btn').innerHTML = 'Ban User';
    } else {
        reasonGroup.style.display = 'none';
        document.getElementById('confirm-ban-btn').className = 'btn btn-primary';
        document.getElementById('confirm-ban-btn').innerHTML = 'Unban User';
    }
});

document.getElementById('confirm-ban-btn').addEventListener('click', async () => {
    const userId = document.getElementById('ban-user-id').value;
    const action = document.getElementById('ban-action').value;
    const reason = document.getElementById('ban-reason').value;

    const endpoint = action === 'ban' ? '/api/users/ban' : '/api/users/unban';
    const body = action === 'ban' ? { user_id: parseInt(userId), reason: reason } : { user_id: parseInt(userId) };

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(body)
        });

        if (!response.ok) throw new Error('API Execution Failed');

        UI.showToast(`User successfully ${action}ned!`);
        banModal.style.display = 'none';
        loadUsers(); // Refresh
    } catch (err) {
        console.error(err);
        UI.showToast(`Failed to ${action} user.`, 'error');
    }
});

// ----------------------------------------------------------------------------
// CONFIG EDITOR
// ----------------------------------------------------------------------------

async function loadConfigEditor() {
    const form = document.getElementById('config-form');

    try {
        const response = await fetch('/api/config', { headers: getAuthHeaders() });
        if (!response.ok) throw new Error('Failed to load config');

        const config = await response.json();
        AppState.config = config;

        form.innerHTML = ''; // Clear loading

        // Dynamically build inputs avoiding private globals
        Object.entries(config).forEach(([key, value]) => {
            // Determine type
            let inputType = 'text';
            let originalType = 'string';

            if (value === 'True' || value === 'False') {
                originalType = 'boolean';
            } else if (!isNaN(value) && value.trim() !== '' && !value.includes('.')) {
                // simple heuristic for int
                originalType = 'number';
                inputType = 'number';
            } else if (value.startsWith('[') || value.startsWith('(')) {
                originalType = 'list';
            }

            // Build DOM Group
            const group = document.createElement('div');
            group.className = 'form-group';

            const label = document.createElement('label');
            label.textContent = key;

            let input;

            if (originalType === 'boolean') {
                input = document.createElement('select');
                input.className = 'form-control';
                input.innerHTML = `<option value="True">True</option><option value="False">False</option>`;
                input.value = value;
            } else if (originalType === 'list') {
                // Advanced input for arrays (comma separated for UX, but backend expects valid python lists)
                // For safety in this live-editor context, we treat it as raw text and warn the user.
                input = document.createElement('input');
                input.type = 'text';
                input.className = 'form-control';
                input.value = value;

                const note = document.createElement('small');
                note.className = 'text-muted';
                note.style.fontSize = '0.75rem';
                note.textContent = 'Keep exact Python List/Tuple formatting.';
                group.appendChild(note);
            } else {
                input = document.createElement('input');
                input.type = inputType;
                input.className = 'form-control';

                // Strip quotes if any for string
                let cleanVal = value;
                if (cleanVal.startsWith('"') && cleanVal.endsWith('"')) {
                    cleanVal = cleanVal.slice(1, -1);
                } else if (cleanVal.startsWith("'") && cleanVal.endsWith("'")) {
                    cleanVal = cleanVal.slice(1, -1);
                }

                input.value = cleanVal;
            }

            input.id = `cfg_${key}`;
            input.setAttribute('data-key', key);
            input.setAttribute('data-orig-type', originalType);

            // Check if sensitive (Token, Hash)
            if (key.includes('TOKEN') || key.includes('HASH')) {
                input.type = 'password';
                input.addEventListener('focus', () => input.type = 'text');
                input.addEventListener('blur', () => input.type = 'password');
            }

            group.insertBefore(label, group.firstChild);
            if (!group.contains(input)) {
                group.appendChild(input);
            }

            form.appendChild(group);
        });

    } catch (err) {
        form.innerHTML = `<div class="text-center text-danger" style="grid-column: 1/-1;">Error loading config: ${err.message}</div>`;
        console.error(err);
    }
}

document.getElementById('save-config-btn').addEventListener('click', async () => {
    const btn = document.getElementById('save-config-btn');
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Saving...`;
    btn.disabled = true;

    const updates = {};
    const inputs = document.querySelectorAll('#config-form .form-control');

    inputs.forEach(input => {
        const key = input.getAttribute('data-key');
        const origType = input.getAttribute('data-orig-type');
        let val = input.value;

        if (origType === 'boolean') {
            // Keep as string 'True' / 'False' for Python parser
            updates[key] = val;
        } else if (origType === 'number') {
            updates[key] = val;
        } else if (origType === 'list') {
            updates[key] = val; // Assuming user wrote it as "[123, 456]"
        } else {
            updates[key] = val; // String. config_manager.py handles quoting
        }
    });

    try {
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(updates)
        });

        if (!response.ok) throw new Error('Failed to save config');

        UI.showToast('Configuration successfully deployed!', 'success');

    } catch (err) {
        UI.showToast(err.message, 'error');
        console.error(err);
    } finally {
        btn.innerHTML = `<i class="fa-solid fa-save"></i> Deploy Changes`;
        btn.disabled = false;
    }
});

// ----------------------------------------------------------------------------
// SYSTEM LOGS
// ----------------------------------------------------------------------------

async function loadSystemLogs() {
    const container = document.getElementById('logs-container');
    container.innerHTML = `<div class="log-line">Fetching system logs...</div>`;

    try {
        const response = await fetch('/api/logs', { headers: getAuthHeaders() });
        if (!response.ok) throw new Error('Failed to completely load logs');

        const data = await response.json();

        if (data.logs && data.logs.length > 0) {
            container.innerHTML = '';
            data.logs.forEach(line => {
                const div = document.createElement('div');
                div.className = 'log-line';
                // HTML Escaping to prevent XSS from logs
                const escaped = line.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

                // Colorize common log levels
                let formatted = escaped;
                if (escaped.includes('INFO') || escaped.includes('✅')) formatted = `<span style="color:#27c93f">${escaped}</span>`;
                if (escaped.includes('WARNING') || escaped.includes('⚠️')) formatted = `<span style="color:#ffbd2e">${escaped}</span>`;
                if (escaped.includes('ERROR') || escaped.includes('❌') || escaped.includes('Traceback')) formatted = `<span style="color:#ff5f56">${escaped}</span>`;

                div.innerHTML = formatted;
                container.appendChild(div);
            });
            // Auto scroll to bottom
            container.scrollTop = container.scrollHeight;
        } else {
            container.innerHTML = `<div class="log-line">No logs available at this time.</div>`;
        }

    } catch (err) {
        container.innerHTML = `<div class="log-line" style="color:#ff5f56">Error fetching logs: ${err.message}</div>`;
        console.error(err);
    }
}

document.getElementById('refresh-logs-btn').addEventListener('click', loadSystemLogs);

// ----------------------------------------------------------------------------
// GLOBAL LISTENERS
// ----------------------------------------------------------------------------

function setupGlobalListeners() {
    document.getElementById('refresh-btn').addEventListener('click', () => {
        if (AppState.currentTab === 'dashboard') loadDashboardStats();
        if (AppState.currentTab === 'users') loadUsers();
        if (AppState.currentTab === 'config') loadConfigEditor();
        if (AppState.currentTab === 'logs') loadSystemLogs();

        UI.showToast('Data refreshed.', 'info');
    });
}
