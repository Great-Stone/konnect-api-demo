const state = {
  currentScene: "traffic-routing-header",
  region: "east",
  mode: "anonymous",
  consumer: "consumer-standard",
  identityConsumer: "consumer-1",
  identityToken: "",
  resilienceScenario: "weighted-load-balancing",
  links: { logs: "#", audit: "#" },
  scenes: {},
  lastRun: null,
  countdownTimer: null,
  countdownEndsAtMs: null,
  resilienceInstances: {},
};

const SCENE_DEFAULTS = {
  "traffic-routing-header": {
    controlTitle: "Request Builder",
    emptyText: "Run the scene to see the Kong request path, route match, backend selection, and response.",
  },
  "traffic-control-rate-limiting": {
    controlTitle: "Traffic Policy Builder",
    emptyText: "Run the scene to see the Kong rate-limiting policy, per-request decisions, and 429 enforcement point.",
  },
  "resilience-failover-health-checks": {
    controlTitle: "Resilience Controls",
    emptyText: "Run the scene to see weighted distribution, target health state, failover, and recovery through Kong.",
  },
  "identity-azure-token-validation": {
    controlTitle: "Identity Controls",
    emptyText: "Generate an Azure AD token, edit it if needed, decode it, and send it through Kong for validation.",
  },
  "identity-keycloak-authorization": {
    controlTitle: "Identity Controls",
    emptyText: "Generate a Keycloak token for the selected consumer, decode it, and send it through Kong for authorization.",
  },
};

const elements = {
  sceneSelect: document.getElementById("sceneSelect"),
  sceneTitle: document.getElementById("sceneTitle"),
  controlPanelTitle: document.getElementById("controlPanelTitle"),
  runScenarioButton: document.getElementById("runScenarioButton"),
  resetSceneButton: document.getElementById("resetSceneButton"),
  resetPanelButton: document.getElementById("resetPanelButton"),
  viewArchitectureButton: document.getElementById("viewArchitectureButton"),
  viewLogsButton: document.getElementById("viewLogsButton"),
  viewAuditButton: document.getElementById("viewAuditButton"),
  viewSceneDetailsButton: document.getElementById("viewSceneDetailsButton"),
  consoleDetailButton: document.getElementById("consoleDetailButton"),
  architectureModal: document.getElementById("architectureModal"),
  closeArchitectureButton: document.getElementById("closeArchitectureButton"),
  sceneDetailsModal: document.getElementById("sceneDetailsModal"),
  closeSceneDetailsButton: document.getElementById("closeSceneDetailsButton"),
  sceneDetailsContent: document.getElementById("sceneDetailsContent"),
  detailViewModal: document.getElementById("detailViewModal"),
  closeDetailViewButton: document.getElementById("closeDetailViewButton"),
  detailMeta: document.getElementById("detailMeta"),
  detailCurl: document.getElementById("detailCurl"),
  detailResponse: document.getElementById("detailResponse"),
  requestPreviewGrid: document.getElementById("requestPreviewGrid"),
  expectedOutcome: document.getElementById("expectedOutcome"),
  consoleOutput: document.getElementById("consoleOutput"),
  statusKong: document.getElementById("statusKong"),
  statusRoute: document.getElementById("statusRoute"),
  headerRoutingControls: document.getElementById("headerRoutingControls"),
  rateModeControls: document.getElementById("rateModeControls"),
  rateConsumerControls: document.getElementById("rateConsumerControls"),
  rateCounterControls: document.getElementById("rateCounterControls"),
  resilienceScenarioControls: document.getElementById("resilienceScenarioControls"),
  resilienceInstanceControls: document.getElementById("resilienceInstanceControls"),
  identityConsumerControls: document.getElementById("identityConsumerControls"),
  identityTokenControls: document.getElementById("identityTokenControls"),
  identityJwtControls: document.getElementById("identityJwtControls"),
  tokenEditor: document.getElementById("tokenEditor"),
  generateTokenButton: document.getElementById("generateTokenButton"),
  decodeTokenButton: document.getElementById("decodeTokenButton"),
  decodedJwtOutput: document.getElementById("decodedJwtOutput"),
  instance1Status: document.getElementById("instance1Status"),
  instance2Status: document.getElementById("instance2Status"),
  clientNodeLabel: document.getElementById("clientNodeLabel"),
  clientNodeTitle: document.getElementById("clientNodeTitle"),
  clientNodeSubtitle: document.getElementById("clientNodeSubtitle"),
  kongNodeLabel: document.getElementById("kongNodeLabel"),
  kongNodeTitle: document.getElementById("kongNodeTitle"),
  kongNodeSubtitle: document.getElementById("kongNodeSubtitle"),
  eastNodeLabel: document.getElementById("eastNodeLabel"),
  eastNodeTitle: document.getElementById("eastNodeTitle"),
  eastNodeSubtitle: document.getElementById("eastNodeSubtitle"),
  westNodeLabel: document.getElementById("westNodeLabel"),
  westNodeTitle: document.getElementById("westNodeTitle"),
  westNodeSubtitle: document.getElementById("westNodeSubtitle"),
};

