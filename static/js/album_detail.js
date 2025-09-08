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
      const albumName = button.getAttribute("data-album-name");
      const deleteUrl = button.getAttribute("data-url");

      // Update modal text
      const albumNameEl = modal.querySelector("#albumName");
      if (albumNameEl) {
        albumNameEl.textContent = albumName;
      }

      // Set correct form action (AJAX endpoint)
      const form = modal.querySelector("#deleteAlbumForm");
      if (form) {
        form.action = deleteUrl;
      }
    });
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const deleteForm = document.getElementById("deleteAlbumForm");
  if (!deleteForm) return;

  deleteForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const url = deleteForm.getAttribute("action");
    const csrftoken = document.querySelector("[name=csrfmiddlewaretoken]").value;

    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "X-CSRFToken": csrftoken },
      });
      const data = await res.json();

      if (data.ok) {
        // Remove the album li
        const li = document.querySelector(`#album-list li[data-id="${data.id}"]`);
        if (li) li.remove();

        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById("deleteAlbumModal"));
        modal.hide();
      } else {
        alert(data.error || "Failed to delete album.");
      }
    } catch (err) {
      console.error("Delete failed:", err);
      alert("Something went wrong deleting the album.");
    }
  });
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

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("album-create-form");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault(); // stop page reload

    const url = form.getAttribute("action");
    const csrftoken = document.querySelector("[name=csrfmiddlewaretoken]").value;
    const nameInput = form.querySelector("[name=name]");
    const name = nameInput.value.trim();

    if (!name) {
      alert("Please enter an album name");
      return;
    }

    try {
      const res = await fetch(url, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrftoken,
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: new URLSearchParams({ name }),
      });

      const data = await res.json();

      if (data.ok) {
        // Reset form
        form.reset();

        // Insert new album at the top of the list
        const list = document.getElementById("album-list");
        if (list) {
          const li = document.createElement("li");
          li.className = "list-group-item d-flex justify-content-between align-items-center flex-wrap";
          li.dataset.id = data.id;
          li.innerHTML = `
            <div class="d-flex flex-column">
              <div>
                <a href="${data.detail_url}" class="fw-bold text-decoration-none">${data.name}</a>
                <span class="badge bg-secondary ms-2">Private</span>
              </div>
              <div class="mt-1">⭐ New album</div>
            </div>
            <div class="btn-group btn-group-sm mt-2 mt-md-0" role="group">
              <a href="${data.detail_url}" class="btn btn-outline-primary">👁 View</a>
              <button type="button" class="btn btn-outline-secondary" disabled>✏ Edit</button>
              <button type="button" class="btn btn-outline-warning" disabled>🌍 Make Public</button>
              <button type="button" class="btn btn-outline-danger" disabled>🗑 Delete</button>
            </div>
          `;
          list.prepend(li);
        }
      } else {
        alert(data.error || "Could not create album");
      }
    } catch (err) {
      console.error("Album create failed:", err);
      alert("Something went wrong");
    }
  });
});

//------------------------ Album Edit modal handler

document.addEventListener("DOMContentLoaded", () => {
  const renameModal = document.getElementById("renameAlbumModal");
  const renameForm = document.getElementById("renameAlbumForm");
  const renameInput = document.getElementById("renameAlbumInput");

  let renameUrl = null;
  let albumLi = null;

  // Open modal with current album name
  document.querySelectorAll(".rename-album-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      renameUrl = btn.getAttribute("data-url");
      const currentName = btn.getAttribute("data-current-name");
      albumLi = btn.closest("li.list-group-item");

      renameInput.value = currentName;
      const modal = new bootstrap.Modal(renameModal);
      modal.show();
    });
  });

  // Submit rename form via AJAX
  if (renameForm) {
    renameForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!renameUrl) return;

      const csrftoken = document.querySelector("[name=csrfmiddlewaretoken]").value;
      const newName = renameInput.value.trim();
      if (!newName) {
        alert("Name cannot be empty");
        return;
      }

      try {
        const res = await fetch(renameUrl, {
          method: "POST",
          headers: {
            "X-CSRFToken": csrftoken,
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: new URLSearchParams({ name: newName }),
        });
        const data = await res.json();

        if (data.ok && albumLi) {
          // Update the DOM with new name
          const link = albumLi.querySelector("a.fw-bold");
          if (link) link.textContent = newName;

          // Also update button dataset
          const btn = albumLi.querySelector(".rename-album-btn");
          if (btn) btn.setAttribute("data-current-name", newName);

          // Close modal
          bootstrap.Modal.getInstance(renameModal).hide();
        } else {
          alert(data.error || "Rename failed");
        }
      } catch (err) {
        console.error("Rename error:", err);
        alert("Something went wrong renaming album.");
      }
    });
  }
});
