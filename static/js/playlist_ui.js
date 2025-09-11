// -------------------- static/js/playlist_ui.js --------------------
(function () {
  "use strict";

  // --- CSRF ---
  function getCookie(name) {
    let val = null;
    if (document.cookie && document.cookie !== "") {
      const parts = document.cookie.split(";");
      for (let c of parts) {
        c = c.trim();
        if (c.startsWith(name + "=")) {
          val = decodeURIComponent(c.slice(name.length + 1));
          break;
        }
      }
    }
    return val;
  }
  const CSRF = getCookie("csrftoken");

  // --- Server-provided membership: #playlist-meta[data-in-ids="1,2,3"] ---
  const metaEl = document.getElementById("playlist-meta");
  const IN_SET = new Set(
    (metaEl?.dataset?.inIds || "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
  );

  // --- Helpers ---
  function setPlaylistBtnState(btn, inPlaylist) {
    btn.setAttribute("aria-pressed", inPlaylist ? "true" : "false");
    btn.classList.toggle("btn-success", inPlaylist);
    btn.classList.toggle("btn-outline-success", !inPlaylist);
    btn.textContent = inPlaylist ? "✓" : "➕";
  }

  function getInitialInState(btn) {
    // Prefer authoritative global set from server:
    const idStr = (btn.dataset.track || "").trim();
    if (idStr && IN_SET.has(idStr)) return true;

    // Optional server hint:
    if (btn.dataset.in === "1") return true;
    if (btn.dataset.in === "0") return false;

    // Fallbacks from current markup:
    const aria = (btn.getAttribute("aria-pressed") || "").toLowerCase();
    if (aria === "true") return true;
    if (aria === "false") return false;

    return btn.classList.contains("btn-success");
  }

  function normalizePlaylistButtons(root = document) {
    root.querySelectorAll(".add-to-playlist").forEach((btn) => {
      setPlaylistBtnState(btn, getInitialInState(btn));
    });
  }

  // Expose for other scripts (e.g., after AJAX insert)
  window.normalizePlaylistButtons = normalizePlaylistButtons;

  // Normalize once DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => normalizePlaylistButtons(document));
  } else {
    normalizePlaylistButtons(document);
  }

  // 🔭 Watch for AJAX-inserted content (Album → Show tracks)
  const observer = new MutationObserver((mutations) => {
    for (const m of mutations) {
      for (const node of m.addedNodes) {
        if (!(node instanceof Element)) continue;
        // If the node itself is a button:
        if (node.classList?.contains("add-to-playlist")) {
          normalizePlaylistButtons(node.parentNode || node);
          continue;
        }
        // Or if it contains any buttons:
        const hasBtn = node.querySelector?.(".add-to-playlist");
        if (hasBtn) normalizePlaylistButtons(node);
      }
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });

  // --- Toggle (event delegation; works for dynamic nodes) ---
  document.addEventListener("click", async (e) => {
    const btn = e.target.closest(".add-to-playlist");
    if (!btn) return;

    const url = btn.dataset.url; // /playlist/toggle/<id>/
    const trackId = (btn.dataset.track || "").trim();
    const originalText = btn.textContent;
    btn.disabled = true;

    try {
      const res = await fetch(url, {
        method: "POST",
        headers: {
          "X-CSRFToken": CSRF,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error("Toggle failed");

      const inPlaylist = !!data.in_playlist;

      // Keep global truth in sync for subsequent hydrations
      if (trackId) {
        if (inPlaylist) IN_SET.add(trackId);
        else IN_SET.delete(trackId);
      }

      // Update all buttons for this track across the page
      document
        .querySelectorAll(`.add-to-playlist[data-track="${trackId}"]`)
        .forEach((b) => setPlaylistBtnState(b, inPlaylist));
    } catch (err) {
      console.error(err);
      btn.textContent = "⚠ Error";
      setTimeout(() => (btn.textContent = originalText), 1200);
    } finally {
      btn.disabled = false;
    }
  });

  // --- Reorder in playlist (unchanged) ---
  const list = document.getElementById("playlist-tracks");
  if (list) {
    let dragging = null;

    list.addEventListener("dragstart", (e) => {
      const li = e.target.closest(".track-item");
      if (!li) return;
      dragging = li;
      li.classList.add("dragging");
      e.dataTransfer.effectAllowed = "move";
    });

    list.addEventListener("dragend", () => {
      if (dragging) dragging.classList.remove("dragging");
      dragging = null;

      const url = list.dataset.reorderUrl;
      const order = [...list.querySelectorAll(".track-item")].map((el) =>
        parseInt(el.dataset.itemid, 10)
      );
      fetch(url, {
        method: "POST",
        headers: {
          "X-CSRFToken": CSRF,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ order }),
      }).catch((err) => console.error(err));
    });

    list.addEventListener("dragover", (e) => {
      e.preventDefault();
      const after = getDragAfterElement(list, e.clientY);
      if (!after) list.appendChild(dragging);
      else list.insertBefore(dragging, after);
    });

    function getDragAfterElement(container, y) {
      const els = [...container.querySelectorAll(".track-item:not(.dragging)")];
      let closest = { offset: Number.NEGATIVE_INFINITY, element: null };
      for (const el of els) {
        const box = el.getBoundingClientRect();
        const offset = y - (box.top + box.height / 2);
        if (offset < 0 && offset > closest.offset) {
          closest = { offset, element: el };
        }
      }
      return closest.element;
    }
  }

  // --- Clear playlist (and reset all buttons) ---
  document.addEventListener("click", async (e) => {
    const btn = e.target.closest("#clear-playlist");
    if (!btn) return;

    const url = btn.dataset.url;
    btn.disabled = true;

    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "X-CSRFToken": CSRF },
      });
      if (!res.ok) throw new Error("Clear failed");

      const list = document.getElementById("playlist-tracks");
      if (list) {
        list.innerHTML =
          '<li class="list-group-item text-muted">No tracks in your playlist yet.</li>';
      }

      // Wipe global set and reset all toggles
      IN_SET.clear();
      document
        .querySelectorAll(".add-to-playlist")
        .forEach((b) => setPlaylistBtnState(b, false));
    } catch (err) {
      console.error(err);
      btn.disabled = false;
    }
  });
})();