const regionButtons = Array.from(document.querySelectorAll("[data-region]"));
const modeButtons = Array.from(document.querySelectorAll("[data-mode]"));
const consumerButtons = Array.from(document.querySelectorAll("[data-consumer]"));
const identityConsumerButtons = Array.from(document.querySelectorAll("[data-identity-consumer]"));
const resilienceScenarioButtons = Array.from(document.querySelectorAll("[data-resilience-scenario]"));
const instanceActionButtons = Array.from(document.querySelectorAll("[data-instance-action]"));
const nodes = {
  kong: document.querySelector('[data-node="kong"]'),
  east: document.querySelector('[data-node="east"]'),
  west: document.querySelector('[data-node="west"]'),
};

const connectors = {
  clientKong: document.querySelector('[data-connector="client-kong"]'),
  kongEast: document.querySelector('[data-connector="kong-east"]'),
  kongWest: document.querySelector('[data-connector="kong-west"]'),
};

function currentSceneDetails() {
  return state.scenes[state.currentScene] || { title: "Scene", services: [], routes: [], plugins: [] };
}

function setActiveButton(buttons, key, value) {
  for (const button of buttons) {
    button.classList.toggle("active", button.dataset[key] === value);
  }
}

function renderRows(container, rows) {
  container.innerHTML = rows
    .map(
      ([label, value]) => `
        <div class="preview-row">
          <span>${label}</span>
          <strong>${value}</strong>
        </div>
      `,
    )
    .join("");
}

function computePreviewRows() {
  if (state.currentScene === "traffic-control-rate-limiting") {
    return [
      ["Method", "GET"],
      ["Path", state.mode === "anonymous" ? "/orders/rate/anonymous" : "/orders/rate/consumer"],
      ["Mode", state.mode],
      ["Consumer", state.mode === "consumer" ? state.consumer : "none"],
      ["Window", "30-second fixed"],
    ];
  }
  if (state.currentScene === "resilience-failover-health-checks") {
    return [
      ["Method", "GET"],
      [
        "Path",
        state.resilienceScenario === "weighted-load-balancing"
          ? "/orders/resilience/weighted"
          : "/orders/resilience/circuit-breaker",
      ],
      [
        "Scenario",
        state.resilienceScenario === "weighted-load-balancing" ? "Weighted Load Balancing" : "Circuit Breaker",
      ],
      [
        "Strategy",
        state.resilienceScenario === "weighted-load-balancing"
          ? "30:70 weighted"
          : "Round robin with active + passive health checks",
      ],
    ];
  }
  if (state.currentScene === "identity-azure-token-validation") {
    return [
      ["Method", "GET"],
      ["Path", "/orders/auth/azure"],
      ["Identity Provider", "Azure AD"],
      ["Consumer", state.identityConsumer],
      ["Audience", "Protected API token validation"],
    ];
  }
  if (state.currentScene === "identity-keycloak-authorization") {
    return [
      ["Method", "GET"],
      ["Path", "/orders/auth/keycloak"],
      ["Identity Provider", "Keycloak"],
      ["Consumer", state.identityConsumer],
    ];
  }
  return [
    ["Method", "GET"],
    ["Path", "/orders"],
    ["Header", state.region === "missing" ? "x-region: <missing>" : `x-region: ${state.region}`],
  ];
}

