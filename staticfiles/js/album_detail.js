// -------------------- static/js/album_detail.js --------------------
(() => {
  "use strict";
  const U = window.AlbumUtils || {};

  // ========== Track DELETE (🗑) ==========
  U.onModalShow &&
    U.onModalShow("deleteTrackModal", ({ modal, trigger }) => {
      if (!trigger) return;
      const trackId = trigger.getAttribute("data-track-id");
      const trackName = trigger.getAttribute("data-track-name") || "";
      modal.querySelector("#deleteTrackName").textContent = trackName;

      // Endpoint to delete the track entirely
      const form = modal.querySelector("#deleteTrackForm");
      form.action = `/tracks/${trackId}/delete/`;
    });

  document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("deleteTrackForm");
    if (!form) return;
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        const res = await fetch(form.action, { method: "POST", headers: { "X-CSRFToken": U.getCSRF() } });
        const data = await res.json();
        if (data.ok) {
          // Try to remove by track id, fallback to album item id if provided
          let row = null;
          if (data.id) row = document.querySelector(`#track-list li[data-track-id="${data.id}"]`);
          if (!row && data.album_item_id) row = document.querySelector(`#track-list li[data-id="${data.album_item_id}"]`);
          if (row) row.remove();
          bootstrap.Modal.getInstance(document.getElementById("deleteTrackModal"))?.hide();
        } else {
          alert(data.error || "Failed to delete track.");
        }
      } catch (err) {
        console.error("Delete track error:", err);
        alert("Network error while deleting track.");
      }
    });
  });

  // ========== Track DETACH (⛔ remove from THIS album only) ==========
  document.addEventListener("click", async (e) => {
    const btn = e.target.closest(".js-detach[data-detach-url]");
    if (!btn) return;
    e.preventDefault();
    try {
      const res = await fetch(btn.getAttribute("data-detach-url"), {
        method: "POST",
        headers: { "X-CSRFToken": U.getCSRF() },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const row = btn.closest("li.list-group-item");
      if (row) row.remove();
    } catch (err) {
      console.error("Detach error:", err);
      alert("Failed to remove track from album.");
    }
  });

  // ========== Track RENAME (modal populate only; submit can be normal POST) ==========
  U.onModalShow &&
    U.onModalShow("renameTrackModal", ({ modal, trigger }) => {
      if (!trigger) return;
      const currentName = trigger.getAttribute("data-track-name") || "";
      const url = trigger.getAttribute("data-url"); // album/<pk>/tracks/<item_id>/rename/
      modal.querySelector("#renameTrackInput").value = currentName;
      modal.querySelector("#renameTrackForm").action = url;
    });
})();

// -------------------- Album Detail: in-album track search --------------------
(function () {
  "use strict";

  function filterTrackList(inputEl) {
    const q = (inputEl.value || "").trim().toLowerCase();
    const targetSel = inputEl.getAttribute("data-target");
    if (!targetSel) return;

    const list = document.querySelector(targetSel);
    if (!list) return;

    const items = Array.from(list.querySelectorAll("li.track-card"));
    let matchCount = 0;

    // Simple text getter (title span preferred)
    const getText = (li) => {
      const titleEl = li.querySelector('[data-role="track-title"], .fw-semibold');
      const txt = titleEl ? titleEl.textContent : li.textContent;
      return (txt || "").toLowerCase();
    };

    items.forEach((li) => {
      const visible = !q || getText(li).includes(q);
      li.classList.toggle("d-none", !visible);
      if (visible) matchCount += 1;
    });

    // No results row
    let emptyRow = list.querySelector(".no-results-row");
    if (!emptyRow) {
      emptyRow = document.createElement("li");
      emptyRow.className = "list-group-item text-muted no-results-row d-none";
      emptyRow.textContent = "No matching tracks.";
      list.appendChild(emptyRow);
    }
    emptyRow.classList.toggle("d-none", matchCount !== 0);
  }

  // Input typing -> filter
  document.addEventListener("input", (e) => {
    const el = e.target;
    if (el && el.classList && el.classList.contains("album-track-search")) {
      filterTrackList(el);
    }
  });

  // Clear button -> empty + refilter
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".album-track-search-clear");
    if (!btn) return;
    const group = btn.closest("[data-album-search]");
    const input = group ? group.querySelector(".album-track-search") : null;
    if (input) {
      input.value = "";
      filterTrackList(input);
      input.focus();
    }
  });

  // If tracks are lazy-loaded/re-rendered, reapply filter if a query is present.
  // Observe any UL with id="album-tracklist-<id>"
  const trackLists = document.querySelectorAll('ul[id^="album-tracklist-"]');
  const mo = new MutationObserver((mutations) => {
    for (const m of mutations) {
      if (m.type === "childList") {
        const list = m.target;
        const albumId = list.getAttribute("data-album-id");
        if (!albumId) continue;
        const searchBox = document.querySelector(`[data-album-search="${albumId}"] .album-track-search`);
        if (searchBox && searchBox.value.trim() !== "") {
          filterTrackList(searchBox);
        }
      }
    }
  });
  trackLists.forEach((ul) => mo.observe(ul, { childList: true }));
})();
