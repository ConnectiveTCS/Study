/** sidebar.js — Collapse/expand sidebar and persist state */
(function () {
  const sidebar = document.getElementById("sidebar");
  const content = document.getElementById("app-content");
  const collapseIcon = document.getElementById("collapse-icon");

  function applyCollapse(collapsed) {
    if (!sidebar) return;
    if (collapsed) {
      sidebar.classList.add("collapsed");
      if (content) content.classList.add("sidebar-collapsed");
      if (collapseIcon) collapseIcon.textContent = "▶";
    } else {
      sidebar.classList.remove("collapsed");
      if (content) content.classList.remove("sidebar-collapsed");
      if (collapseIcon) collapseIcon.textContent = "◀";
    }
  }

  window.toggleSidebar = function () {
    if (!sidebar) return;
    const isCollapsed = sidebar.classList.contains("collapsed");
    const next = !isCollapsed;
    applyCollapse(next);
    localStorage.setItem("sidebar_collapsed", String(next));
  };

  // Restore state
  const stored = localStorage.getItem("sidebar_collapsed");
  if (stored === "true") applyCollapse(true);
})();
