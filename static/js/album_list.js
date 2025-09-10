// -------------------- static/js/album_list.js --------------------
(() => {
  "use strict";
  const U = window.AlbumUtils || {};

  // ========== Delete Album (modal + submit) ==========
  U.onModalShow && U.onModalShow("deleteAlbumModal", ({ modal, trigger }) => {
    if (!trigger) return;
    modal.querySelector("#albumName").textContent = trigger.getAttribute("data-album-name") || "";
    modal.querySelector("#deleteAlbumForm").action = trigger.getAttribute("data-url");
  });

  document.addEventListener("DOMContentLoaded", () => {
    const delForm = document.getElementById("deleteAlbumForm");
    if (!delForm) return;
    delForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        const data = await fetch(delForm.action, {
          method: "POST",
          headers: { "X-CSRFToken": U.getCSRF() },
        }).then((r) => r.json());

        if (data.ok) {
          const li = document.querySelector(`#album-list li[data-id="${data.id}"]`);
          if (li) li.remove();
          bootstrap.Modal.getInstance(document.getElementById("deleteAlbumModal"))?.hide();
        } else {
          alert(data.error || "Failed to delete album.");
        }
      } catch (err) {
        console.error("Delete failed:", err);
        alert("Something went wrong deleting the album.");
      }
    });
  });

  // ========== Album search (debounced) ==========
  document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("album-search-form");
    const input = document.getElementById("album-search-input");
    const list = document.getElementById("album-list");
    if (!form || !input || !list) return;

    const renderRow = (a) => {
      const li = document.createElement("li");
      li.className = "list-group-item d-flex justify-content-between align-items-center flex-wrap";
      li.dataset.id = a.id;
      li.innerHTML = `
        <div class="d-flex flex-column">
          <div>
            <a href="${a.detail_url}" class="fw-bold text-decoration-none album-name">${a.name}</a>
            ${a.is_public ? '<span class="badge bg-success ms-2">Public</span>' : '<span class="badge bg-secondary ms-2">Private</span>'}
          </div>
          <!-- (Optional) You can inject rating stars fragment here if your API returns the HTML -->
        </div>

        <div class="btn-group btn-group-sm mt-2 mt-md-0" role="group">
          <a href="${a.detail_url}" class="btn btn-outline-primary">👁 View</a>
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
                  data-url="${a.delete_url || a.delete_ajax_url || a.edit_url}"
                  data-album-name="${a.name}">
            🗑 Delete
          </button>
        </div>
      `;
      return li;
    };

    const runSearch = U.debounce(async () => {
      try {
        const r = await fetch(`/album/search/?q=${encodeURIComponent(input.value)}`);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const data = await r.json();

        list.innerHTML = "";
        if (!data.results?.length) {
          list.innerHTML = `<li class="list-group-item">No albums found.</li>`;
          return;
        }
        data.results.forEach((a) => list.appendChild(renderRow(a)));
      } catch (err) {
        console.error("Album search error:", err);
      }
    }, 300);

    input.addEventListener("keyup", runSearch);
    form.addEventListener("submit", (e) => e.preventDefault());
  });

  // ========== Create album (AJAX) ==========
  document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("album-create-form");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const name = (form.querySelector("[name=name]")?.value || "").trim();
      if (!name) return alert("Please enter an album name");

      try {
        const data = await U.postForm(form.action, { name });
        if (data.ok) {
          form.reset();
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
                <button type="button"
                        class="btn btn-outline-secondary rename-album-btn"
                        data-bs-toggle="modal"
                        data-bs-target="#renameAlbumModal"
                        data-url="${data.edit_url}"
                        data-current-name="${data.name}">
                  ✏ Edit
                </button>
                <a href="${data.toggle_url}" class="btn btn-outline-warning">🌍 Make Public</a>
                <button type="button"
                        class="btn btn-outline-danger"
                        data-bs-toggle="modal"
                        data-bs-target="#deleteAlbumModal"
                        data-url="${data.delete_url}"
                        data-album-name="${data.name}">
                  🗑 Delete
                </button>
              </div>`;
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

  // ========== Rename Album (modal + submit) ==========
  document.addEventListener("DOMContentLoaded", () => {
    const renameModal = document.getElementById("renameAlbumModal");
    const renameForm  = document.getElementById("renameAlbumForm");
    const renameInput = document.getElementById("renameAlbumInput");
    let renameUrl = null;
    let albumLi = null;

    // Static buttons present on initial render
    document.querySelectorAll(".rename-album-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        renameUrl = btn.getAttribute("data-url");
        albumLi   = btn.closest("li.list-group-item");
        renameInput.value = btn.getAttribute("data-current-name") || "";
        new bootstrap.Modal(renameModal).show();
      });
    });

    // Also handle dynamically injected rows (from search/create)
    U.onModalShow && U.onModalShow("renameAlbumModal", ({ trigger }) => {
      if (!trigger) return;
      renameUrl = trigger.getAttribute("data-url");
      albumLi   = trigger.closest("li.list-group-item");
      renameInput.value = trigger.getAttribute("data-current-name") || "";
    });

    if (renameForm) {
      renameForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!renameUrl) return;
        const newName = (renameInput.value || "").trim();
        if (!newName) return alert("Name cannot be empty");

        try {
          const data = await U.postForm(renameUrl, { name: newName });
          if (data.ok) {
            if (albumLi) {
              const link = albumLi.querySelector("a.fw-bold, .album-name");
              if (link) link.textContent = data.name || newName;
              const btn = albumLi.querySelector(".rename-album-btn");
              if (btn) btn.setAttribute("data-current-name", data.name || newName);
            } else {
              const any = document.querySelector(
                `a[href="${data.detail_url}"].fw-bold, a.album-name[href="${data.detail_url}"]`
              );
              if (any) any.textContent = data.name || newName;
            }
            bootstrap.Modal.getInstance(renameModal)?.hide();
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
})();
