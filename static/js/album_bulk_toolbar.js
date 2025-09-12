// -------------------- static/js/album_bulk_toolbar.js --------------------
(function () {
  "use strict";

  // ---------- Helpers ----------
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

  function closestAlbum(el) {
    return el?.closest("li.album");
  }

  function getSelectedTrackCheckboxes(albumEl) {
    return Array.from(albumEl.querySelectorAll("input.track-check:checked"));
  }

  function getSelectedTrackIds(albumEl) {
    return getSelectedTrackCheckboxes(albumEl)
      .map((cb) => cb.value)
      .filter(Boolean);
  }

  async function post(url, payload) {
    const opts = {
      method: "POST",
      headers: {
        "X-CSRFToken": csrftoken,
        "X-Requested-With": "XMLHttpRequest",
      },
    };
    if (payload !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(payload);
    }
    const res = await fetch(url, opts);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const ct = res.headers.get("content-type") || "";
    return ct.includes("application/json") ? res.json() : res.text();
  }

  function ensureSaveModalBits() {
    const modal = document.getElementById("saveToAlbumModal");
    if (!modal) return {};
    const form = modal.querySelector("#save-to-album-form") || modal.querySelector("form");
    if (!form) return { modal };

    let hidden = form.querySelector("#save-track-ids");
    if (!hidden) {
      hidden = document.createElement("input");
      hidden.type = "hidden";
      hidden.name = "track_ids";
      hidden.id = "save-track-ids";
      form.appendChild(hidden);
    }
    const countEl = modal.querySelector(".js-selected-count");
    const albumSel = form.querySelector('select[name="album_id"]');

    return { modal, form, hidden, countEl, albumSel };
  }

  function setFormAction(form, btn) {
    const urlFromBtn = btn?.dataset?.saveUrl;
    if (urlFromBtn) {
      form.setAttribute("action", urlFromBtn);
    }
    // fallback: leave existing action if present
    const action = form.getAttribute("action");
    return action && action.length > 0;
  }

  // ---------- Select-all (scoped to one album) ----------
  document.addEventListener("change", (e) => {
    const toggle = e.target.closest(".check-all");
    if (!toggle) return;
    const albumEl = closestAlbum(toggle);
    if (!albumEl) return;
    albumEl.querySelectorAll("input.track-check").forEach((cb) => {
      if (!cb.disabled) cb.checked = toggle.checked;
    });
  });

  // ---------- Click handlers ----------
  document.addEventListener("click", async (e) => {
    const btnAddBulk = e.target.closest(".js-add-selected");
    const btnSaveBulk = e.target.closest(".js-save-selected");
    const btnSaveOne = e.target.closest(".js-save");

    // Bulk: Add to player
    if (btnAddBulk) {
      const albumEl = closestAlbum(btnAddBulk);
      if (!albumEl) return;
      const ids = getSelectedTrackIds(albumEl);
      if (!ids.length) {
        alert("Select at least one track.");
        return;
      }

      // For each selected row, call its per-row 'add-to-playlist' URL
      const rows = getSelectedTrackCheckboxes(albumEl).map((cb) => cb.closest("li, .track-row, .list-group-item"));
      const tasks = [];
      const buttonsUpdated = [];

      for (const row of rows) {
        const perRowBtn = row?.querySelector(".add-to-playlist");
        const url = perRowBtn?.dataset?.url;
        if (!url) continue;
        tasks.push(
          post(url).then(() => {
            // Best-effort UI update
            if (perRowBtn) {
              perRowBtn.classList.add("btn-success");
              perRowBtn.classList.remove("btn-outline-success");
              perRowBtn.textContent = "✓";
              perRowBtn.setAttribute("aria-pressed", "true");
              perRowBtn.dataset.in = "1";
              buttonsUpdated.push(perRowBtn);
            }
          })
        );
      }

      try {
        await Promise.all(tasks);
        alert(`Added ${tasks.length} track(s) to player.`);
      } catch (err) {
        console.error(err);
        alert("Some tracks could not be added. Please try again.");
      }
      return;
    }

    // Single: Save (per-track button)
    if (btnSaveOne) {
      const { modal, form, hidden, countEl } = ensureSaveModalBits();
      if (!modal || !form || !hidden) {
        alert("Save dialog is not configured correctly.");
        return;
      }
      if (!setFormAction(form, btnSaveOne) && !form.getAttribute("action")) {
        alert("Missing save URL.");
        return;
      }
      const row = btnSaveOne.closest("[data-track-id]");
      const trackId = row?.dataset?.trackId;
      if (!trackId) {
        alert("Could not determine track ID.");
        return;
      }
      hidden.value = trackId;
      if (countEl) countEl.textContent = "1";
      // Modal is opened by data-bs-toggle/data-bs-target in the button
      return;
    }

    // Bulk: Save selected to album
    if (btnSaveBulk) {
      const albumEl = closestAlbum(btnSaveBulk);
      if (!albumEl) return;
      const ids = getSelectedTrackIds(albumEl);
      if (!ids.length) {
        alert("Select at least one track.");
        return;
      }

      const { modal, form, hidden, countEl } = ensureSaveModalBits();
      if (!modal || !form || !hidden) {
        alert("Save dialog is not configured correctly.");
        return;
      }

      if (!setFormAction(form, btnSaveBulk) && !form.getAttribute("action")) {
        alert("Missing save URL.");
        return;
      }

      hidden.value = ids.join(",");
      if (countEl) countEl.textContent = String(ids.length);
      // Modal is opened by data attributes on the button
      return;
    }
  });

  // ---------- Form submit via AJAX (Save to album modal) ----------
  const saveForm = document.getElementById("save-to-album-form");
  if (saveForm && !saveForm.dataset.bound) {
    saveForm.dataset.bound = "1"; // prevent double binding
    saveForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const albumId = document.getElementById("save-album-select")?.value;
      const ids = document.getElementById("save-track-ids")?.value;
      const saveUrl = saveForm.getAttribute("action");

      if (!albumId || !ids || !saveUrl) {
        alert("Missing album or tracks.");
        return;
      }

      const fd = new FormData();
      fd.append("album_id", albumId);
      fd.append("track_ids", ids);

      try {
        const res = await fetch(saveUrl, {
          method: "POST",
          headers: { "X-CSRFToken": getCookie("csrftoken") },
          body: fd,
        });

        if (res.ok) {
          // Close modal
          bootstrap.Modal.getInstance(document.getElementById("saveToAlbumModal"))?.hide();

          // Optional: replace with a toast/snackbar for nicer UX
          alert("Track(s) saved successfully.");

          // Reload so UI reflects changes (you can remove this if you plan to update DOM instead)
          window.location.reload();
        } else {
          alert("Could not save to album.");
        }
      } catch (err) {
        console.error(err);
        alert("Network error while saving tracks.");
      }
    });
  }
})();
