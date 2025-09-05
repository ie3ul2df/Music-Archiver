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

document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("deleteAlbumModal");
  if (modal) {
    modal.addEventListener("show.bs.modal", function (event) {
      const button = event.relatedTarget;
      const albumId = button.getAttribute("data-album-id");
      const albumName = button.getAttribute("data-album-name");

      // Only update if element exists
      const albumNameEl = modal.querySelector("#albumName");
      if (albumNameEl) {
        albumNameEl.textContent = albumName;
      }

      // Update form action
      const form = modal.querySelector("#deleteAlbumForm");
      if (form) {
        form.action = `/album/${albumId}/delete/`;
      }
    });
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("album-search-form");
  const input = document.getElementById("album-search-input");
  const list = document.getElementById("album-list");

  let timeout = null;

  input.addEventListener("keyup", () => {
    clearTimeout(timeout);
    timeout = setTimeout(() => {
      fetch(`/album/search/?q=${encodeURIComponent(input.value)}`)
        .then((r) => r.json())
        .then((data) => {
          list.innerHTML = "";
          if (data.results.length === 0) {
            list.innerHTML = `<li class="list-group-item">No albums found.</li>`;
            return;
          }
          data.results.forEach((a) => {
            const li = document.createElement("li");
            li.className = "list-group-item d-flex justify-content-between align-items-center";
            li.innerHTML = `
    <div>
      <a href="${a.detail_url}" class="fw-bold text-decoration-none">${a.name}</a>
      ${a.is_public ? '<span class="badge bg-success ms-2">Public</span>' : '<span class="badge bg-secondary ms-2">Private</span>'}
    </div>
    <div class="btn-group btn-group-sm" role="group">
      <a href="${a.detail_url}" class="btn btn-outline-primary">👁 View</a>
      <a href="${a.edit_url}" class="btn btn-outline-secondary">✏ Edit</a>
      <a href="${a.toggle_url}" class="btn btn-outline-warning">
        ${a.is_public ? "🔒 Make Private" : "🌍 Make Public"}
      </a>
      <button type="button"
              class="btn btn-outline-danger"
              data-bs-toggle="modal"
              data-bs-target="#deleteAlbumModal"
              data-album-id="${a.id}"
              data-album-name="${a.name}">
        🗑 Delete
      </button>
    </div>
  `;
            list.appendChild(li);
          });
        });
    }, 300); // debounce: wait 300ms after typing
  });

  // Prevent form submission (we want AJAX only)
  form.addEventListener("submit", (e) => e.preventDefault());
});

document.addEventListener("DOMContentLoaded", () => {
  const trackList = document.getElementById("track-list");
  if (!trackList) return;

  const albumId = trackList.dataset.albumId;

  // ---- DELETE ----
  const deleteModal = document.getElementById("deleteTrackModal");
  if (deleteModal) {
    deleteModal.addEventListener("show.bs.modal", (event) => {
      const button = event.relatedTarget;
      const trackId = button.getAttribute("data-track-id");
      const trackName = button.getAttribute("data-track-name");

      deleteModal.querySelector("#deleteTrackName").textContent = trackName;
      const form = deleteModal.querySelector("#deleteTrackForm");
      form.action = `/album/${albumId}/tracks/${trackId}/remove/`;
    });
  }

  // ---- RENAME ----
  const renameModal = document.getElementById("renameTrackModal");
  if (renameModal) {
    renameModal.addEventListener("show.bs.modal", (event) => {
      const button = event.relatedTarget;
      const trackId = button.getAttribute("data-track-id");
      const trackName = button.getAttribute("data-track-name");

      renameModal.querySelector("#renameTrackInput").value = trackName;
      const form = renameModal.querySelector("#renameTrackForm");
      form.action = `/album/${albumId}/tracks/${trackId}/rename/`;
    });
  }
});
