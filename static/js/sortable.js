// static/js/sortable.js
(function () {
  "use strict";

  function getCookie(name) {
    let v = null;
    if (document.cookie) {
      for (const part of document.cookie.split(";")) {
        const c = part.trim();
        if (c.startsWith(name + "=")) {
          v = decodeURIComponent(c.slice(name.length + 1));
          break;
        }
      }
    }
    return v;
  }
  const CSRF = getCookie("csrftoken");

  const lists = document.querySelectorAll("[data-reorder-url]");
  if (!lists.length) return;

  lists.forEach((list) => {
    // Ensure immediate children are draggable (safe even if already set)
    list.querySelectorAll(":scope > li").forEach((li) => {
      if (!li.hasAttribute("draggable")) li.setAttribute("draggable", "true");
    });

    let dragEl = null;

    list.addEventListener("dragstart", (e) => {
      const li = e.target.closest("li[data-id]");
      if (!li) return;

      // Don't start drag from interactive controls
      if (
        e.target.closest("button, a, input, textarea, select, label, .js-fav, .js-save, .rename-track-btn, .js-detach, .add-to-playlist, .rename-album-btn")
      ) {
        e.preventDefault();
        return;
      }

      dragEl = li;
      li.classList.add("dragging");
      e.dataTransfer.effectAllowed = "move";
      try {
        e.dataTransfer.setData("text/plain", li.dataset.id);
      } catch {}
    });

    list.addEventListener("dragover", (e) => {
      if (!dragEl) return;
      if (dragEl.parentElement !== list) return; // keep inside same <ul>
      e.preventDefault();

      const after = getAfter(list, e.clientY);
      if (after == null) list.appendChild(dragEl);
      else list.insertBefore(dragEl, after);
    });

    list.addEventListener("drop", (e) => e.preventDefault());

    list.addEventListener("dragend", async () => {
      if (!dragEl) return;
      dragEl.classList.remove("dragging");

      // Collect the new order
      const ids = [...list.querySelectorAll(":scope > li[data-id]")].map((li) => {
        const id = li.dataset.id;
        return /^\d+$/.test(id) ? parseInt(id, 10) : id;
      });

      try {
        const res = await fetch(list.dataset.reorderUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": CSRF || "",
          },
          body: JSON.stringify({ order: ids }),
        });
        if (!res.ok) throw new Error("HTTP " + res.status);
        await res.json();
      } catch (err) {
        console.error("Reorder save failed:", err);
        alert("Couldn't save order. Please try again.");
      } finally {
        dragEl = null;
      }
    });
  });

  function getAfter(container, y) {
    // IMPORTANT: don't rely on a class that may not exist; use all child LIs
    const els = [...container.querySelectorAll(":scope > li:not(.dragging)")];
    let closest = { offset: Number.NEGATIVE_INFINITY, el: null };
    for (const el of els) {
      const box = el.getBoundingClientRect();
      const offset = y - (box.top + box.height / 2);
      if (offset < 0 && offset > closest.offset) closest = { offset, el };
    }
    return closest.el;
  }
})();
