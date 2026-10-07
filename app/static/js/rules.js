(() => {
  const app = document.querySelector("#rules-app");
  if (!app) return;

  const modal = document.querySelector("#rule-modal");
  const form = document.querySelector("#rule-form");
  const fields = document.querySelector("#rule-fields");
  const enabled = document.querySelector("#rule-enabled");
  const toggleStatus = document.querySelector("#rule-toggle-status");
  const formError = document.querySelector("#rule-form-error");
  const formSuccess = document.querySelector("#rule-form-success");
  const guideText = document.querySelector("#rule-guide-text");
  const saveButton = document.querySelector("#rule-save");
  const resetButton = document.querySelector("#rule-reset");
  const closeButton = document.querySelector("#rule-close");
  const cancelButton = document.querySelector("#rule-cancel");
  const toast = document.querySelector("#rule-toast");
  const state = { currentRuleCode: null, originalRuleData: null, draftRuleData: null, isSaving: false };

  const t = (key) => window.NOAMSI18n?.t(key) ?? key;
  const dynamic = (type, value) => window.NOAMSI18n?.dynamic(type, value) ?? value;
  const clone = (value) => JSON.parse(JSON.stringify(value));
  const fieldDefinitions = {
    minimum_history: { min: 1, max: 10000, step: 1, integer: true },
    multiplier: { min: 1.01, max: 1000, step: 0.01, exclusiveMin: 1 },
    minimum_difference: { min: 0, max: 1000000000, step: 0.01 },
    medium_threshold_percentage: { min: 0, max: 100000, step: 0.01 },
    high_threshold_percentage: { min: 0, max: 100000, step: 0.01 },
    critical_threshold_percentage: { min: 0, max: 100000, step: 0.01 },
    approval_threshold: { min: 0, max: 1000000000, step: 0.01 },
    critical_multiplier: { min: 1.01, max: 1000, step: 0.01, exclusiveMin: 1 },
    window_days: { min: 1, max: 3650, step: 1, integer: true },
    minimum_operations: { min: 2, max: 10000, step: 1, integer: true }
  };

  const setNotice = (message = "", success = false) => {
    formError.hidden = success || !message;
    formSuccess.hidden = !success || !message;
    formError.textContent = success ? "" : message;
    formSuccess.textContent = success ? message : "";
  };
  const showToast = (message) => {
    toast.textContent = message; toast.hidden = false;
    window.clearTimeout(showToast.timer); showToast.timer = window.setTimeout(() => { toast.hidden = true; }, 3200);
  };
  const setBusy = (busy, action = "save") => {
    state.isSaving = busy; saveButton.disabled = busy; resetButton.disabled = busy;
    closeButton.disabled = busy; cancelButton.disabled = busy;
    saveButton.textContent = busy && action === "save" ? t("rules.saving") : t("rules.save");
    resetButton.textContent = busy && action === "reset" ? t("rules.restoring") : t("rules.restore");
  };
  const updateEnabledPresentation = () => {
    if (!state.draftRuleData) return;
    state.draftRuleData.enabled = enabled.checked;
    enabled.setAttribute("aria-checked", String(enabled.checked));
    toggleStatus.textContent = t(enabled.checked ? "rules.enabled" : "rules.disabled_state");
    toggleStatus.className = `rule-toggle-status ${enabled.checked ? "active" : "disabled"}`;
    fields.classList.toggle("is-disabled", !enabled.checked);
    fields.querySelectorAll("input").forEach((input) => { input.disabled = !enabled.checked; });
  };
  const renderFields = () => {
    fields.replaceChildren();
    const entries = Object.entries(state.draftRuleData?.configuration || {});
    if (!entries.length) return;
    for (const [key, value] of entries) {
      const definition = fieldDefinitions[key];
      if (!definition) continue;
      const wrapper = document.createElement("div"); wrapper.className = "rule-field";
      const label = document.createElement("label"); label.htmlFor = `rule-field-${key}`; label.textContent = t(`rules.field.${key}`);
      const input = document.createElement("input"); input.type = "number"; input.id = `rule-field-${key}`; input.name = key; input.value = value;
      input.min = definition.min; input.max = definition.max; input.step = definition.step;
      input.setAttribute("aria-describedby", `rule-field-${key}-error`);
      input.addEventListener("input", () => { state.draftRuleData.configuration[key] = input.value; clearFieldError(key); });
      const fieldError = document.createElement("small"); fieldError.className = "rule-field-error"; fieldError.id = `rule-field-${key}-error`; fieldError.hidden = true;
      wrapper.append(label, input, fieldError); fields.append(wrapper);
    }
    updateEnabledPresentation();
  };
  const renderGuide = () => {
    if (!state.currentRuleCode) return;
    const key = `rules.guide.${state.currentRuleCode}`;
    guideText.dataset.i18n = key;
    guideText.textContent = t(key);
  };
  const renderModal = () => {
    document.querySelector("#rule-modal-title").textContent = t(`rule.${state.currentRuleCode}.name`);
    document.querySelector("#rule-modal-code").textContent = state.currentRuleCode;
    enabled.checked = state.draftRuleData.enabled; renderFields(); renderGuide(); setNotice(); setBusy(false); updateEnabledPresentation();
  };
  const clearFieldError = (key) => {
    const message = document.querySelector(`#rule-field-${key}-error`); const input = form.elements.namedItem(key);
    if (message) { message.hidden = true; message.textContent = ""; } input?.removeAttribute("aria-invalid");
  };
  const showFieldError = (key, message) => {
    const fieldMessage = document.querySelector(`#rule-field-${key}-error`); const input = form.elements.namedItem(key);
    if (!fieldMessage || !input) { setNotice(message); return; }
    fieldMessage.textContent = message; fieldMessage.hidden = false; input.setAttribute("aria-invalid", "true"); input.focus();
  };
  const closeModal = () => {
    if (!modal.open || state.isSaving) return;
    modal.close(); document.body.classList.remove("modal-open");
    state.currentRuleCode = null; state.originalRuleData = null; state.draftRuleData = null; setNotice();
  };
  const request = async (url, options = {}) => {
    let response;
    try { response = await fetch(url, { headers: { "Content-Type": "application/json" }, ...options }); }
    catch { throw new Error(t(options.method === "POST" ? "rules.restore_failed" : "rules.save_failed")); }
    const text = await response.text(); let payload = {};
    if (text) { try { payload = JSON.parse(text); } catch { payload = {}; } }
    if (!response.ok) {
      const fallback = response.status === 422 ? t("rules.validation_error") : t(options.method === "POST" ? "rules.restore_failed" : "rules.save_failed");
      const issue = new Error(payload.error?.message || payload.detail?.[0]?.msg || fallback);
      issue.field = payload.error?.details?.field || payload.detail?.[0]?.loc?.at(-1); issue.status = response.status; throw issue;
    }
    return payload;
  };
  const openRule = async (code) => {
    if (state.isSaving) return;
    try {
      const data = await request(`/api/rules/${encodeURIComponent(code)}`);
      state.currentRuleCode = code; state.originalRuleData = clone(data); state.draftRuleData = clone(data);
      renderModal(); modal.showModal(); document.body.classList.add("modal-open"); closeButton.focus();
    } catch (issue) { showToast(issue.message || t("rules.load_failed")); }
  };
  const validateDraft = () => {
    let firstError = null; const configuration = {};
    for (const input of fields.querySelectorAll("input")) {
      clearFieldError(input.name); const definition = fieldDefinitions[input.name]; const value = Number(input.value);
      let message = "";
      if (input.value.trim() === "" || !Number.isFinite(value)) message = t("rules.validation_number");
      else if (definition.integer && !Number.isInteger(value)) message = t("rules.validation_integer");
      else if (definition.exclusiveMin !== undefined && value <= definition.exclusiveMin) message = t("rules.validation_greater_than_one");
      else if (value < definition.min) message = `${t("rules.validation_minimum")} ${definition.min}.`;
      else if (value > definition.max) message = `${t("rules.validation_maximum")} ${definition.max}.`;
      if (message && !firstError) firstError = { key: input.name, message };
      configuration[input.name] = definition.integer ? Number.parseInt(input.value, 10) : value;
    }
    if (!firstError && state.currentRuleCode === "BUDGET_DEVIATION") {
      if (!(configuration.medium_threshold_percentage < configuration.high_threshold_percentage && configuration.high_threshold_percentage < configuration.critical_threshold_percentage)) {
        firstError = { key: "medium_threshold_percentage", message: t("rules.validation_threshold_order") };
      }
    }
    if (firstError) { showFieldError(firstError.key, firstError.message); return null; }
    state.draftRuleData.configuration = configuration; return configuration;
  };
  const updateCard = (rule) => {
    const card = document.querySelector(`[data-rule-code="${rule.rule_code}"]`); if (!card) return;
    const badge = card.querySelector("[data-rule-state]"); badge.className = `rule-state ${rule.enabled ? "active" : "disabled"}`;
    badge.dataset.i18n = rule.enabled ? "rules.enabled" : "rules.disabled_state"; badge.textContent = t(badge.dataset.i18n);
    const summary = card.querySelector("[data-rule-config]"); summary.replaceChildren(); const entries = Object.entries(rule.configuration);
    if (!entries.length) { const item = document.createElement("small"); item.textContent = t("rules.fixed_logic"); summary.append(item); }
    for (const [key, value] of entries) { const item = document.createElement("small"); const label = document.createElement("b"); label.textContent = t(`rules.field.${key}`); item.append(label, `: ${value}`); summary.append(item); }
    card.querySelector('[data-stat="executions"]').textContent = rule.statistics.total_executions;
    card.querySelector('[data-stat="findings"]').textContent = rule.statistics.total_findings;
    const status = card.querySelector('[data-stat="status"]'); status.dataset.i18nValue = rule.statistics.last_status || "not_run"; status.textContent = dynamic("status", status.dataset.i18nValue);
    const updated = card.querySelector("[data-rule-updated]"); updated.dateTime = rule.updated_at; updated.textContent = new Date(rule.updated_at).toLocaleString(window.NOAMSI18n?.currentLanguage() || "en");
    const badges = [...document.querySelectorAll("[data-rule-state]")];
    document.querySelector("#rules-active").textContent = badges.filter((item) => item.classList.contains("active")).length;
    document.querySelector("#rules-disabled").textContent = badges.filter((item) => item.classList.contains("disabled")).length;
  };

  document.querySelectorAll("[data-configure-rule]").forEach((button) => button.addEventListener("click", () => openRule(button.dataset.configureRule)));
  enabled.addEventListener("change", updateEnabledPresentation);
  closeButton.addEventListener("click", closeModal); cancelButton.addEventListener("click", closeModal);
  modal.addEventListener("cancel", (event) => { event.preventDefault(); closeModal(); });
  modal.addEventListener("click", (event) => { if (event.target === modal) closeModal(); });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && modal.open) { event.preventDefault(); closeModal(); }
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault(); if (state.isSaving) return; setNotice(); const configuration = validateDraft(); if (!configuration) return;
    setBusy(true, "save");
    try {
      const rule = await request(`/api/rules/${encodeURIComponent(state.currentRuleCode)}`, { method: "PATCH", body: JSON.stringify({ enabled: enabled.checked, configuration }) });
      updateCard(rule); state.originalRuleData = clone(rule); state.draftRuleData = clone(rule); setBusy(false); closeModal(); showToast(t("rules.changes_saved"));
    } catch (issue) { setBusy(false); issue.field ? showFieldError(issue.field, issue.message) : setNotice(issue.message || t("rules.save_failed")); }
  });
  resetButton.addEventListener("click", async () => {
    if (state.isSaving || !window.confirm(t("rules.restore_confirm"))) return;
    setNotice(); setBusy(true, "reset");
    try {
      let rule = await request(`/api/rules/${encodeURIComponent(state.currentRuleCode)}/reset`, { method: "POST" });
      if (!rule.rule_code) rule = await request(`/api/rules/${encodeURIComponent(state.currentRuleCode)}`);
      updateCard(rule); state.originalRuleData = clone(rule); state.draftRuleData = clone(rule); renderModal(); setNotice(t("rules.defaults_restored"), true); showToast(t("rules.defaults_restored"));
    } catch (issue) { setBusy(false); setNotice(issue.message || t("rules.restore_failed")); }
  });
  document.addEventListener("noams:languagechange", () => {
    if (state.draftRuleData && modal.open) { renderFields(); renderGuide(); updateEnabledPresentation(); }
  });
})();
