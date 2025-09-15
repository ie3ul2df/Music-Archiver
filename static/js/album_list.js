// -------------------- static/js/album_list.js --------------------
(() => {
  "use strict";
  const U = window.AlbumUtils || {};

  const notify = (message, level) => {
    if (typeof window.showMessage === "function") {
      return window.showMessage(message, level);
    }
    if (typeof window.alert === "function") {
      window.alert(message);
    }
    return false;
  };
  // ========== Delete Album (modal + submit) ==========
  U.onModalShow &&
    U.onModalShow("deleteAlbumModal", ({ modal, trigger }) => {
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
          // alert(data.error || "Failed to delete album.");
          notify(data.error || "Failed to delete album.", "danger");
        }
      } catch (err) {
        console.error("Delete failed:", err);
        // alert("Something went wrong deleting the album.");
        notify("Something went wrong deleting the album.", "danger");
      }
    });
  });

  // ========== Create album (AJAX) ==========
  document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("album-create-form");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const name = (form.querySelector("[name=name]")?.value || "").trim();
      // if (!name) return alert("Please enter an album name");
      if (!name) {
        notify("Please enter an album name", "warning");
        return;
      }

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
          // alert(data.error || "Could not create album");
          notify(data.error || "Could not create album", "danger");
        }
      } catch (err) {
        console.error("Album create failed:", err);
        // alert("Free users are limited to 3 albums only, upgrade for unlimited album and anlimited tracks...");
        notify("Free users are limited to 3 albums only, upgrade for unlimited album and anlimited tracks...", "warning");
      }
    });
  });

  // ========== Rename Album (modal + submit; uses Bootstrap trigger) ==========
  document.addEventListener("DOMContentLoaded", () => {
    const renameModal = document.getElementById("renameAlbumModal");
    const renameForm = document.getElementById("renameAlbumForm");
    const renameInput = document.getElementById("renameAlbumInput");

    // set by onModalShow so submit can find the right row back
    let lastTriggerBtn = null;

    // When the modal is about to show, fill fields from the button that opened it
    if (U.onModalShow) {
      U.onModalShow("renameAlbumModal", ({ modal, trigger }) => {
        lastTriggerBtn = trigger || null;

        const url = trigger?.getAttribute("data-url") || "";
        const name = trigger?.getAttribute("data-current-name") || "";

        if (renameForm) renameForm.setAttribute("action", url);
        if (renameInput) renameInput.value = name;
      });
    }

    // Submit via AJAX to renameForm.action
    if (renameForm) {
      renameForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const url = renameForm.getAttribute("action");
        const newName = (renameInput?.value || "").trim();

        // if (!url) return alert("Missing rename URL.");
        // if (!newName) return alert("Name cannot be empty.");
        if (!url) {
          notify("Missing rename URL.", "danger");
          return;
        }
        if (!newName) {
          notify("Name cannot be empty.", "warning");
          return;
        }

        try {
          const data = await U.postForm(url, { name: newName }); // expects {ok, name, detail_url?}
          if (!data || data.ok === false) {
            // alert((data && data.error) || "Rename failed");
            notify((data && data.error) || "Rename failed", "danger");
            return;
          }

          // Update the row that contained the trigger button
          let li = lastTriggerBtn?.closest("li.list-group-item");
          if (!li) {
            // fallback: find by matching data-url (works for static or injected rows)
            try {
              const selector = `.rename-album-btn[data-url="${CSS.escape(url)}"]`;
              li = document.querySelector(selector)?.closest("li.list-group-item") || null;
            } catch (_) {}
          }

          // Update visible name + the button's current-name
          const newLabel = data.name || newName;
          if (li) {
            const titleEl = li.querySelector("a.fw-bold, .album-name");
            if (titleEl) titleEl.textContent = newLabel;
            const btn = li.querySelector(".rename-album-btn");
            if (btn) btn.setAttribute("data-current-name", newLabel);
          }

          // Close modal
          bootstrap.Modal.getInstance(renameModal)?.hide();

          // Keep the cached snapshot correct
          const isSearching = !!(document.getElementById("album-search-input")?.value || "").trim();
          const albumId = li?.dataset.id;
          if (isSearching && albumId && window.patchBaseAlbumName) {
            // We’re in search mode: patch the cached “original list” DOM with just this album’s new name
            window.patchBaseAlbumName(albumId, newLabel);
          } else {
            // Not searching: safe to overwrite snapshot with current DOM
            window.updateAlbumListSnapshot?.();
          }
        } catch (err) {
          console.error("Rename error:", err);
          // alert("Something went wrong renaming album.");
          notify("Something went wrong renaming album.", "danger");
        }
      });
    }
  });
})();

