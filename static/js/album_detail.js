// static/js/album_detail.js
(function () {
  "use strict";

  const list = document.getElementById("track-list");
  if (!list) return;

  // Helper: find the element you should insert before based on mouse Y
  function getDragAfterElement(container, y) {
    const els = [...container.querySelectorAll("li[data-id]:not(.dragging)")];
    let closest = { offset: Number.NEGATIVE_INFINITY, element: null };

    for (const el of els) {
      const box = el.getBoundingClientRect();
      const offset = y - (box.top + box.height / 2);
      // We want the *first* element whose middle is below the cursor (offset < 0),
      // but closest to it (largest offset)
      if (offset < 0 && offset > closest.offset) {
        closest = { offset, element: el };
      }
    }
    return closest.element;
  }

  let dragItem = null;

  // Start dragging
  list.addEventListener("dragstart", (e) => {
    const li = e.target.closest("li[data-id]");
    if (!li) return;
    dragItem = li;
    li.classList.add("dragging");
    e.dataTransfer.effectAllowed = "move";
    // Some browsers need non-empty data to initiate DnD
    try {
      e.dataTransfer.setData("text/plain", li.dataset.id);
    } catch {}
  });

  // Reorder in-place while dragging
  list.addEventListener("dragover", (e) => {
    e.preventDefault(); // allow drop
    if (!dragItem) return;
    const after = getDragAfterElement(list, e.clientY);
    if (after == null) {
      list.appendChild(dragItem);
    } else {
      list.insertBefore(dragItem, after);
    }
  });

  // Clean up class when leaving
  list.addEventListener("dragend", () => {
    if (dragItem) dragItem.classList.remove("dragging");
    dragItem = null;

    // Read the *current* DOM order (AlbumTrack IDs)
    const ids = Array.from(list.querySelectorAll("li[data-id]")).map((li) => parseInt(li.dataset.id, 10));

    console.log("Saving album order:", ids);

    const url = list.dataset.reorderUrl;
    fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"), // defined in static/js/cookies.js
      },
      body: JSON.stringify({ order: ids }),
    })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        console.log("Server response:", data);
      })
      .catch((err) => {
        console.error("Reorder error:", err);
        alert("Failed to save order. Please try again.");
      });
  });
})();