function computeExpectedOutcome() {
  if (state.currentScene === "traffic-control-rate-limiting") {
    if (state.mode === "anonymous") {
      return "Anonymous requests should pass for requests 1-20 in each 30-second fixed window. Request 21 should return 429.";
    }
    return state.consumer === "consumer-gold"
      ? "consumer-gold should pass for requests 1-10 in each 30-second fixed window. Request 11 should return 429."
      : "consumer-standard should pass for requests 1-5 in each 30-second fixed window. Request 6 should return 429.";
  }
  if (state.currentScene === "resilience-failover-health-checks") {
    return state.resilienceScenario === "weighted-load-balancing"
      ? "Kong should distribute traffic across both healthy targets using the configured 30:70 weights."
      : "Kong should round robin across both healthy targets, then remove an unhealthy target from rotation and fail over to the remaining target.";
  }
  if (state.currentScene === "identity-azure-token-validation") {
    return "Kong should validate the Azure AD bearer token and only forward valid requests to the protected API.";
  }
  if (state.currentScene === "identity-keycloak-authorization") {
    return state.identityConsumer === "consumer-1"
      ? "consumer-1 should be authorized because its service account token contains the required role."
      : "consumer-2 should be denied because its service account token does not contain the required role.";
  }
  if (state.region === "missing") {
    return "Kong should apply the catch-all policy route and return a guided missing-header response.";
  }
  return state.region === "east"
    ? "Orders East should receive the request."
    : "Orders West should receive the request.";
}

function defaultTopologyForScene() {
  if (state.currentScene === "traffic-control-rate-limiting") {
    return {
      labels: {
        client: ["Client", "API Caller", `Mode: ${state.mode}`],
        kong: ["Gateway", "Kong Data Plane", "Rate-limiting enforcement"],
        east: ["Backend", "Orders API", "Allowed: pending"],
        west: ["Policy Window", "Fixed Window Counter", "Request pending"],
      },
      nodes: {
        west: "static",
      },
      connectors: {
        kongWest: "hidden",
      },
    };
  }
  if (state.currentScene === "resilience-failover-health-checks") {
    const instance1Running = state.resilienceInstances["instance-1"]?.running ?? true;
    const instance2Running = state.resilienceInstances["instance-2"]?.running ?? true;
    return {
      labels: {
        client: ["Client", "API Caller", "GET resilience route"],
        kong: [
          "Gateway",
          "Kong Data Plane",
          state.resilienceScenario === "weighted-load-balancing" ? "30:70 weighted" : "Round robin + health checks",
        ],
        east: ["Target", "Service Instance 1", instance1Running ? "Healthy" : "Unhealthy"],
        west: ["Target", "Service Instance 2", instance2Running ? "Healthy" : "Unhealthy"],
      },
      nodes: {
        east: instance1Running ? null : "error",
        west: instance2Running ? null : "error",
      },
    };
  }
  if (state.currentScene === "identity-azure-token-validation") {
    return {
      labels: {
        client: ["Client", "Token Caller", "Bearer token supplied"],
        kong: ["Gateway", "Kong Data Plane", "openid-connect validation"],
        east: ["Protected API", "Orders API", "Awaiting validated request"],
        west: ["Identity Provider", "Azure AD", "Awaiting validation"],
      },
    };
  }
  if (state.currentScene === "identity-keycloak-authorization") {
    return {
      labels: {
        client: ["Client", state.identityConsumer, "Bearer token supplied"],
        kong: ["Gateway", "Kong Data Plane", "openid-connect + roles"],
        east: ["Protected API", "Orders API", "Awaiting authorization"],
        west: ["Identity Provider", "Keycloak", "Awaiting validation"],
      },
    };
  }
  return {
    labels: {
      client: ["Client", "Web Caller", "GET /orders"],
      kong: ["Gateway", "Kong Data Plane", "Header routing policy"],
      east: ["Upstream", "Orders East", "x-region: east"],
      west: ["Upstream", "Orders West", "x-region: west"],
    },
  };
}

