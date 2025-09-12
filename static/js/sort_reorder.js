// -------------------- static/js/sort_reorder.js --------------------
(function () {
  "use strict";

  // --- CSRF ---
  function getCookie(name) {
    let val = null;
    if (document.cookie && document.cookie !== "") {
      for (let c of document.cookie.split(";")) {
        c = c.trim();
        if (c.startsWith(name + "=")) {
          val = decodeURIComponent(c.slice(name.length + 1));
          break;
        }
      }
    }
    return val;
  }
  const csrftoken = getCookie("csrftoken");

  async function postJSON(url, payload) {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrftoken,
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify(payload || {}),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const ct = res.headers.get("content-type") || "";
    return ct.includes("application/json") ? res.json() : res.text();
  }

  function makeSortable(container, itemSelector) {
    if (!container) return;
    let dragItem = null;

    container.addEventListener("dragstart", (e) => {
      const target = e.target.closest(itemSelector);
      if (!target) return;
      dragItem = target;
      e.dataTransfer.effectAllowed = "move";
    });

    container.addEventListener("dragover", (e) => {
      e.preventDefault();
      if (!dragItem) return;
      const items = Array.from(container.querySelectorAll(itemSelector));
      const after = items.find((el) => {
        if (el === dragItem) return false;
        const rect = el.getBoundingClientRect();
        return e.clientY <= rect.top + rect.height / 2;
      });
      if (after) {
        container.insertBefore(dragItem, after);
      } else {
        container.appendChild(dragItem);
      }
    });

    container.addEventListener("dragend", () => {
      if (!dragItem) return;
      saveOrder(container).catch(console.error);
      dragItem = null;
    });
  }

  async function saveOrder(container) {
    // Are we inside an album card?
    const albumCard = container.closest("li.album");
    const idsFrom = (sel, attr) =>
      Array.from(container.querySelectorAll(sel))
        .map((el) => parseInt(el.getAttribute(attr), 10))
        .filter((n) => Number.isInteger(n));

    if (albumCard) {
      // Album track reordering: li[data-id] holds AlbumTrack.id from your template
      const atIds = idsFrom("li[data-id]", "data-id");
      if (!atIds.length) return;

      // Prefer data attribute if you add it in the template; otherwise default
      let url = albumCard.dataset.reorderUrl || `/album/${parseInt(albumCard.dataset.id, 10)}/tracks/reorder/`;

      // Normalize accidental plurals
      url = url.replace("/albums/", "/album/");

      const data = await postJSON(url, { order: atIds });
      container.dispatchEvent(new CustomEvent("list:reordered", { detail: { scope: "album", ids: atIds, response: data } }));
      return;
    }

    // Global track reordering fallback
    // Accept li[data-id] (track id) or li[data-track-id]
    const tIds = Array.from(container.querySelectorAll("li[data-id], li[data-track-id]"))
      .map((el) => parseInt(el.getAttribute("data-id") || el.getAttribute("data-track-id"), 10))
      .filter((n) => Number.isInteger(n));

    if (!tIds.length) return;

    const globalUrl = window.TRACKS_REORDER_URL || "/tracks/api/tracks/reorder/";

    const data = await postJSON(globalUrl, { order: tIds });
    container.dispatchEvent(new CustomEvent("list:reordered", { detail: { scope: "global", ids: tIds, response: data } }));
  }

  // Init: album track lists (your album card uses <ul class="list-group">)
  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("li.album ul.list-group").forEach((ul) => {
      makeSortable(ul, "li.list-group-item");
    });
    // If you also have a standalone global list, init it here as needed:
    // const globalList = document.querySelector("#tracks-global");
    // if (globalList) makeSortable(globalList, "li");
  });
})();
