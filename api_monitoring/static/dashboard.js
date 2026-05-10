let currentMinutes = 60;
let latencyChart, errorChart;
const PALETTE = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4'];

document.addEventListener("DOMContentLoaded", () => {
    initCharts();
    
    document.getElementById("btnRefresh").addEventListener("click", refreshAll);
    document.getElementById("serviceFilter").addEventListener("change", () => {
        fetchEndpoints().then(refreshAll);
    });
    document.getElementById("endpointFilter").addEventListener("change", refreshAll);
    
    document.querySelectorAll("#timeFilters button").forEach(btn => {
        btn.addEventListener("click", (e) => {
            document.querySelectorAll("#timeFilters button").forEach(b => b.classList.remove("active"));
            e.target.classList.add("active");
            currentMinutes = parseInt(e.target.dataset.minutes);
            refreshAll();
        });
    });
    
    document.getElementById("addRuleForm").addEventListener("submit", (e) => {
        e.preventDefault();
        submitNewRule();
    });

    fetchServices().then(() => fetchEndpoints()).then(refreshAll);
    setInterval(refreshAll, 15000);
});

function initCharts() {
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.borderColor = '#334155';
    
    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'top' } },
        scales: {
            x: { grid: { display: false } },
            y: { beginAtZero: true }
        },
        interaction: { intersect: false, mode: 'index' }
    };

    latencyChart = new Chart(document.getElementById('latencyChart'), {
        type: 'line',
        data: { labels: [], datasets: [] },
        options: {
            ...commonOptions,
            plugins: { ...commonOptions.plugins, tooltip: { callbacks: { label: (c) => c.dataset.label + ': ' + c.raw.toFixed(1) + 'ms' } } }
        }
    });

    errorChart = new Chart(document.getElementById('errorChart'), {
        type: 'line',
        data: { labels: [], datasets: [] },
        options: {
            ...commonOptions
        }
    });
}

async function refreshAll() {
    const service = document.getElementById("serviceFilter").value;
    const endpoint = document.getElementById("endpointFilter").value;
    
    await Promise.all([
        fetchStats(service, endpoint, currentMinutes),
        fetchTimeSeries(service, endpoint, currentMinutes),
        fetchAlertEvents(),
        fetchAlertRules()
    ]);
    
    document.getElementById("lastUpdated").innerText = `Last updated: Just now`;
}

async function fetchServices() {
    try {
        const res = await fetch('/metrics/services');
        const data = await res.json();
        const select = document.getElementById("serviceFilter");
        select.innerHTML = '<option value="">All Services</option>';
        data.services.forEach(s => {
            select.innerHTML += `<option value="${s}">${s}</option>`;
        });
    } catch (e) { console.error("fetchServices error:", e); }
}

async function fetchEndpoints() {
    try {
        const service = document.getElementById("serviceFilter").value;
        let url = '/metrics/endpoints';
        if (service) url += `?service_name=${service}`;
        const res = await fetch(url);
        const data = await res.json();
        const select = document.getElementById("endpointFilter");
        const currentValue = select.value;
        
        select.innerHTML = '<option value="">All Endpoints</option>';
        data.endpoints.forEach(e => {
            select.innerHTML += `<option value="${e}">${e}</option>`;
        });
        
        if (data.endpoints.includes(currentValue)) {
            select.value = currentValue;
        }
    } catch (e) { console.error("fetchEndpoints error:", e); }
}

async function fetchStats(service, endpoint, minutes) {
    try {
        let url = `/metrics/stats?minutes=${minutes}`;
        if (service) url += `&service_name=${service}`;
        if (endpoint) url += `&endpoint=${endpoint}`;
        const res = await fetch(url);
        const stats = await res.json();
        
        document.getElementById("stat-total").innerText = stats.total_requests;
        
        const lat = document.getElementById("stat-latency");
        lat.innerText = stats.avg_response_time_ms.toFixed(1);
        lat.style.color = stats.avg_response_time_ms > 500 ? 'var(--danger)' : (stats.avg_response_time_ms > 200 ? 'var(--warning)' : 'var(--success)');
        
        const err = document.getElementById("stat-error");
        err.innerText = stats.error_rate_percent.toFixed(2) + '%';
        err.style.color = stats.error_rate_percent > 5 ? 'var(--danger)' : (stats.error_rate_percent > 1 ? 'var(--warning)' : 'var(--success)');
        
        document.getElementById("stat-rps").innerText = stats.requests_per_minute.toFixed(1);
    } catch (e) { console.error(e); }
}

