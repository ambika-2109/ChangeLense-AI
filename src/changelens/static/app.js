const $ = (selector) => document.querySelector(selector);
const planInput = $("#plan-input");
const inputFeedback = $("#input-feedback");
const inputFooter = $(".input-footer");
const analyzeButton = $("#analyze-button");
const resultsContent = $("#results-content");
const reportState = $("#report-state");
const fileInput = $("#plan-file");
const dropzone = $("#dropzone");
const MAX_FILE_BYTES = 10 * 1024 * 1024;

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function setFeedback(message, isError = false) {
  inputFeedback.textContent = message;
  inputFooter.classList.toggle("error", isError);
}

function showToast(message, isError = false) {
  const toast = document.getElementById("upload-toast");
  if (!toast) return;
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.add("show");
  clearTimeout(toast._toastTimer);
  toast._toastTimer = setTimeout(() => toast.classList.remove("show"), 3200);
}

function setReportState(label, state = "") {
  reportState.className = `report-state ${state}`.trim();
  reportState.lastChild.textContent = label;
}

function prettyValue(value) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

function renderLoading() {
  resultsContent.replaceChildren();
  const loading = node("div", "loading-state");
  loading.append(node("span", "spinner"));
  loading.append(node("span", "", "Reading plan, tracing dependencies, and evaluating policies…"));
  resultsContent.append(loading);
}

function renderError(message) {
  resultsContent.replaceChildren();
  const error = node("div", "error-box");
  error.textContent = message;
  resultsContent.append(error);
  setReportState("Could not analyze", "failed");
}

function renderSummary(report) {
  const changedCount = report.changes.filter(
    (change) => !["no-op", "read"].includes(change.operation),
  ).length;
  const findingsCount = report.findings.length;
  const impactCount = report.affected_resources.length;
  const grid = node("div", "summary-grid");
  const summaries = [
    ["Resources changed", changedCount, ""],
    ["Risk findings", findingsCount, findingsCount ? "has-risk" : "safe"],
    ["Blast radius", impactCount, ""],
  ];
  for (const [label, value, emphasis] of summaries) {
    const card = node("div", "summary-card");
    card.append(node("span", "summary-label", label));
    card.append(node("span", `summary-value ${emphasis}`.trim(), String(value)));
    grid.append(card);
  }
  return grid;
}

function renderFinding(finding) {
  const severity = String(finding.severity || "medium").toLowerCase();
  const card = node("article", `finding-card severity-${severity}`);
  const top = node("div", "finding-top");
  const titleWrap = node("div", "finding-title-wrap");
  titleWrap.append(node("span", "risk-icon", severity === "critical" ? "!" : "◇"));
  titleWrap.append(node("h4", "finding-title", finding.title));
  top.append(titleWrap);
  top.append(node("span", "severity-badge", severity));
  card.append(top);
  card.append(node("p", "finding-reason", finding.reasoning));

  const meta = node("div", "finding-meta");
  const recommendation = node("div", "");
  recommendation.append(node("span", "meta-label", "Recommended verification"));
  recommendation.append(node("div", "meta-value", finding.recommended_test));
  meta.append(recommendation);

  if (finding.evidence?.length) {
    for (const evidence of finding.evidence) {
      const evidenceBlock = node("div", "");
      evidenceBlock.append(node("span", "meta-label", "Evidence · " + evidence.evidence_id));
      evidenceBlock.append(node("code", "evidence-ref", evidence.source));
      evidenceBlock.append(node("div", "meta-value", evidence.detail));
      meta.append(evidenceBlock);
    }
  } else if (finding.evidence_refs?.length) {
    const evidenceBlock = node("div", "");
    evidenceBlock.append(node("span", "meta-label", "Evidence references"));
    for (const reference of finding.evidence_refs) {
      evidenceBlock.append(node("code", "evidence-ref", reference));
    }
    meta.append(evidenceBlock);
  }

  if (finding.uncertainties?.length) {
    const uncertainty = node("div", "uncertainty-box");
    uncertainty.append(node("span", "meta-label", "What is not known"));
    uncertainty.append(document.createTextNode(finding.uncertainties.join(" ")));
    meta.append(uncertainty);
  }
  card.append(meta);
  return card;
}

function renderChanges(changes) {
  const list = node("div", "resource-list");
  for (const change of changes) {
    const row = node("article", "resource-row");
    const top = node("div", "resource-top");
    top.append(node("code", "resource-address", change.address));
    top.append(node("span", `operation-pill operation-${change.operation}`, change.operation));
    row.append(top);

    const attributes = Object.entries(change.changed_attributes || {});
    if (attributes.length) {
      const attributeList = node("div", "attribute-list");
      for (const [name, values] of attributes) {
        const item = node("div", "attribute-row");
        item.append(node("span", "attribute-name", name));
        const pair = node("span", "attribute-values");
        pair.append(document.createTextNode(prettyValue(values.before)));
        pair.append(node("span", "arrow", "→"));
        pair.append(document.createTextNode(prettyValue(values.after)));
        item.append(pair);
        attributeList.append(item);
      }
      row.append(attributeList);
    } else {
      row.append(node("div", "resource-dependencies", "No attribute-level differences reported."));
    }
    if (change.depends_on?.length) {
      row.append(node("div", "resource-dependencies", `Depends on: ${change.depends_on.join(", ")}`));
    }
    list.append(row);
  }
  return list;
}

