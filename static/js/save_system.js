(function () {
  "use strict";

  // CSRF from cookie
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return decodeURIComponent(parts.pop().split(";").shift());
  }
  const csrfToken = getCookie("csrftoken");

  // When user clicks "💾 Save Track", stash the track id into hidden input
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-track-id][data-bs-target='#saveTrackModal']");
    if (btn) {
      const tid = btn.getAttribute("data-track-id");
      const input = document.getElementById("saveTrackId");
      if (input) input.value = tid;
    }
  });

  // Handle "Save track" modal form submit via fetch
  const form = document.getElementById("saveTrackForm");
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const trackId = document.getElementById("saveTrackId").value;
      const albumId = document.getElementById("albumSelect").value;
      if (!trackId || !albumId) return;

      try {
        const resp = await fetch(`/save/tracks/${trackId}/save/`, {
          method: "POST",
          headers: {
            "X-CSRFToken": csrfToken,
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
          },
          body: new URLSearchParams({ album_id: albumId }).toString(),
        });
        const data = await resp.json();
        if (data.ok) {
          // Close modal & give a tiny toast/alert
          const modalEl = document.getElementById("saveTrackModal");
          const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
          modal.hide();
          alert(data.created ? "Track saved ✓" : "Already saved.");
        } else {
          alert(data.error || "Could not save track.");
        }
      } catch (err) {
        console.error(err);
        alert("Network error.");
      }
    });
  }

  // Optional: intercept "Save Album" link to do fetch() instead of full nav
  document.addEventListener("click", async (e) => {
    const a = e.target.closest("a[data-save-album='1'][href*='/save/album/']");
    if (!a) return;
    e.preventDefault();
    try {
      const resp = await fetch(a.getAttribute("href"), {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken },
      });
      const data = await resp.json();
      alert(data.ok ? (data.created ? "Album saved ✓" : "Already saved.") : "Could not save album.");
    } catch (err) {
      console.error(err);
      alert("Network error.");
    }
  });
})();