async function fetchTimeSeries(service, endpoint, minutes) {
    try {
        let url = `/metrics/timeseries?minutes=${minutes}&bucket_minutes=${minutes <= 15 ? 1 : 5}`;
        if (service) url += `&service_name=${service}`;
        if (endpoint) url += `&endpoint=${endpoint}`;
        const res = await fetch(url);
        const data = await res.json();
        
        const labels = data.map(d => {
            const date = new Date(d.bucket_start);
            return `${date.getHours().toString().padStart(2,'0')}:${date.getMinutes().toString().padStart(2,'0')}`;
        });
        
        latencyChart.data.labels = labels;
        latencyChart.data.datasets = [{
            label: service || 'All Services Avg',
            data: data.map(d => d.avg_latency),
            borderColor: PALETTE[0],
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            fill: true,
            tension: 0.4
        }];
        latencyChart.update();
        
        errorChart.data.labels = labels;
        errorChart.data.datasets = [{
            label: 'Error Rate (%)',
            data: data.map(d => d.error_rate),
            borderColor: 'var(--danger)',
            backgroundColor: 'rgba(239, 68, 68, 0.2)',
            fill: true,
            tension: 0.4
        }];
        errorChart.update();
        
        updateHealthTable(data);
    } catch (e) { console.error(e); }
}

function updateHealthTable(tsData) {
    const tbody = document.querySelector("#healthTable tbody");
    if (tsData.length === 0) return;
    
    const currentService = document.getElementById("serviceFilter").value || "All Services";
    const lastBucket = tsData[tsData.length - 1];
    
    // Check if the last bucket had any traffic (simple heuristic)
    const isHealthy = lastBucket && lastBucket.request_count > 0;
    const nowStr = new Date().toLocaleTimeString();
    
    tbody.innerHTML = `
        <tr>
            <td>${currentService}</td>
            <td>${nowStr}</td>
            <td><div class="status-dot ${isHealthy ? 'healthy' : 'unhealthy'}"></div> ${isHealthy ? 'Live' : 'No Traffic Recently'}</td>
        </tr>
    `;
}

async function fetchAlertEvents() {
    try {
        const res = await fetch('/alerts/events?limit=10');
        const data = await res.json();
        const tbody = document.querySelector("#alertsEventTable tbody");
        tbody.innerHTML = '';
        
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center">No alerts found.</td></tr>';
            return;
        }
        
        data.forEach(e => {
            const dateStr = new Date(e.triggered_at * 1000).toLocaleString();
            const tr = document.createElement('tr');
            if (!e.resolved) tr.className = 'row-unresolved';
            else tr.className = 'row-resolved';
            
            tr.innerHTML = `
                <td>${dateStr}</td>
                <td><strong>${e.rule_name}</strong></td>
                <td>${e.service_name || 'All'}</td>
                <td>${e.metric_value.toFixed(2)}</td>
                <td>${e.message}</td>
                <td><span class="badge ${e.resolved ? 'badge-success' : 'badge-danger'}">${e.resolved ? 'Resolved' : 'Active'}</span></td>
                <td>
                    ${!e.resolved ? `<button class="btn-primary" onclick="resolveAlert(${e.id})" style="padding: 4px 8px; font-size: 11px;">Resolve</button>` : '-'}
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) { console.error(e); }
}

async function fetchAlertRules() {
    try {
        const res = await fetch('/alerts');
        const data = await res.json();
        const tbody = document.querySelector("#alertRulesTable tbody");
        tbody.innerHTML = '';
        
        data.forEach(r => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${r.rule_name}</strong></td>
                <td>${r.service_name || 'All'}</td>
                <td>${r.metric_type}</td>
                <td>${r.condition === 'gt' ? '>' : '<'}</td>
                <td>${r.threshold}</td>
                <td>${r.time_window_minutes}m</td>
                <td><span class="badge ${r.is_active ? 'badge-success' : 'badge-warning'}">${r.is_active ? 'Active' : 'Inactive'}</span></td>
                <td>
                    ${r.is_active ? `<button class="btn-danger" onclick="deactivateRule(${r.id})" style="padding: 4px 8px; font-size: 11px;">Disable</button>` : '-'}
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) { console.error(e); }
}

async function resolveAlert(eventId) {
    try {
        await fetch(`/alerts/events/${eventId}/resolve`, { method: 'POST' });
        refreshAll();
    } catch (e) { console.error(e); }
}

async function deactivateRule(ruleId) {
    try {
        await fetch(`/alerts/${ruleId}`, { method: 'DELETE' });
        refreshAll();
    } catch (e) { console.error(e); }
}

async function submitNewRule() {
    const payload = {
        rule_name: document.getElementById('ruleName').value,
        service_name: document.getElementById('ruleService').value || null,
        metric_type: document.getElementById('ruleMetric').value,
        condition: document.getElementById('ruleCondition').value,
        threshold: parseFloat(document.getElementById('ruleThreshold').value),
        time_window_minutes: parseInt(document.getElementById('ruleWindow').value)
    };
    
    try {
        await fetch('/alerts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        document.getElementById("addRuleForm").reset();
        refreshAll();
    } catch (e) { console.error(e); }
}
