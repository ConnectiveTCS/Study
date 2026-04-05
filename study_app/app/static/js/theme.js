/**
 * theme.js — Manages dark/light mode and custom colour theme
 * Persists choices in localStorage and optionally syncs to server for logged-in users.
 */

(function () {
  const root = document.documentElement;
  const themeVarsEl = document.getElementById("theme-vars");

  // ---------- Dark / Light Toggle ----------
  window.toggleTheme = function () {
    const current = root.getAttribute("data-theme");
    const next = current === "dark" ? "light" : "dark";
    applyThemeMode(next);
    persistTheme();
  };

  function applyThemeMode(mode) {
    root.setAttribute("data-theme", mode);
    const wrapper = document.getElementById("theme-icon");
    const label = document.getElementById("theme-label");
    if (wrapper) {
      wrapper.innerHTML = `<i data-lucide="${mode === "dark" ? "sun" : "moon"}"></i>`;
      if (window.lucide)
        lucide.createIcons({ nodes: [wrapper.firstElementChild] });
    }
    if (label) label.textContent = mode === "dark" ? "Light Mode" : "Dark Mode";
  }

  // ---------- Colour Picker ----------
  /**
   * updateThemeColor(property, hexValue)
   * property: 'primary' | 'accent' | 'background'
   */
  window.updateThemeColor = function (property, value) {
    const map = {
      primary: "--primary",
      accent: "--accent",
      background: "--bg",
    };
    const cssVar = map[property];
    if (!cssVar) return;
    root.style.setProperty(cssVar, value);
    updateThemeStyleTag();
    persistTheme();
  };

  function updateThemeStyleTag() {
    if (!themeVarsEl) return;
    const primary =
      root.style.getPropertyValue("--primary") ||
      getComputedStyle(root).getPropertyValue("--primary");
    const accent =
      root.style.getPropertyValue("--accent") ||
      getComputedStyle(root).getPropertyValue("--accent");
    const bg =
      root.style.getPropertyValue("--bg") ||
      getComputedStyle(root).getPropertyValue("--bg");
    themeVarsEl.textContent = `:root { --primary: ${primary}; --accent: ${accent}; --bg: ${bg}; --grad-1: ${primary}; }`;
  }

  // ---------- Persistence ----------
  function persistTheme() {
    const prefs = {
      mode: root.getAttribute("data-theme"),
      primary:
        root.style.getPropertyValue("--primary") ||
        getComputedStyle(root).getPropertyValue("--primary").trim(),
      accent:
        root.style.getPropertyValue("--accent") ||
        getComputedStyle(root).getPropertyValue("--accent").trim(),
      background:
        root.style.getPropertyValue("--bg") ||
        getComputedStyle(root).getPropertyValue("--bg").trim(),
    };

    localStorage.setItem("studyforce_theme", JSON.stringify(prefs));

    // Sync to server if logged in
    fetch("/auth/theme", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify(prefs),
    }).catch(() => {}); // silently fail if not logged in
  }

  function loadThemeFromStorage() {
    const raw = localStorage.getItem("studyforce_theme");
    if (!raw) return;
    try {
      const prefs = JSON.parse(raw);
      if (prefs.mode) applyThemeMode(prefs.mode);
      if (prefs.primary) root.style.setProperty("--primary", prefs.primary);
      if (prefs.accent) root.style.setProperty("--accent", prefs.accent);
      if (prefs.background) root.style.setProperty("--bg", prefs.background);
      updateThemeStyleTag();
    } catch (_) {
      /* ignore parse errors */
    }
  }

  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.getAttribute("content");
    const input = document.querySelector('input[name="csrf_token"]');
    return input ? input.value : "";
  }

  // On page load: apply persisted theme before rendering
  loadThemeFromStorage();

  // Expose internals needed by profile page
  window.applyThemeMode = applyThemeMode;
  window.persistTheme = persistTheme;
})();