function updateStaticPreview() {
  renderRows(elements.requestPreviewGrid, computePreviewRows());
  elements.expectedOutcome.textContent = computeExpectedOutcome();
}

function resetTopology() {
  for (const node of Object.values(nodes)) {
    node.classList.remove("active", "error", "static");
  }
  for (const connector of Object.values(connectors)) {
    connector.classList.remove("active", "error", "hidden");
  }
}

function stopCountdown() {
  if (state.countdownTimer) {
    clearInterval(state.countdownTimer);
    state.countdownTimer = null;
  }
  state.countdownEndsAtMs = null;
}

function resetView() {
  stopCountdown();
  state.lastRun = null;
  elements.consoleDetailButton.disabled = true;
  elements.consoleOutput.innerHTML = `
    <div class="console-empty console-empty-wide">
      <p>${SCENE_DEFAULTS[state.currentScene].emptyText}</p>
    </div>
  `;
  elements.statusKong.className = "status-pill neutral";
  elements.statusKong.textContent = "Kong Waiting";
  elements.statusRoute.className = "status-pill neutral";
  elements.statusRoute.textContent = "Route Pending";
  resetTopology();
  renderTopology({ ...defaultTopologyForScene(), statusKong: "Kong Waiting", statusKongClass: "neutral", statusRoute: "Route Pending", statusRouteClass: "neutral" });
  updateStaticPreview();
}

function stringifyPayload(value) {
  if (value == null || value === "") {
    return "None";
  }
  if (typeof value === "string") {
    return value;
  }
  return JSON.stringify(value, null, 2);
}

function formatHeaders(headers) {
  const entries = Object.entries(headers || {});
  if (!entries.length) {
    return "None";
  }
  return entries
    .map(([key, value]) => `${key}: ${value}`)
    .join("\n");
}

function renderConsolePane(title, statusMarkup, sections) {
  return `
    <section class="console-pane">
      <div class="console-pane-header">
        <strong>${title}</strong>
        ${statusMarkup || ""}
      </div>
      <div class="console-pane-body">
        ${sections
          .map(
            ([label, value, className = ""]) => `
              <div class="console-section">
                <span class="console-section-label">${label}</span>
                <pre class="console-code ${className}">${value}</pre>
              </div>
            `,
          )
          .join("")}
      </div>
    </section>
  `;
}

function renderConsole(consoleView) {
  const request = consoleView.request || {};
  const response = consoleView.response || {};
  const requestSummary = `${request.method || "GET"} ${request.endpoint || "/"}`;
  const responseStatus = response.status != null ? `HTTP ${response.status}` : "";
  const responseStatusClass = response.status >= 400 ? "error" : "success";

  elements.consoleOutput.innerHTML = `
    <div class="console-split">
      ${renderConsolePane("Request", "", [
        ["Method", request.method || "GET"],
        ["Endpoint", request.endpoint || "/"],
        ["Headers", formatHeaders(request.headers)],
        ["Body", stringifyPayload(request.body)],
      ])}
      ${renderConsolePane(
        "Response",
        `<span class="console-status ${responseStatusClass}">${responseStatus}</span>`,
        [
          ["Summary", requestSummary],
          ["Headers", formatHeaders(response.headers)],
          ["Body", stringifyPayload(response.body)],
        ],
      )}
    </div>
  `;
}

