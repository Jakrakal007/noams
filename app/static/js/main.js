const modal = document.querySelector("#upload-modal");
const form = document.querySelector("#upload-form");
const fileInput = document.querySelector("#analysis-file");
const fileLabel = document.querySelector("#file-label");
const formError = document.querySelector("#form-error");
const submitButton = document.querySelector("#process-upload");
const findingModal = document.querySelector("#finding-modal");
const t = (key) => window.NOAMSI18n?.t(key) ?? key;
const dynamicLabel = (type, value) => window.NOAMSI18n?.dynamic(type, value) ?? value;

const openModal = () => {
  form.reset();
  fileLabel.textContent = t("upload.file");
  formError.hidden = true;
  modal.showModal();
};

const closeModal = () => {
  if (!submitButton.disabled) modal.close();
};

document.querySelector("#open-upload")?.addEventListener("click", openModal);
document.querySelector("#close-upload")?.addEventListener("click", closeModal);
document.querySelector("#cancel-upload")?.addEventListener("click", closeModal);
modal?.addEventListener("click", (event) => {
  if (event.target === modal) closeModal();
});

fileInput?.addEventListener("change", () => {
  fileLabel.textContent = fileInput.files[0]?.name || t("upload.file");
  formError.hidden = true;
});

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!fileInput.files.length) {
    showFormError(t("upload.select_error"));
    return;
  }

  submitButton.disabled = true;
  submitButton.textContent = t("upload.processing");
  formError.hidden = true;

  try {
    const response = await fetch("/api/analysis/upload", {
      method: "POST",
      body: new FormData(form),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(dynamicLabel("message", payload.error?.message || t("upload.process_error")));

    modal.close();
    renderResult(payload);
    await refreshDashboard();
  } catch (error) {
    showFormError(dynamicLabel("message", error.message || t("error.unexpected")));
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = t("upload.run");
  }
});

function showFormError(message) {
  formError.textContent = message;
  formError.hidden = false;
}

function renderResult(result) {
  document.querySelector("#result-filename").textContent = result.filename;
  const status = document.querySelector("#result-status");
  status.dataset.i18nDynamic = "status";
  status.dataset.i18nValue = result.status;
  status.textContent = dynamicLabel("status", result.status);
  document.querySelector("#result-total").textContent = result.total_records.toLocaleString("en");
  document.querySelector("#result-valid").textContent = result.valid_records.toLocaleString("en");
  document.querySelector("#result-invalid").textContent = result.invalid_records.toLocaleString("en");
  document.querySelector("#result-time").textContent = `${result.processing_time_ms} ms`;

  const errorsSection = document.querySelector("#errors-section");
  const noErrors = document.querySelector("#no-errors");
  const errorsBody = document.querySelector("#errors-body");
  errorsBody.replaceChildren();

  errorsSection.hidden = result.errors.length === 0;
  noErrors.hidden = result.errors.length !== 0;
  result.errors.forEach((error) => {
    const row = document.createElement("tr");
    [error.row, error.column, error.message].forEach((value) => {
      const cell = document.createElement("td");
      if (value === error.message) {
        cell.dataset.i18nDynamic = "validation";
        cell.dataset.i18nValue = value;
        cell.textContent = dynamicLabel("validation", value);
      } else cell.textContent = value;
      row.appendChild(cell);
    });
    errorsBody.appendChild(row);
  });

  const card = document.querySelector("#analysis-result");
  const savedAnalysisLink = document.querySelector("#view-saved-analysis");
  savedAnalysisLink.href = `/analysis/${result.analysis_id}`;
  savedAnalysisLink.hidden = false;
  card.hidden = false;
  card.scrollIntoView({ behavior: "smooth", block: "start" });
  renderFindings(result.findings || []);
}

