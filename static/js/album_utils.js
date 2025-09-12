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

  // Delete album: prefill modal
  onModalShow("deleteAlbumModal", ({ modal, trigger }) => {
    if (!trigger) return;
    const url = trigger.getAttribute("data-url");
    const name = trigger.getAttribute("data-album-name") || "";
    const form = modal.querySelector("#deleteAlbumForm");
    const label = modal.querySelector("#deleteAlbumName");
    if (form) form.action = url || "";
    if (label) label.textContent = name;
  });

  // expose
  w.AlbumUtils = { getCookie, getCSRF, debounce, postJSON, postForm, onModalShow, qs, qsa };
})(window);
