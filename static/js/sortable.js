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
    // mark immediate children draggable if not already
    list.querySelectorAll(":scope > li").forEach((li) => {
      if (!li.hasAttribute("draggable")) li.setAttribute("draggable", "true");
      li.classList.add("reorder-item");
    });

    let dragEl = null;

    list.addEventListener("dragstart", (e) => {
      const li = e.target.closest("li[data-id]");
      if (!li) return;
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
      const ids = [...list.querySelectorAll(":scope > li[data-id]")].map((li) => {
        const id = li.dataset.id;
        return /^\d+$/.test(id) ? parseInt(id, 10) : id; // supports numeric or string ids
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
    const els = [...container.querySelectorAll(":scope > li.reorder-item:not(.dragging)")];
    let closest = { offset: Number.NEGATIVE_INFINITY, el: null };
    for (const el of els) {
      const box = el.getBoundingClientRect();
      const offset = y - (box.top + box.height / 2);
      if (offset < 0 && offset > closest.offset) closest = { offset, el };
    }
    return closest.el;
  }
})();