function renderTopology(topology) {
  resetTopology();
  const labels = topology.labels || {};
  const labelTargets = {
    client: ["clientNodeLabel", "clientNodeTitle", "clientNodeSubtitle"],
    kong: ["kongNodeLabel", "kongNodeTitle", "kongNodeSubtitle"],
    east: ["eastNodeLabel", "eastNodeTitle", "eastNodeSubtitle"],
    west: ["westNodeLabel", "westNodeTitle", "westNodeSubtitle"],
  };

  for (const [key, values] of Object.entries(labels)) {
    const [labelId, titleId, subtitleId] = labelTargets[key];
    elements[labelId].textContent = values[0];
    elements[titleId].textContent = values[1];
    elements[subtitleId].textContent = values[2];
  }

  for (const [name, stateValue] of Object.entries(topology.nodes || {})) {
    if (stateValue === "active") {
      nodes[name].classList.add("active");
    } else if (stateValue === "error") {
      nodes[name].classList.add("error");
    } else if (stateValue === "static") {
      nodes[name].classList.add("static");
    }
  }
  for (const [name, stateValue] of Object.entries(topology.connectors || {})) {
    if (stateValue === "active") {
      connectors[name].classList.add("active");
    } else if (stateValue === "error") {
      connectors[name].classList.add("error");
    } else if (stateValue === "hidden") {
      connectors[name].classList.add("hidden");
    }
  }

  elements.statusKong.className = `status-pill ${topology.statusKongClass || "neutral"}`;
  elements.statusKong.textContent = topology.statusKong || "Kong Waiting";
  elements.statusRoute.className = `status-pill ${topology.statusRouteClass || "neutral"}`;
  elements.statusRoute.textContent = topology.statusRoute || "Route Pending";
}

function renderSceneDetails() {
  const scene = currentSceneDetails();
  const blocks = [
    ["Control Plane", scene.controlPlane || "Not defined"],
    ["Data Plane", scene.dataPlane || "Not defined"],
    ["Public Path", scene.publicPath || "Not defined"],
    ["Routing Header", scene.routingHeader || "Not defined"],
    ["Services", (scene.services || []).join(", ") || "None"],
    ["Routes", (scene.routes || []).join(", ") || "None"],
    ["Plugins", (scene.plugins || []).join(", ") || "None"],
  ];

  if (scene.consumers?.length) {
    blocks.push(["Consumers", scene.consumers.join(", ")]);
  }
  if (scene.upstreams?.length) {
    blocks.push(["Upstreams", scene.upstreams.join(", ")]);
  }
  if (scene.scenarios?.length) {
    blocks.push(["Scenarios", scene.scenarios.join(", ")]);
  }

  elements.sceneDetailsContent.innerHTML = blocks
    .map(
      ([label, value]) => `
        <div class="entity-block">
          <p class="label">${label}</p>
          <strong>${value}</strong>
        </div>
      `,
    )
    .join("");
}

function renderDetailView(detailView) {
  elements.detailMeta.innerHTML = (detailView.entities || [])
    .map(
      ([label, value]) => `
        <div class="entity-block">
          <p class="label">${label}</p>
          <strong>${value}</strong>
        </div>
      `,
    )
    .join("");
  elements.detailCurl.textContent = detailView.curl || "";
  elements.detailResponse.textContent = JSON.stringify(detailView.response || {}, null, 2);
}

function decodeJwt(token) {
  const parts = (token || "").trim().split(".");
  if (parts.length < 2) {
    throw new Error("Token is not a JWT.");
  }
  const decodePart = (value) => {
    const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized + "=".repeat((4 - (normalized.length % 4)) % 4);
    return JSON.parse(atob(padded));
  };
  return {
    header: decodePart(parts[0]),
    payload: decodePart(parts[1]),
  };
}

function renderDecodedJwt(decoded) {
  elements.decodedJwtOutput.textContent = JSON.stringify(decoded, null, 2);
}

function updateControlVisibility() {
  const isRateScene = state.currentScene === "traffic-control-rate-limiting";
  const isResilienceScene = state.currentScene === "resilience-failover-health-checks";
  const isIdentityScene =
    state.currentScene === "identity-azure-token-validation" ||
    state.currentScene === "identity-keycloak-authorization";
  elements.headerRoutingControls.classList.toggle("hidden", isRateScene || isResilienceScene || isIdentityScene);
  elements.rateModeControls.classList.toggle("hidden", !isRateScene);
  elements.rateCounterControls.classList.toggle("hidden", !isRateScene);
  elements.rateConsumerControls.classList.toggle("hidden", !isRateScene || state.mode !== "consumer");
  elements.resilienceScenarioControls.classList.toggle("hidden", !isResilienceScene);
  elements.resilienceInstanceControls.classList.toggle("hidden", !isResilienceScene);
  elements.identityTokenControls.classList.toggle("hidden", !isIdentityScene);
  elements.identityJwtControls.classList.toggle("hidden", !isIdentityScene);
  elements.identityConsumerControls.classList.toggle(
    "hidden",
    !(
      state.currentScene === "identity-keycloak-authorization" ||
      state.currentScene === "identity-azure-token-validation"
    ),
  );
  elements.controlPanelTitle.textContent = SCENE_DEFAULTS[state.currentScene].controlTitle;
}

