const state = { sources: [], sinks: [], zones: [], routes: [], devices: [] };

const sourcesEl = document.getElementById("sources");
const destinationsEl = document.getElementById("destinations");
const routesEl = document.getElementById("routes");
const routeBtn = document.getElementById("route-btn");
const routeErrorEl = document.getElementById("route-error");
const connStatusEl = document.getElementById("conn-status");

function deviceName(deviceId) {
  const device = state.devices.find((d) => d.id === deviceId);
  return device ? device.name : deviceId;
}

function selectedSourceId() {
  const checked = sourcesEl.querySelector("input[name=source]:checked");
  return checked ? checked.value : null;
}

function selectedDestinations() {
  const zoneIds = [...destinationsEl.querySelectorAll("input[data-kind=zone]:checked")].map(
    (el) => el.value
  );
  const sinkIds = [...destinationsEl.querySelectorAll("input[data-kind=sink]:checked")].map(
    (el) => el.value
  );
  return { zoneIds, sinkIds };
}

function render() {
  // Sources
  sourcesEl.innerHTML = "";
  if (state.sources.length === 0) {
    sourcesEl.innerHTML = '<p class="empty">No sources registered yet. Start an agent.</p>';
  }
  for (const source of state.sources) {
    const row = document.createElement("div");
    row.className = "row";
    row.innerHTML = `
      <input type="radio" name="source" value="${source.id}" id="src-${source.id}">
      <label for="src-${source.id}">${source.name}</label>
      <span class="meta">${deviceName(source.device_id)}</span>
    `;
    sourcesEl.appendChild(row);
  }
  const previouslySelected = selectedSourceId();
  if (previouslySelected) {
    const el = sourcesEl.querySelector(`input[value="${previouslySelected}"]`);
    if (el) el.checked = true;
  }

  // Destinations: zones first, then sinks with no zone
  destinationsEl.innerHTML = "";
  if (state.zones.length === 0 && state.sinks.length === 0) {
    destinationsEl.innerHTML = '<p class="empty">No zones or sinks registered yet.</p>';
  }
  for (const zone of state.zones) {
    const row = document.createElement("div");
    row.className = "row";
    row.innerHTML = `
      <input type="checkbox" data-kind="zone" value="${zone.id}" id="zone-${zone.id}">
      <label for="zone-${zone.id}">${zone.name}</label>
      <span class="meta">${zone.sink_ids.length} sink(s)</span>
    `;
    destinationsEl.appendChild(row);
  }
  const unzoned = state.sinks.filter((s) => !s.zone_id);
  for (const sink of unzoned) {
    const row = document.createElement("div");
    row.className = "row";
    row.innerHTML = `
      <input type="checkbox" data-kind="sink" value="${sink.id}" id="sink-${sink.id}">
      <label for="sink-${sink.id}">${sink.name}</label>
      <span class="meta">${deviceName(sink.device_id)}</span>
    `;
    destinationsEl.appendChild(row);
  }

  routeBtn.disabled = state.sources.length === 0 || (state.zones.length === 0 && state.sinks.length === 0);

  // Routes
  routesEl.innerHTML = "";
  const active = state.routes.filter((r) => r.status !== "stopped");
  if (active.length === 0) {
    routesEl.innerHTML = '<p class="empty">No active routes.</p>';
  }
  for (const route of active) {
    const source = state.sources.find((s) => s.id === route.source_id);
    const sinkNames = route.sink_ids
      .map((id) => state.sinks.find((s) => s.id === id)?.name || id)
      .join(", ");
    const card = document.createElement("div");
    card.className = "route-card";
    card.innerHTML = `
      <div>
        <strong>${source ? source.name : route.source_id}</strong>
        &rarr; ${sinkNames}
        <div class="status ${route.status}">${route.status}${route.error ? ": " + route.error : ""}</div>
      </div>
      <button data-route-id="${route.id}">Stop</button>
    `;
    card.querySelector("button").addEventListener("click", () => stopRoute(route.id));
    routesEl.appendChild(card);
  }
}

async function refreshState() {
  const res = await fetch("/api/state");
  Object.assign(state, await res.json());
  render();
}

async function createRoute() {
  routeErrorEl.textContent = "";
  const sourceId = selectedSourceId();
  if (!sourceId) return;
  const { zoneIds, sinkIds } = selectedDestinations();
  const res = await fetch("/api/routes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_id: sourceId, zone_ids: zoneIds, sink_ids: sinkIds }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    routeErrorEl.textContent = body.detail || `Request failed (${res.status})`;
  }
}

async function stopRoute(routeId) {
  await fetch(`/api/routes/${routeId}`, { method: "DELETE" });
}

routeBtn.addEventListener("click", createRoute);

function connectWebSocket() {
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(`${protocol}//${location.host}/ws`);

  ws.onopen = () => {
    connStatusEl.textContent = "connected";
    connStatusEl.className = "badge connected";
  };
  ws.onclose = () => {
    connStatusEl.textContent = "disconnected";
    connStatusEl.className = "badge disconnected";
    setTimeout(connectWebSocket, 2000);
  };
  ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.type === "state") {
      Object.assign(state, message.data);
      render();
    }
  };
}

refreshState();
connectWebSocket();