async function refreshDashboard() {
  const response = await fetch("/api/analysis/metrics");
  if (!response.ok) return;
  const metrics = await response.json();
  const values = {
    "#analyses-count": metrics.analyses_count.toLocaleString("en"),
    "#records-processed": metrics.records_processed.toLocaleString("en"),
    "#findings-count": metrics.findings_count.toLocaleString("en"),
    "#critical-risks": metrics.critical_risks.toLocaleString("en"),
    "#estimated-impact": formatMoney(metrics.estimated_impact),
  };
  Object.entries(values).forEach(([selector, value]) => {
    const element = document.querySelector(selector);
    if (element) element.textContent = value;
  });
}

const analysisDeleteModal = document.querySelector("#analysis-delete-modal");
const analysisDeleteFilename = document.querySelector("#analysis-delete-filename");
const analysisDeleteError = document.querySelector("#analysis-delete-error");
const analysisDeleteConfirm = document.querySelector("#confirm-analysis-delete");
let pendingAnalysisDelete = null;

function closeAnalysisDeleteModal() {
  if (!analysisDeleteModal || analysisDeleteConfirm?.disabled) return;
  pendingAnalysisDelete = null;
  analysisDeleteModal.close();
}

document.querySelectorAll(".analysis-delete-button").forEach((button) => {
  button.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    pendingAnalysisDelete = { id: button.dataset.analysisId, filename: button.dataset.analysisFilename };
    analysisDeleteFilename.textContent = pendingAnalysisDelete.filename;
    analysisDeleteError.hidden = true;
    analysisDeleteError.textContent = "";
    analysisDeleteModal.showModal();
  });
});

document.querySelector("#cancel-analysis-delete")?.addEventListener("click", closeAnalysisDeleteModal);
document.querySelector("#close-analysis-delete")?.addEventListener("click", closeAnalysisDeleteModal);
analysisDeleteModal?.addEventListener("click", (event) => {
  if (event.target === analysisDeleteModal) closeAnalysisDeleteModal();
});
analysisDeleteModal?.addEventListener("cancel", (event) => {
  if (analysisDeleteConfirm?.disabled) event.preventDefault();
  else pendingAnalysisDelete = null;
});
analysisDeleteConfirm?.addEventListener("click", async () => {
  if (!pendingAnalysisDelete || analysisDeleteConfirm.disabled) return;
  const { id } = pendingAnalysisDelete;
  analysisDeleteConfirm.disabled = true;
  analysisDeleteConfirm.textContent = "Deleting...";
  analysisDeleteError.hidden = true;
  try {
    const response = await fetch(`/api/analysis/${id}`, { method: "DELETE" });
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.error?.message || "The analysis could not be deleted. Please try again.");
    }
    analysisDeleteModal.close();
    pendingAnalysisDelete = null;
    await refreshDashboard();
    window.location.reload();
  } catch (error) {
    analysisDeleteError.textContent = error.message;
    analysisDeleteError.hidden = false;
  } finally {
    analysisDeleteConfirm.disabled = false;
    analysisDeleteConfirm.textContent = "Yes, delete";
  }
});

function renderFindings(findings) {
  const list = document.querySelector("#findings-list");
  const empty = document.querySelector("#no-findings");
  document.querySelector("#findings-total").textContent = findings.length.toLocaleString("en");
  list.replaceChildren();
  empty.hidden = findings.length !== 0;
  findings.forEach((finding) => list.appendChild(createFindingCard(finding)));
}