function renderResilienceInstances(instances) {
  state.resilienceInstances = instances || {};
  const instance1 = state.resilienceInstances["instance-1"];
  const instance2 = state.resilienceInstances["instance-2"];
  elements.instance1Status.textContent = instance1 ? (instance1.running ? "healthy" : "unhealthy") : "unknown";
  elements.instance2Status.textContent = instance2 ? (instance2.running ? "healthy" : "unhealthy") : "unknown";

  for (const button of instanceActionButtons) {
    const instance = state.resilienceInstances[button.dataset.instanceId];
    const running = Boolean(instance?.running);
    if (button.dataset.instanceAction === "start") {
      button.disabled = running;
    } else {
      button.disabled = !running;
    }
  }
}

function updateRowsValue(rows, label, value) {
  return rows.map(([rowLabel, rowValue]) => (rowLabel === label ? [rowLabel, value] : [rowLabel, rowValue]));
}

function tickRateLimitCountdown() {
  if (!state.lastRun || state.currentScene !== "traffic-control-rate-limiting") {
    stopCountdown();
    return;
  }

  const result = state.lastRun.result || {};
  if (!state.countdownEndsAtMs) {
    stopCountdown();
    return;
  }

  const secondsLeft = Math.max(0, Math.ceil((state.countdownEndsAtMs - Date.now()) / 1000));
  result.resetSeconds = secondsLeft;

  if (state.lastRun.topology?.labels?.west) {
    state.lastRun.topology.labels.west = [
      state.lastRun.topology.labels.west[0],
      state.lastRun.topology.labels.west[1],
      `Request ${result.executionCount}, reset in ${secondsLeft}s`,
    ];
    renderTopology(state.lastRun.topology);
  }

  if (secondsLeft === 0) {
    stopCountdown();
  }
}

function startRateLimitCountdown() {
  stopCountdown();
  const resetSeconds = state.lastRun?.result?.resetSeconds;
  if (state.currentScene !== "traffic-control-rate-limiting" || resetSeconds == null) {
    return;
  }
  state.countdownEndsAtMs = Date.now() + (Math.max(resetSeconds, 0) * 1000);
  tickRateLimitCountdown();
  state.countdownTimer = window.setInterval(tickRateLimitCountdown, 1000);
}

async function runScenario() {
  elements.runScenarioButton.disabled = true;
  resetView();
  try {
    let path = "/api/scenes/header-routing/run";
    let body = { region: state.region === "missing" ? "" : state.region };
    if (state.currentScene === "traffic-control-rate-limiting") {
      path = "/api/scenes/rate-limiting/run";
      body = { mode: state.mode, consumer: state.consumer };
    } else if (state.currentScene === "resilience-failover-health-checks") {
      path = "/api/scenes/resilience/run";
      body = { scenario: state.resilienceScenario };
    } else if (state.currentScene === "identity-azure-token-validation") {
      path = "/api/scenes/identity/azure/run";
      body = { token: elements.tokenEditor.value.trim(), consumer: state.identityConsumer };
    } else if (state.currentScene === "identity-keycloak-authorization") {
      path = "/api/scenes/identity/keycloak/run";
      body = { token: elements.tokenEditor.value.trim(), consumer: state.identityConsumer };
    }

    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const payload = await response.json();
    state.lastRun = payload;
    elements.consoleDetailButton.disabled = false;
    elements.expectedOutcome.textContent = payload.expectedOutcome;
    renderRows(elements.requestPreviewGrid, payload.requestPreview);
    renderConsole(payload.consoleView);
    renderTopology(payload.topology);
    renderDetailView(payload.detailView);
    if (payload.instanceStates) {
      renderResilienceInstances(payload.instanceStates);
    }
    startRateLimitCountdown();
  } catch (error) {
    elements.consoleOutput.innerHTML = `
      <div class="console-empty console-empty-wide">
        <p>${error.message}</p>
      </div>
    `;
  } finally {
    elements.runScenarioButton.disabled = false;
  }
}

