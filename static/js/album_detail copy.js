// -------------------- static/js/album_detail.js -------------------- 

// --- CSRF helper (use everywhere) ---
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + "=")) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
function getCSRF() {
  return getCookie("csrftoken");
}

// Drag-and-drop reordering for tracks in an album.
// Updates DOM order live and POSTs new order (AlbumTrack IDs) back to the server.
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
        "X-CSRFToken": getCSRF(),
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


// Populate and configure the Delete Album modal when opened (sets album name and form action). 
// Also, add event listener to the modal to handle the form submission. 
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


// Handle the DELETE request for the album.
// Redirect to the album list page on success.
// Show error alert on failure. 
document.addEventListener("DOMContentLoaded", () => {
  const deleteForm = document.getElementById("deleteAlbumForm");
  if (!deleteForm) return;

  deleteForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const url = deleteForm.getAttribute("action");

    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "X-CSRFToken": getCSRF() },
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


// Handle the DELETE request for the album search. 
// This is called from the search form's submit event.
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("album-search-form");
  const input = document.getElementById("album-search-input");
  const list = document.getElementById("album-list");

  // If this page has no search UI, stop here
  if (!form || !input || !list) return;

  let timeout = null;

  input.addEventListener("keyup", () => {
    clearTimeout(timeout);
    timeout = setTimeout(() => {
      fetch(`/album/search/?q=${encodeURIComponent(input.value)}`)
        .then((r) => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.json();
        })
        .then((data) => {
          list.innerHTML = "";
          if (data.results.length === 0) {
            list.innerHTML = `<li class="list-group-item">No albums found.</li>`;
            return;
          }

          data.results.forEach((a) => {
            const li = document.createElement("li");
            li.className =
              "list-group-item d-flex justify-content-between align-items-center";
            li.innerHTML = `
              <div>
                <a href="${a.detail_url}" class="fw-bold text-decoration-none album-name">${a.name}</a>
                ${
                  a.is_public
                    ? '<span class="badge bg-success ms-2">Public</span>'
                    : '<span class="badge bg-secondary ms-2">Private</span>'
                }
              </div>
              <div class="btn-group btn-group-sm" role="group">
                <a href="${a.detail_url}" class="btn btn-outline-primary">👁 View</a>
                <!-- ✏ Edit as POST-able button (opens modal) -->
                <button type="button"
                        class="btn btn-outline-secondary rename-album-btn"
                        data-bs-toggle="modal"
                        data-bs-target="#renameAlbumModal"
                        data-url="${a.edit_url}"
                        data-current-name="${a.name}">
                  ✏ Edit
                </button>
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
        })
        .catch((err) => {
          console.error("Album search error:", err);
        });
    }, 300); // debounce
  });

  // Prevent form submission (we want AJAX only)
  form.addEventListener("submit", (e) => e.preventDefault());
});


// DOMContentLoaded event listener for DOMContentLoaded event listeners.
// This is the first event listener that gets called when the DOM is ready. 
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
      const trackName = button.getAttribute("data-track-name");
      const url = button.getAttribute("data-url");

      // Fill input with current track name
      renameModal.querySelector("#renameTrackInput").value = trackName;

      // Update form action to the correct endpoint
      const form = renameModal.querySelector("#renameTrackForm");
      form.action = url;
    });
  }
});


// DOMContentLoaded event listener for DOMContentLoaded event listeners.
// This is the first event listener that gets called when the DOM is ready. 
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("album-create-form");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault(); // stop page reload

    const url = form.getAttribute("action");
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
          "X-CSRFToken": getCSRF(),
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


// Album rename modal 
document.addEventListener("DOMContentLoaded", () => {
  const renameModal = document.getElementById("renameAlbumModal");
  const renameForm = document.getElementById("renameAlbumForm");
  const renameInput = document.getElementById("renameAlbumInput");

  let renameUrl = null;
  let albumLi = null;

  // Existing static buttons (rendered on page load)
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

  // NEW: also populate when modal opens (works for dynamic buttons from search)
  if (renameModal) {
    renameModal.addEventListener("show.bs.modal", (event) => {
      const btn = event.relatedTarget;
      if (!btn) return;

      // Fill globals used by submit handler
      renameUrl = btn.getAttribute("data-url");
      albumLi = btn.closest("li.list-group-item");

      const currentName = btn.getAttribute("data-current-name") || "";
      renameInput.value = currentName;
    });
  }

  // Submit rename form via AJAX
  if (renameForm) {
    renameForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!renameUrl) return;

      const newName = renameInput.value.trim();
      if (!newName) {
        alert("Name cannot be empty");
        return;
      }

      try {
        const res = await fetch(renameUrl, {
          method: "POST",
          headers: {
            "X-CSRFToken": getCSRF(),
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: new URLSearchParams({ name: newName }),
        });
        const data = await res.json();

        if (data.ok) {
          // Update the DOM with new name (works for both static and searched rows)
          if (!albumLi) {
            // best-effort: update any first matching link if we don't have the row
            const any = document.querySelector(`a[href="${data.detail_url}"].fw-bold, a.album-name[href="${data.detail_url}"]`);
            if (any) any.textContent = data.name || newName;
          } else {
            const link = albumLi.querySelector("a.fw-bold, .album-name");
            if (link) link.textContent = data.name || newName;

            // Also update button dataset on this row
            const btn = albumLi.querySelector(".rename-album-btn");
            if (btn) btn.setAttribute("data-current-name", data.name || newName);
          }

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


// DELETE (🗑) — delete my track entirely
// DETACH (⛔) — remove from THIS album only
document.addEventListener("DOMContentLoaded", () => {
  const deleteModal = document.getElementById("deleteTrackModal");

  // --- DELETE HANDLER (🗑) ---
  if (deleteModal) {
    deleteModal.addEventListener("show.bs.modal", (event) => {
      const button = event.relatedTarget;
      const trackId = button.getAttribute("data-track-id");
      const trackName = button.getAttribute("data-track-name");

      // Update modal content
      deleteModal.querySelector("#deleteTrackName").textContent = trackName;

      // Point form action to correct endpoint
      const form = deleteModal.querySelector("#deleteTrackForm");
      form.action = `/tracks/${trackId}/delete/`; // ✅ Track delete endpoint
    });

    const deleteForm = document.getElementById("deleteTrackForm");
    if (deleteForm) {
      deleteForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const url = deleteForm.getAttribute("action");

        try {
          const res = await fetch(url, {
            method: "POST",
            headers: { "X-CSRFToken": getCSRF() },
          });

          const data = await res.json();
          if (data.ok) {
            // Remove deleted track row from DOM
            const li = document.querySelector(
              `#track-list li[data-track-id="${data.id}"]`
            );
            if (li) li.remove();

            // Close modal
            bootstrap.Modal.getInstance(deleteModal)?.hide();
          } else {
            alert(data.error || "Failed to delete track.");
          }
        } catch (err) {
          console.error("Delete track error:", err);
          alert("Network error while deleting track.");
        }
      });
    }
  }

  // --- DETACH HANDLER (⛔) ---
  document.addEventListener("click", async (e) => {
    const btn = e.target.closest(".js-detach[data-detach-url]");
    if (!btn) return;

    e.preventDefault();
    const url = btn.getAttribute("data-detach-url");

    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "X-CSRFToken": getCSRF() },
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      // Remove detached track row from DOM
      const row = btn.closest("li.list-group-item");
      if (row) row.remove();
    } catch (err) {
      console.error("Detach error:", err);
      alert("Failed to remove track from album.");
    }
  });
});
