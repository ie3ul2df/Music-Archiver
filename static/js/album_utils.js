// -------------------- static/js/album_utils.js --------------------
(function (w) {
  "use strict";

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
  function getCSRF() { return getCookie("csrftoken"); }

  // Simple debounce
  function debounce(fn, wait) {
    let t = null;
    return function (...args) {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), wait);
    };
  }

  async function _handle(res) {
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const ct = res.headers.get("content-type") || "";
    return ct.includes("application/json") ? res.json() : res.text();
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

  // Wire bootstrap modal show event with a clean callback
  function onModalShow(modalId, handler) {
    const el = document.getElementById(modalId);
    if (!el) return;
    el.addEventListener("show.bs.modal", (event) => {
      handler({ modal: el, trigger: event.relatedTarget });
    });
  }

  // Tiny DOM helpers (optional)
  const qs  = (sel, root = document) => root.querySelector(sel);
  const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  w.AlbumUtils = { getCookie, getCSRF, debounce, postJSON, postForm, onModalShow, qs, qsa };
})(window);
