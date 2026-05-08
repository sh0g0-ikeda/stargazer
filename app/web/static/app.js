const state = {
  projectId: null,
  latestArchitecture: null,
  latestResponse: null,
};

const output = document.querySelector("#responseOutput");
const projectIdView = document.querySelector("#projectId");
const projectPhaseView = document.querySelector("#projectPhase");
const architectureMap = document.querySelector("#architectureMap");
const opsDashboard = document.querySelector("#opsDashboard");
const serverStatus = document.querySelector("#serverStatus");

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "content-type": "application/json",
    },
    ...options,
  });
  const body = await response.json();
  state.latestResponse = body;
  output.textContent = JSON.stringify(body, null, 2);
  if (!response.ok || body.error) {
    throw new Error(body.error ? body.error.message : `HTTP ${response.status}`);
  }
  return body.data;
}

async function refreshProject() {
  if (!state.projectId) {
    return;
  }
  const project = await api(`/api/projects/${state.projectId}`);
  projectIdView.textContent = project.id;
  projectPhaseView.textContent = project.phase;
}

async function createProject() {
  const data = await api("/api/projects", {
    method: "POST",
    body: JSON.stringify({
      name: document.querySelector("#projectName").value,
      idea: document.querySelector("#projectIdea").value,
    }),
  });
  state.projectId = data.id;
  projectIdView.textContent = data.id;
  projectPhaseView.textContent = data.phase;
}

async function requireProject() {
  if (!state.projectId) {
    await createProject();
  }
  return state.projectId;
}

async function runStep(step) {
  const projectId = await requireProject();
  if (step === "follow-up") {
    await api(`/api/projects/${projectId}/follow-up`, { method: "POST", body: "{}" });
  } else if (step === "requirements") {
    await api(`/api/projects/${projectId}/requirements`, { method: "POST", body: "{}" });
  } else if (step === "approve-requirements") {
    await approve("requirements");
  } else if (step === "designs") {
    await api(`/api/projects/${projectId}/designs`, { method: "POST", body: "{}" });
  } else if (step === "approve-design") {
    await approve("design");
  } else if (step === "architecture") {
    await api(`/api/projects/${projectId}/architecture`, {
      method: "POST",
      body: JSON.stringify({ target_project_id: document.querySelector("#targetProjectId").value }),
    });
    await loadArchitecture();
  } else if (step === "security") {
    await api(`/api/projects/${projectId}/security`, { method: "POST", body: "{}" });
  } else if (step === "approve-architecture") {
    await approve("architecture");
  } else if (step === "target-app") {
    await api(`/api/projects/${projectId}/target-app`, { method: "POST", body: "{}" });
  } else if (step === "apply") {
    await api(`/api/projects/${projectId}/apply`, { method: "POST", body: "{}" });
  } else if (step === "ops") {
    await loadOps();
  } else if (step === "timeline") {
    await api(`/api/projects/${projectId}/timeline`);
  }
  await refreshProject();
}

async function approve(gate) {
  const projectId = await requireProject();
  await api(`/api/projects/${projectId}/approve`, {
    method: "POST",
    body: JSON.stringify({
      gate,
      decision: "approved",
      rationale: "Approved from demo UI",
      snapshot: state.latestResponse ? state.latestResponse.data : {},
    }),
  });
}

async function runDemoFlow() {
  await createProject();
  for (const step of [
    "follow-up",
    "requirements",
    "approve-requirements",
    "designs",
    "approve-design",
    "architecture",
    "security",
    "approve-architecture",
    "target-app",
    "apply",
    "ops",
    "timeline",
  ]) {
    await runStep(step);
  }
}

async function loadArchitecture() {
  const projectId = await requireProject();
  const architecture = await api(`/api/projects/${projectId}/architecture/latest`);
  state.latestArchitecture = architecture;
  renderArchitecture(architecture);
}

function renderArchitecture(architecture) {
  const nodes = architecture.spec.nodes;
  architectureMap.classList.remove("empty");
  architectureMap.replaceChildren();
  for (const node of nodes) {
    const item = document.createElement("article");
    item.className = "node";
    appendText(item, "strong", node.name);
    appendText(item, "span", `ID: ${node.id}`);
    appendText(item, "span", `Type: ${node.type}`);
    appendText(item, "span", `Cost: ${node.cost_band}`);
    appendText(item, "span", `Params: ${JSON.stringify(node.parameters)}`);
    architectureMap.appendChild(item);
  }
}

async function previewNodeEdit() {
  const projectId = await requireProject();
  await api(`/api/projects/${projectId}/architecture/preview-node`, {
    method: "POST",
    body: JSON.stringify(nodePatchPayload()),
  });
}

async function saveNodeEdit(event) {
  event.preventDefault();
  const projectId = await requireProject();
  await api(`/api/projects/${projectId}/architecture/update-node`, {
    method: "POST",
    body: JSON.stringify({
      ...nodePatchPayload(),
      change_reason: "Adjusted Cloud Run parameters from demo UI",
    }),
  });
  await loadArchitecture();
}

function nodePatchPayload() {
  return {
    node_id: document.querySelector("#nodeId").value,
    parameter_patch: {
      memory: document.querySelector("#nodeMemory").value,
      cpu: document.querySelector("#nodeCpu").value,
      allow_unauthenticated: document.querySelector("#allowUnauthenticated").checked,
    },
  };
}

async function loadOps() {
  const projectId = await requireProject();
  const ops = await api(`/api/projects/${projectId}/ops`);
  opsDashboard.classList.remove("empty");
  opsDashboard.replaceChildren();
  for (const [key, value] of Object.entries(ops)) {
    const item = document.createElement("article");
    item.className = "metric";
    appendText(item, "strong", key);
    appendText(item, "span", summary(value));
    opsDashboard.appendChild(item);
  }
}

function summary(value) {
  if (value === null || value === undefined) {
    return "-";
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (Array.isArray(value)) {
    return `${value.length} item(s)`;
  }
  return Object.keys(value).slice(0, 4).join(", ");
}

function appendText(parent, tagName, value) {
  const element = document.createElement(tagName);
  element.textContent = String(value);
  parent.appendChild(element);
}

async function checkHealth() {
  try {
    await api("/api/health");
    serverStatus.textContent = "Server ready";
  } catch (error) {
    serverStatus.textContent = "Server unavailable";
  }
}

document.querySelector("#createProjectButton").addEventListener("click", () => withBusy(createProject));
document.querySelector("#runDemoButton").addEventListener("click", () => withBusy(runDemoFlow));
document.querySelector("#previewNodeButton").addEventListener("click", () => withBusy(previewNodeEdit));
document.querySelector("#nodeEditForm").addEventListener("submit", (event) => withBusy(() => saveNodeEdit(event)));
for (const button of document.querySelectorAll("[data-step]")) {
  button.addEventListener("click", () => withBusy(() => runStep(button.dataset.step)));
}

async function withBusy(operation) {
  const buttons = Array.from(document.querySelectorAll("button"));
  buttons.forEach((button) => {
    button.disabled = true;
  });
  try {
    await operation();
  } catch (error) {
    output.textContent = JSON.stringify({ error: error.message }, null, 2);
  } finally {
    buttons.forEach((button) => {
      button.disabled = false;
    });
  }
}

checkHealth();
