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

    // Bulk: Add to playlist (add-only, no toggle)
    if (btnAddBulk) {
      const albumEl = closestAlbum(btnAddBulk);
      if (!albumEl) return;

      const ids = getSelectedTrackIds(albumEl);
      if (!ids.length) {
        alert("Select at least one track.");
        return;
      }

      const url = btnAddBulk.dataset.url; // bulk_add endpoint
      try {
        const res = await fetch(url, {
          method: "POST",
          headers: { "X-CSRFToken": csrftoken },
          body: new URLSearchParams({ track_ids: ids.join(",") }),
        });
        const data = await res.json();
        if (data.ok) {
          alert(`Added ${data.added} track(s), skipped ${data.skipped} duplicate(s).`);
          // Optional: update UI by turning per-row buttons into ✓
          ids.forEach((tid) => {
            const rowBtn = albumEl.querySelector(`.add-to-playlist[data-track="${tid}"]`);
            if (rowBtn) {
              rowBtn.classList.add("btn-success");
              rowBtn.classList.remove("btn-outline-success");
              rowBtn.textContent = "✓";
              rowBtn.dataset.in = "1";
              rowBtn.setAttribute("aria-pressed", "true");
            }
          });
        } else {
          alert("Could not add tracks to playlist.");
        }
      } catch (err) {
        console.error(err);
        alert("Network error while adding tracks.");
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
          headers: {
            "X-CSRFToken": getCookie("csrftoken"),
            "X-Requested-With": "XMLHttpRequest",
          },
          body: fd,
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        // close modal
        bootstrap.Modal.getInstance(document.getElementById("saveToAlbumModal"))?.hide();

        // success feedback
        alert(`Added ${data.added} track(s), skipped ${data.skipped} duplicate(s).`);

        // ✅ update UI without reload

        // 1) Update the source album rows (mark save buttons as "already saved")
        const trackIds = ids.split(",");
        trackIds.forEach((id) => {
          const row = document.querySelector(`li.track-card[data-track-id="${id}"]`);
          if (row) {
            const saveBtn = row.querySelector(".js-save");
            if (saveBtn) {
              saveBtn.textContent = "🗃️";
              saveBtn.title = "Already saved to your albums";
              saveBtn.classList.remove("btn-outline-secondary");
              saveBtn.classList.add("btn-secondary");
              saveBtn.disabled = true;
            }
          }
        });

        // 2) Inject new rows into the *target* album, if HTML was returned
        if (data.html && data.album_id) {
          const list = document.querySelector(`#album-tracklist-${data.album_id}`);
          if (list) {
            // remove "No tracks" message if present
            const emptyMsg = list.parentElement.querySelector(".small.text-muted.mt-2");
            if (emptyMsg) emptyMsg.remove();

            list.insertAdjacentHTML("beforeend", data.html);
          }
        }
      } catch (err) {
        console.error(err);
        alert(err.message || "Network error while saving tracks.");
      }
    });
  }

  //--------------------------- Bulk Detach ---------------------------//
  // Bulk remove selected tracks from THIS album (by AlbumTrack ids)
  document.addEventListener("click", async (e) => {
    const btn = e.target.closest(".js-remove-selected");
    if (!btn) return;

    // Find the album card and its track list
    const card = btn.closest("li.album, .album.card, .album");
    const list = card?.querySelector(".album-tracklist");
    if (!list) return;

    // Collect selected AlbumTrack ids from checked rows
    const checked = Array.from(list.querySelectorAll(".track-check:checked"));
    const itemIds = checked.map((cb) => cb.closest("li.track-card")?.dataset.id).filter(Boolean);

    if (itemIds.length === 0) {
      alert("Select at least one track to remove.");
      return;
    }
    if (!confirm(`Remove ${itemIds.length} track(s) from this album?`)) return;

    const url = btn.dataset.url;
    const origHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerText = "Removing…";

    try {
      const data = await post(url, { items: itemIds });
      if (!data?.ok) throw new Error("Server error.");

      // Remove rows from DOM
      (data.removed || []).forEach((id) => {
        const li = list.querySelector(`li.track-card[data-id="${id}"]`);
        if (li) li.remove();
      });

      // Uncheck “select all” if present
      const checkAll = card.querySelector(".check-all");
      if (checkAll) checkAll.checked = false;

      // If empty, show a friendly message
      if (!list.querySelector("li.track-card")) {
        const empty = document.createElement("div");
        empty.className = "small text-muted mt-2";
        empty.textContent = "No tracks in this album yet.";
        list.after(empty);
      }
    } catch (err) {
      console.error(err);
      alert(err.message || "Bulk remove failed.");
    } finally {
      btn.disabled = false;
      btn.innerHTML = origHTML;
    }
  });
})();
