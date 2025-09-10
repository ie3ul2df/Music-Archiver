// -------------------- static/js/album_detail.js --------------------
(() => {
  "use strict";
  const U = window.AlbumUtils || {};

  // ========== Drag & Drop reorder (album detail only) ==========
  const list = document.getElementById("track-list");
  if (list) {
    function getDragAfterElement(container, y) {
      const els = [...container.querySelectorAll("li[data-id]:not(.dragging)")];
      let closest = { offset: Number.NEGATIVE_INFINITY, element: null };
      for (const el of els) {
        const box = el.getBoundingClientRect();
        const offset = y - (box.top + box.height / 2);
        if (offset < 0 && offset > closest.offset) closest = { offset, element: el };
      }
      return closest.element;
    }

    let dragItem = null;

    list.addEventListener("dragstart", (e) => {
      const li = e.target.closest("li[data-id]");
      if (!li) return;
      dragItem = li;
      li.classList.add("dragging");
      e.dataTransfer.effectAllowed = "move";
      try { e.dataTransfer.setData("text/plain", li.dataset.id); } catch {}
    });

    list.addEventListener("dragover", (e) => {
      e.preventDefault();
      if (!dragItem) return;
      const after = getDragAfterElement(list, e.clientY);
      if (after == null) list.appendChild(dragItem);
      else list.insertBefore(dragItem, after);
    });

    list.addEventListener("dragend", () => {
      if (dragItem) dragItem.classList.remove("dragging");
      dragItem = null;

      const ids = [...list.querySelectorAll("li[data-id]")].map((li) => parseInt(li.dataset.id, 10));
      U.postJSON(list.dataset.reorderUrl, { order: ids })
        .catch((err) => {
          console.error("Reorder error:", err);
          alert("Failed to save order.");
        });
    });
  }

  // ========== Track DELETE (🗑) ==========
  U.onModalShow && U.onModalShow("deleteTrackModal", ({ modal, trigger }) => {
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
  U.onModalShow && U.onModalShow("renameTrackModal", ({ modal, trigger }) => {
    if (!trigger) return;
    const currentName = trigger.getAttribute("data-track-name") || "";
    const url = trigger.getAttribute("data-url"); // album/<pk>/tracks/<item_id>/rename/
    modal.querySelector("#renameTrackInput").value = currentName;
    modal.querySelector("#renameTrackForm").action = url;
  });
})();
