(() => {
  const modal = document.querySelector("#settings-modal");
  const openButtons = document.querySelectorAll("[data-settings-open]");
  const closeButton = modal?.querySelector("[data-settings-close]");
  const themeSelect = document.querySelector("#theme-select");
  const languageSelect = document.querySelector("#language-select");
  let previousFocus = null;

  const applyTheme = (theme) => {
    const selected = theme === "light" ? "light" : "dark";
    document.documentElement.dataset.theme = selected;
    localStorage.setItem("noams.theme", selected);
    if (themeSelect) themeSelect.value = selected;
  };

  const applyLanguage = (language) => {
    const selected = language === "es" ? "es" : "en";
    localStorage.setItem("noams.language", selected);
    if (languageSelect) languageSelect.value = selected;
    window.NOAMSI18n?.apply();
  };

  const openSettings = (event) => {
    previousFocus = event?.currentTarget || document.activeElement;
    openButtons.forEach((button) => button.setAttribute("aria-expanded", "true"));
    document.body.classList.add("settings-open");
    modal.showModal();
    closeButton?.focus();
  };

  const closeSettings = () => {
    if (!modal?.open) return;
    modal.close();
    document.body.classList.remove("settings-open");
    openButtons.forEach((button) => button.setAttribute("aria-expanded", "false"));
    previousFocus?.focus();
  };

  applyTheme(localStorage.getItem("noams.theme"));
  if (languageSelect) languageSelect.value = window.NOAMSI18n?.currentLanguage() || "en";
  openButtons.forEach((button) => button.addEventListener("click", openSettings));
  closeButton?.addEventListener("click", closeSettings);
  modal?.addEventListener("click", (event) => { if (event.target === modal) closeSettings(); });
  modal?.addEventListener("cancel", (event) => { event.preventDefault(); closeSettings(); });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && modal?.open) {
      event.preventDefault();
      closeSettings();
    }
  });
  themeSelect?.addEventListener("change", () => applyTheme(themeSelect.value));
  languageSelect?.addEventListener("change", () => applyLanguage(languageSelect.value));
})();
