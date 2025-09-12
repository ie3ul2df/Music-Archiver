// -------------------- static/js/album_utils.js --------------------
(function (w) {
  "use strict";

  // ---------- helpers ----------
  function getCookie(name) {
    let val = null;
    if (document.cookie && document.cookie !== "") {
      const parts = document.cookie.split(";");
      for (let c of parts) {
        c = c.trim();
        if (c.startsWith(name + "=")) {
          val = decodeURIComponent(c.slice(name.length + 1));
          break;
        }
      }
    }
    return val;
  }
  function getCSRF() {
    return getCookie("csrftoken");
  }

  function debounce(fn, wait) {
    let t = null;
    return function (...args) {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), wait);
    };
  }

  async function _handle(res) {
    const ok = res.ok;
    const ct = res.headers.get("content-type") || "";
    const isJSON = ct.includes("application/json");
    const payload = isJSON ? await res.json() : await res.text();
    if (!ok) {
      const msg = isJSON && payload && payload.error ? payload.error : `HTTP ${res.status}`;
      throw new Error(msg);
    }
    return payload; // may be object or string
  }

  // POST JSON with CSRF
  function postJSON(url, payload) {
    return fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRF(),
      },
      body: JSON.stringify(payload || {}),
    }).then(_handle);
  }

  // POST x-www-form-urlencoded with CSRF
  function postForm(url, data) {
    return fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-CSRFToken": getCSRF(),
      },
      body: new URLSearchParams(data || {}),
    }).then(_handle);
  }

  // Delegated Bootstrap 'show' listener (works even if modal HTML is rendered later)
  function onModalShow(modalId, handler) {
    document.addEventListener("show.bs.modal", (event) => {
      const modal = event.target;
      if (modal && modal.id === modalId) {
        handler({ modal, trigger: event.relatedTarget || null });
      }
    });
  }

  const qs = (sel, root = document) => root.querySelector(sel);
  const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  // ---------- Album: RENAME wiring ----------
  onModalShow("renameAlbumModal", ({ modal, trigger }) => {
    if (!trigger) return;
    const url = trigger.getAttribute("data-url");
    const current = trigger.getAttribute("data-current-name") || "";
    const form = modal.querySelector("#renameAlbumForm");
    const input = modal.querySelector("#renameAlbumInput");
    if (form) form.action = url || "";
    if (input) {
      input.value = current;
      setTimeout(() => input.focus(), 50);
    }
  });

  document.addEventListener("submit", async (e) => {
    const form = e.target;
    if (!form) return;

    // Rename album
    if (form.id === "renameAlbumForm") {
      e.preventDefault();
      const url = form.action;
      const name = (form.querySelector("#renameAlbumInput")?.value || "").trim();
      if (!name) return;
      try {
        const data = await postForm(url, { name });
        // Accept either JSON {ok:true, id, name} or any 200 response as success
        const newName = typeof data === "object" && data.name ? data.name : name;

        // Update visible album title inline
        const titleEl = qs('[data-role="album-name"]') || qs(`#album-name-${data?.id || ""}`);
        if (titleEl) titleEl.textContent = newName;

        const modal = qs("#renameAlbumModal");
        if (modal) bootstrap.Modal.getInstance(modal)?.hide();
      } catch (err) {
        console.error(err);
        alert(err.message || "Rename failed.");
      }
    }

    // Delete album
    if (form.id === "deleteAlbumForm") {
      e.preventDefault();
      const url = form.action;
      try {
        const res = await fetch(url, {
          method: "POST",
          headers: { "X-CSRFToken": getCSRF() },
        });
        const ct = res.headers.get("content-type") || "";
        const isJSON = ct.includes("application/json");
        const payload = isJSON ? await res.json() : null;

        if (!res.ok || (isJSON && payload && payload.ok === false)) {
          const msg = (payload && payload.error) || `HTTP ${res.status}`;
          throw new Error(msg);
        }

        // Redirect target (prefer server-provided)
        const target = (payload && payload.redirect) || "/";
        window.location.href = target;
      } catch (err) {
        console.error(err);
        alert(err.message || "Delete failed.");
      }
    }
  });

  // Prefill the Rename Track modal everywhere (list + detail)
  onModalShow("renameTrackModal", ({ modal, trigger }) => {
    if (!trigger) return;
    const url = trigger.getAttribute("data-url") || "";
    const current = trigger.getAttribute("data-track-name") || "";
    const form = modal.querySelector("#renameTrackForm");
    const input = modal.querySelector("#renameTrackInput");
    if (form) form.action = url;
    if (input) {
      input.value = current;
      setTimeout(() => input.focus(), 50);
    }
  });

  // expose
  w.AlbumUtils = { getCookie, getCSRF, debounce, postJSON, postForm, onModalShow, qs, qsa };

  // Submit via fetch to avoid redirect; update ALL matching rows inline
  document.addEventListener("submit", async (e) => {
    if (e.target?.id !== "renameTrackForm") return;
    e.preventDefault();

    const form = e.target;
    const url = form.action;
    const name = (form.querySelector("#renameTrackInput")?.value || "").trim();
    if (!url || !name) return;

    try {
      const fd = new FormData();
      fd.append("name", name);

      const res = await fetch(url, {
        method: "POST",
        headers: {
          "X-CSRFToken": AlbumUtils.getCSRF(),
          "X-Requested-With": "XMLHttpRequest",
        },
        body: fd,
      });

      const isJSON = (res.headers.get("content-type") || "").includes("application/json");
      const data = isJSON ? await res.json() : null;

      const label = data?.name || name;

      // 1) Best: locate the exact row by album_item_id returned by the server
      let li = data?.album_item_id ? document.querySelector(`li.track-card[data-id="${data.album_item_id}"]`) : null;

      // 2) Fallback: match the button by the *pathname* (avoid absolute vs relative mismatch)
      if (!li) {
        const pathname = new URL(url, location.origin).pathname;
        const safe = window.CSS && CSS.escape ? CSS.escape(pathname) : pathname;
        const btn = document.querySelector(`.rename-track-btn[data-url="${safe}"]`);
        li = btn ? btn.closest("li.track-card") : null;
      }

      if (li) {
        const titleEl = li.querySelector('[data-role="track-title"], .fw-semibold');
        if (titleEl) titleEl.textContent = label;
        // keep the modal trigger(s) in sync so re-opening shows the new name
        li.querySelectorAll(".rename-track-btn").forEach((b) => b.setAttribute("data-track-name", label));
      }

      bootstrap.Modal.getInstance(document.getElementById("renameTrackModal"))?.hide();
    } catch (err) {
      console.error("Track rename failed:", err);
      alert(err.message || "Rename failed. Please try again.");
    }
  });
})(window);