async function generateIdentityToken() {
  const path =
    state.currentScene === "identity-keycloak-authorization"
      ? "/api/scenes/identity/keycloak/token"
      : "/api/scenes/identity/azure/token";
  const body =
    state.currentScene === "identity-keycloak-authorization"
      ? { consumer: state.identityConsumer }
      : { consumer: state.identityConsumer };
  elements.generateTokenButton.disabled = true;
  try {
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || payload.tokenResponse?.error_description || "Token generation failed.");
    }
    state.identityToken = payload.token || "";
    elements.tokenEditor.value = state.identityToken;
    elements.decodedJwtOutput.textContent = "Token generated. Decode the current token to inspect its claims.";
  } finally {
    elements.generateTokenButton.disabled = false;
  }
}

function handleDecodeToken() {
  try {
    const decoded = decodeJwt(elements.tokenEditor.value.trim());
    renderDecodedJwt(decoded);
  } catch (error) {
    elements.decodedJwtOutput.textContent = error.message;
  }
}

async function refreshResilienceStatus() {
  if (state.currentScene !== "resilience-failover-health-checks") {
    return;
  }
  const response = await fetch("/api/scenes/resilience/status");
  const payload = await response.json();
  renderResilienceInstances(payload.instances);
}

async function resetSceneRuntime() {
  if (state.currentScene !== "resilience-failover-health-checks") {
    if (
      state.currentScene === "identity-azure-token-validation" ||
      state.currentScene === "identity-keycloak-authorization"
    ) {
      state.identityToken = "";
      elements.tokenEditor.value = "";
      elements.decodedJwtOutput.textContent = "Decode the current token to inspect its claims.";
    }
    resetView();
    return;
  }
  await fetch("/api/scenes/resilience/reset", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  await refreshResilienceStatus();
  resetView();
}

async function changeInstanceState(instanceId, action) {
  const response = await fetch("/api/scenes/resilience/instance", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ instance: instanceId, action }),
  });
  const payload = await response.json();
  renderResilienceInstances(payload.instances);
  if (state.currentScene === "resilience-failover-health-checks") {
    resetView();
  }
}

async function loadConfig() {
  const response = await fetch("/api/config");
  const payload = await response.json();
  state.links = payload.links;
  state.scenes = payload.scenes;
  elements.sceneSelect.innerHTML = payload.sceneOptions
    .map((scene) => `<option value="${scene.id}">${scene.label}</option>`)
    .join("");
  updateSceneState(payload.sceneOptions[0]?.id || "traffic-routing-header");
}

function updateArchitectureModal() {
  const scene = currentSceneDetails();
  document.getElementById("architectureTitle").textContent = scene.title || "Scene";
  const body = elements.architectureModal.querySelector(".modal-body");
  body.innerHTML = (scene.architecture || [])
    .map((line) => `<p>${line}</p>`)
    .join("");
}

function updateSceneState(sceneId) {
  stopCountdown();
  state.currentScene = sceneId;
  const scene = currentSceneDetails();
  elements.sceneTitle.textContent = scene.title || "Scene";
  updateControlVisibility();
  renderSceneDetails();
  updateArchitectureModal();
  resetView();
  if (state.currentScene === "resilience-failover-health-checks") {
    refreshResilienceStatus();
  }
  if (
    state.currentScene === "identity-azure-token-validation" ||
    state.currentScene === "identity-keycloak-authorization"
  ) {
    elements.tokenEditor.value = state.identityToken;
    elements.decodedJwtOutput.textContent = "Decode the current token to inspect its claims.";
  }
}

function openLink(url) {
  if (!url || url === "#") {
    return;
  }
  window.open(url, "_blank", "noopener,noreferrer");
}

