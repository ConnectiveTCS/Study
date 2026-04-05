/**
 * toast.js — Programmatic toast notification system
 *
 * Usage:
 *   showToast({ title: 'Saved!', message: 'Your note was saved.', type: 'success' })
 *   type: 'success' | 'danger' | 'warning' | 'info'
 */
(function () {
  const ICONS = {
    success: '<i data-lucide="check-circle-2"></i>',
    danger: '<i data-lucide="x-circle"></i>',
    warning: '<i data-lucide="alert-triangle"></i>',
    info: '<i data-lucide="info"></i>',
    badge: '<i data-lucide="trophy"></i>',
  };
  const AUTO_DISMISS_MS = 4500;

  window.showToast = function ({
    title = "",
    message = "",
    type = "info",
    duration = AUTO_DISMISS_MS,
  } = {}) {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = "toast";
    toast.setAttribute("role", "alert");
    toast.setAttribute("aria-live", "assertive");
    toast.innerHTML = `
      <span class="toast-icon" aria-hidden="true">${ICONS[type] || ICONS.info}</span>
      <div class="toast-body">
        ${title ? `<div class="toast-title">${sanitize(title)}</div>` : ""}
        ${message ? `<div class="toast-msg">${sanitize(message)}</div>` : ""}
      </div>
      <button class="toast-close" aria-label="Dismiss notification">×</button>
    `;

    container.appendChild(toast);
    if (window.lucide)
      lucide.createIcons({ nodes: [toast.querySelector(".toast-icon")] });

    const dismiss = () => {
      toast.classList.add("removing");
      toast.addEventListener("animationend", () => toast.remove(), {
        once: true,
      });
    };

    toast.querySelector(".toast-close").addEventListener("click", dismiss);
    if (duration > 0) setTimeout(dismiss, duration);
  };

  function sanitize(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // Expose for external use
  window.ToastType = {
    SUCCESS: "success",
    DANGER: "danger",
    WARNING: "warning",
    INFO: "info",
  };
})();
