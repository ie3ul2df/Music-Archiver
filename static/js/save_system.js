(function () {
  "use strict";

  const notify = (message, level) => {
    if (typeof window.showMessage === "function") {
      return window.showMessage(message, level);
    }
    if (typeof window.alert === "function") {
      window.alert(message);
    }
    return false;
  };

  // --- CSRF from cookie ---
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return decodeURIComponent(parts.pop().split(";").shift());
  }
  const csrfToken = getCookie("csrftoken");

  // Cache modal + form
  const modalEl = document.getElementById("saveToAlbumModal");
  const form = document.getElementById("save-to-album-form");

  // 1) When user clicks 💾, set form.action to that track's save URL
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".js-save[data-save-url]");
    if (!btn || !form) return;

    const saveUrl = btn.getAttribute("data-save-url");
    if (saveUrl) form.setAttribute("action", saveUrl);
  });

  // 2) Submit the modal form via fetch to form.action, sending album_id
  // if (form) {
  //   form.addEventListener("submit", async (e) => {
  //     e.preventDefault();

  //     const actionUrl = form.getAttribute("action");
  //     const select = document.getElementById("save-album-select");
  //     const albumId = select ? select.value : "";

  //     if (!actionUrl || !albumId) {
  //       alert("Missing save URL or album.");
  //       return;
  //     }

  //     try {
  //       const resp = await fetch(actionUrl, {
  //         method: "POST",
  //         headers: {
  //           "X-CSRFToken": csrfToken,
  //           "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
  //         },
  //         body: new URLSearchParams({ album_id: albumId }).toString(),
  //       });

  //       // Expect JSON { ok: True/False, created: True/False }
  //       const data = await resp.json().catch(() => ({}));
  //       if (!resp.ok || !data || data.ok === false) {
  //         alert((data && data.error) || "Could not save track.");
  //         return;
  //       }

  //       // Close modal on success
  //       if (modalEl) {
  //         const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
  //         modal.hide();
  //       }
  //       alert(data.created ? "Track saved ✓" : "Track already saved.");

  //     } catch (err) {
  //       console.error("Save track error", err);
  //       alert("Network error.");
  //     }
  //   });
  // }

  // 3) (Optional) Intercept "Save Album" links to POST via fetch
  document.addEventListener("click", async (e) => {
    const a = e.target.closest("a[data-save-album='1'][href]");
    if (!a) return;

    // Only intercept URLs under /save/... ; otherwise let normal nav happen
    if (!a.getAttribute("href").includes("/save/")) return;

    e.preventDefault();
    try {
      const resp = await fetch(a.getAttribute("href"), {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken },
      });
      const data = await resp.json().catch(() => ({}));
      // alert(data && data.ok ? (data.created ? "Album saved ✓" : "Album already saved.") : "Could not save album.");
      const ok = !!(data && data.ok);
      if (ok) {
        const created = !!data.created;
        const message = created ? "Album saved ✓" : "Album already saved.";
        notify(message, created ? "success" : "info");
      } else {
        notify("Could not save album.", "danger");
      }
    } catch (err) {
      console.error("Save album error", err);
      notify("Network error.", "danger");
    }
  });
})();
