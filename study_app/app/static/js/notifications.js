/**
 * notifications.js — Poll in-app notifications and register browser push
 */
(function () {
  const POLL_INTERVAL_MS = 60000; // poll every 60 seconds

  // ---------- In-app polling ----------
  function pollNotifications() {
    fetch("/notifications/unread-count")
      .then((r) => r.json())
      .then((data) => {
        const badge = document.querySelectorAll(".notif-badge");
        badge.forEach((el) => {
          el.textContent = data.count || "";
          el.style.display = data.count > 0 ? "inline-flex" : "none";
        });
      })
      .catch(() => {}); // silently fail if offline
  }

  setInterval(pollNotifications, POLL_INTERVAL_MS);

  // ---------- Browser Push Registration ----------
  const vapidPublicKey = document.body.dataset.vapidPublicKey;

  if (
    vapidPublicKey &&
    "serviceWorker" in navigator &&
    "PushManager" in window
  ) {
    navigator.serviceWorker.ready
      .then((registration) => {
        registration.pushManager.getSubscription().then((existing) => {
          if (existing) return; // already subscribed
          // Only request permission if user has interacted
          // (will be called from a settings page button, not auto-trigger)
        });
      })
      .catch(() => {});
  }

  window.subscribeToPush = function () {
    if (!vapidPublicKey) return Promise.reject("No VAPID key");
    return navigator.serviceWorker.ready
      .then((reg) =>
        reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
        }),
      )
      .then((sub) =>
        fetch("/notifications/push/subscribe", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrf(),
          },
          body: JSON.stringify(sub.toJSON()),
        }),
      );
  };

  function urlBase64ToUint8Array(base64String) {
    const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding)
      .replace(/-/g, "+")
      .replace(/_/g, "/");
    const raw = window.atob(base64);
    return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
  }

  function getCsrf() {
    const input = document.querySelector('input[name="csrf_token"]');
    return input ? input.value : "";
  }
})();