function renderReport(report) {
  resultsContent.replaceChildren();
  resultsContent.append(renderSummary(report));

  const findingsSection = node("section", "report-section");
  const findingsHeading = node("div", "section-heading");
  findingsHeading.append(node("h3", "", "Risk findings"));
  findingsHeading.append(node("span", "section-count", `${report.findings.length} total`));
  findingsSection.append(findingsHeading);
  if (report.findings.length) {
    for (const finding of report.findings) findingsSection.append(renderFinding(finding));
  } else {
    const allClear = node("div", "no-findings");
    allClear.append(node("span", "no-findings-icon", "✓"));
    const message = node("div", "");
    message.append(node("strong", "", "No configured risk rules were triggered"));
    message.append(node("p", "", "This is not a guarantee of safety; the current policy set is intentionally limited."));
    allClear.append(message);
    findingsSection.append(allClear);
  }
  resultsContent.append(findingsSection);

  const impactSection = node("section", "report-section");
  const impactHeading = node("div", "section-heading");
  impactHeading.append(node("h3", "", "Affected resources"));
  impactHeading.append(node("span", "section-count", `${report.affected_resources.length} resources`));
  impactSection.append(impactHeading);
  const chips = node("div", "impact-chips");
  if (report.affected_resources.length) {
    for (const resource of report.affected_resources) chips.append(node("span", "impact-chip", resource));
  } else {
    chips.append(node("span", "section-count", "No planned changes to trace"));
  }
  impactSection.append(chips);
  resultsContent.append(impactSection);

  const changesSection = node("section", "report-section");
  const changesHeading = node("div", "section-heading");
  changesHeading.append(node("h3", "", "Resource changes"));
  changesHeading.append(node("span", "section-count", `${report.changes.length} resources`));
  changesSection.append(changesHeading);
  if (report.changes.length) changesSection.append(renderChanges(report.changes));
  else changesSection.append(node("p", "section-count", "The plan contains no resource changes."));
  resultsContent.append(changesSection);

  if (report.warnings?.length) {
    const warning = node("div", "warning-box");
    warning.append(node("strong", "", "Analysis limitations"));
    warning.append(document.createTextNode(report.warnings.join(" ")));
    resultsContent.append(warning);
  }
  const version = report.plan_format_version ? ` · plan ${report.plan_format_version}` : "";
  setReportState(`Analysis complete${version}`, "complete");
}

async function loadExample(name) {
  setFeedback("Loading sample…");
  try {
    const response = await fetch(`/examples/${encodeURIComponent(name)}`);
    if (!response.ok) throw new Error("Sample plan could not be loaded.");
    const plan = await response.json();
    planInput.value = JSON.stringify(plan, null, 2);
    $("#file-name").textContent = "Sample loaded · choose a local JSON file to replace it";
    setFeedback("Sample loaded · review before analyzing");
  } catch (error) {
    setFeedback(error.message || "Unable to load sample.", true);
  }
}

async function readPlanFile(file) {
  if (!file) return;
  if (file.size > MAX_FILE_BYTES) {
    setFeedback("File exceeds the 10 MB limit.", true);
    return;
  }
  try {
    const text = await file.text();
    JSON.parse(text);
    planInput.value = text;
    $("#file-name").textContent = file.name;
    setFeedback("File loaded · submit when ready");
    showToast(`JSON uploaded: ${file.name}`);
  } catch {
    setFeedback("That file is not valid JSON.", true);
    showToast("Invalid JSON file", true);
  }
}

async function analyze() {
  let plan;
  try {
    plan = JSON.parse(planInput.value);
    if (!plan || typeof plan !== "object" || Array.isArray(plan)) {
      throw new Error("The plan must be a JSON object.");
    }
  } catch (error) {
    renderError(error.message || "Enter a valid Terraform plan JSON object.");
    setFeedback("Check the JSON payload and try again.", true);
    return;
  }

  analyzeButton.disabled = true;
  analyzeButton.querySelector(".button-content").lastChild.textContent = "Analyzing…";
  renderLoading();
  setReportState("Analysis in progress");
  setFeedback("Plan submitted for deterministic analysis");
  try {
    const response = await fetch("/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(plan),
    });
    const result = await response.json();
    if (!response.ok) {
      const detail = typeof result.detail === "string" ? result.detail : "The plan could not be analyzed.";
      throw new Error(detail);
    }
    renderReport(result);
  } catch (error) {
    renderError(error.message || "Could not reach the analysis API. Check that the server is running.");
    setFeedback("Analysis failed", true);
  } finally {
    analyzeButton.disabled = false;
    analyzeButton.querySelector(".button-content").lastChild.textContent = "Analyze changes";
  }
}

async function checkHealth() {
  const status = $("#api-status");
  try {
    const response = await fetch("/health");
    if (!response.ok) throw new Error("offline");
    status.className = "api-status online";
    status.lastChild.textContent = "API connected";
  } catch {
    status.className = "api-status offline";
    status.lastChild.textContent = "API unavailable";
  }
}

$("#example-select").addEventListener("change", (event) => loadExample(event.target.value));
analyzeButton.addEventListener("click", analyze);
fileInput.addEventListener("change", (event) => readPlanFile(event.target.files[0]));
dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    fileInput.click();
  }
});
for (const eventName of ["dragenter", "dragover"]) {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.add("dragover");
  });
}
for (const eventName of ["dragleave", "drop"]) {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.remove("dragover");
  });
}
dropzone.addEventListener("drop", (event) => readPlanFile(event.dataTransfer.files[0]));

checkHealth();
loadExample($("#example-select").value);