function toggleModal(element, show) {
  element.classList.toggle("hidden", !show);
  element.setAttribute("aria-hidden", String(!show));
}

for (const button of regionButtons) {
  button.addEventListener("click", () => {
    state.region = button.dataset.region;
    setActiveButton(regionButtons, "region", state.region);
    updateStaticPreview();
  });
}

for (const button of modeButtons) {
  button.addEventListener("click", () => {
    state.mode = button.dataset.mode;
    setActiveButton(modeButtons, "mode", state.mode);
    updateControlVisibility();
    updateStaticPreview();
  });
}

for (const button of consumerButtons) {
  button.addEventListener("click", () => {
    state.consumer = button.dataset.consumer;
    setActiveButton(consumerButtons, "consumer", state.consumer);
    updateStaticPreview();
  });
}

for (const button of identityConsumerButtons) {
  button.addEventListener("click", () => {
    state.identityConsumer = button.dataset.identityConsumer;
    setActiveButton(identityConsumerButtons, "identityConsumer", state.identityConsumer);
    state.identityToken = "";
    elements.tokenEditor.value = "";
    elements.decodedJwtOutput.textContent = "Decode the current token to inspect its claims.";
    updateStaticPreview();
    resetView();
  });
}

for (const button of resilienceScenarioButtons) {
  button.addEventListener("click", () => {
    state.resilienceScenario = button.dataset.resilienceScenario;
    setActiveButton(resilienceScenarioButtons, "resilienceScenario", state.resilienceScenario);
    updateStaticPreview();
    resetView();
  });
}

for (const button of instanceActionButtons) {
  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      await changeInstanceState(button.dataset.instanceId, button.dataset.instanceAction);
    } finally {
      button.disabled = false;
    }
  });
}

elements.tokenEditor.addEventListener("input", () => {
  state.identityToken = elements.tokenEditor.value;
});
elements.generateTokenButton.addEventListener("click", generateIdentityToken);
elements.decodeTokenButton.addEventListener("click", handleDecodeToken);
elements.sceneSelect.addEventListener("change", (event) => updateSceneState(event.target.value));
elements.runScenarioButton.addEventListener("click", runScenario);
elements.resetSceneButton.addEventListener("click", resetSceneRuntime);
elements.resetPanelButton.addEventListener("click", resetSceneRuntime);
elements.viewArchitectureButton.addEventListener("click", () => toggleModal(elements.architectureModal, true));
elements.viewLogsButton.addEventListener("click", () => openLink(state.links.logs));
elements.viewAuditButton.addEventListener("click", () => openLink(state.links.audit));
elements.viewSceneDetailsButton.addEventListener("click", () => {
  renderSceneDetails();
  toggleModal(elements.sceneDetailsModal, true);
});
elements.consoleDetailButton.addEventListener("click", () => {
  if (!state.lastRun) {
    return;
  }
  renderDetailView(state.lastRun.detailView);
  toggleModal(elements.detailViewModal, true);
});
elements.closeArchitectureButton.addEventListener("click", () => toggleModal(elements.architectureModal, false));
elements.closeSceneDetailsButton.addEventListener("click", () => toggleModal(elements.sceneDetailsModal, false));
elements.closeDetailViewButton.addEventListener("click", () => toggleModal(elements.detailViewModal, false));

for (const modal of [elements.architectureModal, elements.sceneDetailsModal, elements.detailViewModal]) {
  modal.addEventListener("click", (event) => {
    if (event.target === modal) {
      toggleModal(modal, false);
    }
  });
}

window.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    toggleModal(elements.architectureModal, false);
    toggleModal(elements.sceneDetailsModal, false);
    toggleModal(elements.detailViewModal, false);
  }
});

loadConfig().then(() => {
  setActiveButton(regionButtons, "region", state.region);
  setActiveButton(modeButtons, "mode", state.mode);
  setActiveButton(consumerButtons, "consumer", state.consumer);
  setActiveButton(identityConsumerButtons, "identityConsumer", state.identityConsumer);
  setActiveButton(resilienceScenarioButtons, "resilienceScenario", state.resilienceScenario);
  updateStaticPreview();
  resetView();
});