function createFindingCard(finding) {
  const card = document.createElement("article");
  card.className = "finding-card";
  card.dataset.severity = finding.severity;

  const head = document.createElement("div");
  head.className = "finding-card-head";
  const text = document.createElement("div");
  const title = document.createElement("h4");
  title.dataset.i18nDynamic = "rule";
  title.dataset.i18nValue = finding.rule_code;
  title.textContent = dynamicLabel("rule", finding.rule_code);
  const description = document.createElement("p");
  description.dataset.i18nDynamic = "finding_description";
  description.dataset.i18nValue = finding.description;
  description.textContent = dynamicLabel("finding_description", finding.description);
  text.append(title, description);
  const badge = document.createElement("span");
  badge.className = "severity-badge";
  badge.dataset.i18nDynamic = "severity";
  badge.dataset.i18nValue = finding.severity;
  badge.textContent = dynamicLabel("severity", finding.severity);
  head.append(text, badge);

  const meta = document.createElement("div");
  meta.className = "finding-meta";
  [finding.rule_code, finding.supplier_name, formatMoney(finding.estimated_impact)].filter(Boolean).forEach((value) => {
    const item = document.createElement("span");
    item.textContent = value;
    meta.appendChild(item);
  });
  const button = document.createElement("button");
  button.type = "button";
  button.className = "detail-button";
  button.dataset.i18n = "result.view_details";
  button.textContent = t("result.view_details");
  button.addEventListener("click", () => openFindingDetail(finding.id));
  meta.appendChild(button);
  card.append(head, meta);
  return card;
}

async function openFindingDetail(findingId) {
  const response = await fetch(`/api/findings/${findingId}`);
  if (!response.ok) return;
  const finding = await response.json();
  const grid = document.querySelector("#finding-detail-grid");
  grid.replaceChildren();
  const details = [
    ["finding.identifier", finding.finding_uuid],
    ["finding.title", dynamicLabel("rule", finding.rule_code), true],
    ["common.status", dynamicLabel("status", finding.status)],
    ["finding.severity", dynamicLabel("severity", finding.severity)],
    ["finding.rule", finding.rule_code],
    ["finding.category", dynamicLabel("category", finding.category)],
    ["common.description", dynamicLabel("finding_description", finding.description), true],
    ["finding.supplier", finding.supplier_name],
    ["finding.date", finding.transaction_date],
    ["finding.purchase_order", finding.purchase_order],
    ["finding.detected_amount", formatMoney(finding.detected_value)],
    ["finding.expected", formatMoney(finding.expected_value)],
    ["finding.deviation", finding.deviation_percentage ? `${finding.deviation_percentage}%` : null],
    ["finding.impact", formatMoney(finding.estimated_impact)],
    ["finding.confidence", finding.confidence_score ? `${(Number(finding.confidence_score) * 100).toFixed(0)}%` : null],
  ];
  details.forEach(([label, value, wide]) => {
    const wrapper = document.createElement("div");
    if (wide) wrapper.className = "wide";
    const term = document.createElement("dt");
    term.dataset.i18n = label;
    term.textContent = t(label);
    const description = document.createElement("dd");
    description.textContent = value ?? t("finding.not_applicable");
    wrapper.append(term, description);
    grid.appendChild(wrapper);
  });
  const evidence = document.querySelector("#finding-evidence");
  evidence.replaceChildren();
  Object.entries(finding.evidence_json || {}).forEach(([key, value]) => {
    const term = document.createElement("dt");
    term.dataset.i18nDynamic = "evidence";
    term.dataset.i18nValue = key;
    term.textContent = dynamicLabel("evidence", key);
    const description = document.createElement("dd");
    description.textContent = typeof value === "object" ? JSON.stringify(value) : String(value);
    evidence.append(term, description);
  });
  findingModal.showModal();
}

function formatMoney(value) {
  if (value === null || value === undefined || value === "") return null;
  const locale = window.NOAMSI18n?.currentLanguage() === "es" ? "es-PE" : "en-PE";
  return new Intl.NumberFormat(locale, { style: "currency", currency: "PEN" }).format(Number(value));
}

document.querySelectorAll(".js-finding-detail").forEach((button) => {
  button.addEventListener("click", () => openFindingDetail(button.dataset.findingId));
});

document.querySelector("#close-finding")?.addEventListener("click", () => findingModal.close());
findingModal?.addEventListener("click", (event) => {
  if (event.target === findingModal) findingModal.close();
});

if (modal && window.location.hash === "#upload") openModal();