// ========== Unified search (input-group style) ==========
(function () {
  "use strict";

  const wrap = document.getElementById("album-search");
  const input = wrap?.querySelector(".js-unified-search");
  const targetSel = input?.getAttribute("data-target") || "#album-list";
  const list = document.querySelector(targetSel);
  const SEARCH_URL = wrap?.dataset?.searchUrl || "/album/search/";

  if (!wrap || !input || !list) return;

  // --- base snapshot of the full page list (unfiltered) ---
  let originalListHTML = list.innerHTML;

  // allow other code (rename) to patch snapshot
  window.patchBaseAlbumName = (id, newName) => {
    const wrapDiv = document.createElement("div");
    wrapDiv.innerHTML = originalListHTML;
    const li = wrapDiv.querySelector(`li[data-id="${window.CSS && CSS.escape ? CSS.escape(String(id)) : id}"]`);
    if (!li) return;
    const titleEl = li.querySelector('[data-role="album-name"], a.fw-bold, .album-name');
    if (titleEl) titleEl.textContent = newName;
    const btn = li.querySelector(".rename-album-btn");
    if (btn) btn.setAttribute("data-current-name", newName);
    originalListHTML = wrapDiv.innerHTML;
  };

  window.updateAlbumListSnapshot = () => {
    originalListHTML = list.innerHTML;
  };

  const restoreOriginal = () => {
    list.innerHTML = originalListHTML;
  };

  const debounce = (fn, ms) => {
    let t;
    return (...a) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...a), ms);
    };
  };

  let lastQuery = "";
  let aborter = null;

  async function performSearch(q) {
    if (!q) {
      restoreOriginal();
      return;
    }

    if (aborter) aborter.abort();
    aborter = new AbortController();

    const r = await fetch(`${SEARCH_URL}?q=${encodeURIComponent(q)}`, { signal: aborter.signal });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();

    const hasAlbums = (data.albums_html || "").trim();
    const hasTracks = (data.tracks_html || "").trim();

    list.innerHTML = "";

    if (!hasAlbums && !hasTracks) {
      list.innerHTML = `<li class="list-group-item">No results found.</li>`;
      return;
    }

    if (hasAlbums) {
      const h = document.createElement("li");
      h.className = "list-group-item active";
      h.textContent = "Albums";
      list.appendChild(h);

      const wrap = document.createElement("div");
      wrap.innerHTML = data.albums_html;
      wrap.childNodes.forEach((n) => {
        if (n.nodeType === 1) list.appendChild(n);
      });
    }

    if (hasTracks) {
      const h = document.createElement("li");
      h.className = "list-group-item active";
      h.textContent = "Tracks";
      list.appendChild(h);

      const wrap = document.createElement("div");
      wrap.innerHTML = data.tracks_html;
      wrap.childNodes.forEach((n) => {
        if (n.nodeType === 1) list.appendChild(n);
      });
    }
  }

  const runSearch = debounce(async () => {
    const q = (input.value || "").trim();
    if (q === lastQuery) return;
    lastQuery = q;
    try {
      await performSearch(q);
    } catch (err) {
      if (err.name !== "AbortError") console.error("Unified search error:", err);
    }
  }, 250);

  input.addEventListener("input", runSearch);
  input.addEventListener("keyup", runSearch);

  // Clear button restores snapshot
  wrap.addEventListener("click", (e) => {
    const btn = e.target.closest(".js-unified-search-clear");
    if (!btn) return;
    input.value = "";
    lastQuery = "";
    restoreOriginal();
    input.focus();
  });
})();

//--------------------------- Search Through Saved Albums & tracks ---------------------------//

// -------- Saved Albums / Saved Tracks search (top-level rows only) --------
(function () {
  "use strict";

  function filterList(input) {
    const target = input.getAttribute("data-target");
    if (!target) return;
    const list = document.querySelector(target);
    if (!list) return;

    const q = (input.value || "").trim().toLowerCase();

    // Only DIRECT children <li> of the top list
    const rows = Array.from(list.children).filter((el) => el.tagName === "LI" && !el.classList.contains("no-results-row"));

    let shown = 0;
    for (const li of rows) {
      // Prefer a title element inside our partials
      const titleEl = li.querySelector('[data-role="album-name"], [data-role="track-title"], .fw-bold, .fw-semibold');
      const hay = ((titleEl ? titleEl.textContent : li.textContent) || "").toLowerCase();

      const visible = !q || hay.includes(q);
      li.classList.toggle("d-none", !visible);
      if (visible) shown++;
    }

    // Add / toggle "No results" row
    let emptyRow = list.querySelector(".no-results-row");
    if (!emptyRow) {
      emptyRow = document.createElement("li");
      emptyRow.className = "list-group-item text-muted no-results-row d-none";
      emptyRow.textContent = "No matching results.";
      list.appendChild(emptyRow);
    }
    emptyRow.classList.toggle("d-none", shown !== 0);
  }

  // type to filter
  document.addEventListener("input", (e) => {
    if (e.target.classList?.contains("saved-search-input")) {
      filterList(e.target);
    }
  });

  // clear button
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".saved-search-clear");
    if (!btn) return;
    const group = btn.closest("[data-saved-search]");
    const input = group?.querySelector(".saved-search-input");
    if (input) {
      input.value = "";
      filterList(input);
      input.focus();
    }
  });

  // re-apply when tab is shown (Bootstrap)
  document.addEventListener("shown.bs.tab", (e) => {
    const paneSel = e.target?.getAttribute("data-bs-target");
    const pane = paneSel && document.querySelector(paneSel);
    if (!pane) return;
    pane.querySelectorAll(".saved-search-input").forEach((inp) => {
      if (inp.value.trim()) filterList(inp);
    });
  });
})();
