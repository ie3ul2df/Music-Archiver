// --------------------------- static/js/track_list.js ---------------------------//
const trackListNotify = (message, level) => {
  if (typeof window.showMessage === "function") {
    return window.showMessage(message, level);
  }
  if (typeof window.alert === "function") {
    window.alert(message);
  }
  return false;
};
/* ---------------- CSRF helpers (global) ----------------
   We expose window.getCookie and window.getCSRF so all IIFEs can use them. */
(function () {
  if (typeof window.getCookie !== "function") {
    window.getCookie = function getCookie(name) {
      let cookieValue = null;
      if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
          const cookie = cookies[i].trim();
          if (cookie.substring(0, name.length + 1) === name + "=") {
            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
            break;
          }
        }
      }
      return cookieValue;
    };
  }
  if (typeof window.getCSRF !== "function") {
    window.getCSRF = function getCSRF() {
      return window.getCookie("csrftoken") || "";
    };
  }
})();

// --------------------------- MAIN: albums & tracks sortable, helpers ---------------------------//
(function () {
  "use strict";

  // Generic POST JSON utility with CSRF
  async function postJSON(url, payload) {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "X-CSRFToken": getCSRF(),
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
      credentials: "same-origin",
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`POST ${url} → ${res.status} ${res.statusText} ${text.slice(0, 200)}`);
    }
    return res.json().catch(() => ({}));
  }

  // ----------------------------- INIT SORTABLES -------------------------------
  document.addEventListener("DOMContentLoaded", () => {
    // Global Check/Uncheck All
    const globalBtn = document.getElementById("check-all-global");
    if (globalBtn) {
      globalBtn.addEventListener("click", () => {
        const checks = document.querySelectorAll(".track-check");
        const allChecked = [...checks].every((cb) => cb.checked);
        checks.forEach((cb) => (cb.checked = !allChecked));
        globalBtn.textContent = allChecked ? "✔ All" : "✖ None";
      });
    }
  });

  // ----------------------- Album-level "Check All" toggle ---------------------
  document.addEventListener("change", (e) => {
    if (!e.target.classList.contains("check-all")) return;
    const album = e.target.closest(".album");
    if (!album) return;
    album.querySelectorAll(".track-check").forEach((cb) => (cb.checked = e.target.checked));
  });

  // No-op, music_player.js may hook into dragend if needed
  document.addEventListener("dragend", () => {});
})();

// ----------------------- Clear recent tracks list ----------------------- //
document.addEventListener("DOMContentLoaded", () => {
  const clearBtn = document.getElementById("clear-recent");
  // const list = document.getElementById("recent-list");
  const list = document.getElementById("recent-tracks");

  if (clearBtn && list) {
    clearBtn.addEventListener("click", async () => {
      if (!confirm("Clear all recently played tracks?")) return;

      try {
        const res = await fetch(clearBtn.dataset.url, {
          method: "POST",
          headers: {
            "X-CSRFToken": getCSRF(),
            Accept: "application/json",
          },
          credentials: "same-origin",
        });
        const data = await res.json().catch(() => ({}));

        if (data && data.ok) {
          list.innerHTML = '<li class="list-group-item text-muted">No recently played tracks.</li>';
        } else {
          trackListNotify((data && data.error) || "Failed to clear recent list.", "danger");
        }
      } catch (err) {
        console.error("Error clearing recent list:", err);
      }
    });
  }
});
