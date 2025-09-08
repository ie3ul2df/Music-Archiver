(function () {
  "use strict";

  // CSRF
  function csrftoken() {
    const m = document.cookie.match(/(?:^|;)\s*csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  // Delegated clicks
  document.addEventListener("click", async (e) => {
    const favBtn = e.target.closest(".js-fav");
    const saveBtn = e.target.closest(".js-save");
    const playBtn = e.target.closest(".js-inline-play");

    // Toggle favourite
    if (favBtn) {
      e.preventDefault();
      const url = favBtn.dataset.url;
      try {
        const res = await fetch(url, { method: "POST", headers: { "X-CSRFToken": csrftoken() } });
        if (res.ok) {
          favBtn.classList.toggle("btn-danger");
          favBtn.classList.toggle("btn-outline-danger");
        }
      } catch {}
    }

    // Open Save modal
    if (saveBtn) {
      e.preventDefault();
      const row = saveBtn.closest(".track-card");
      const trackId = row?.dataset.trackId;
      const saveUrl = saveBtn.dataset.saveUrl;
      const modalEl = document.getElementById("saveToAlbumModal");
      if (!modalEl || !trackId || !saveUrl) return;

      document.getElementById("save-track-id").value = trackId;
      document.getElementById("save-url").value = saveUrl;

      const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
      modal.show();
    }

    // Inline play/pause
    if (playBtn) {
      e.preventDefault();
      const row = playBtn.closest(".track-card");
      const audio = row?.querySelector(".inline-audio");
      if (!audio) return;

      audio.classList.remove("d-none");

      if (audio.paused) {
        audio.play().catch(() => {});
        playBtn.textContent = "⏸";
      } else {
        audio.pause();
        playBtn.textContent = "▶";
      }
    }
  });

  // Save form submit
  const saveForm = document.getElementById("save-to-album-form");
  if (saveForm) {
    saveForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const albumId = document.getElementById("save-album-select").value;
      const saveUrl = document.getElementById("save-url").value;

      const fd = new FormData();
      fd.append("album_id", albumId);

      const res = await fetch(saveUrl, {
        method: "POST",
        headers: { "X-CSRFToken": csrftoken() },
        body: fd,
      });

      if (res.ok) {
        bootstrap.Modal.getInstance(document.getElementById("saveToAlbumModal"))?.hide();
      } else {
        alert("Could not save to album.");
      }
    });
  }

  // Log play on <audio> 'play'
  document.addEventListener(
    "play",
    (e) => {
      const audio = e.target;
      if (!(audio instanceof HTMLAudioElement)) return;
      const url = audio.dataset.logUrl;
      if (!url) return;
      // fire-and-forget
      fetch(url, { method: "POST", headers: { "X-CSRFToken": csrftoken() } }).catch(() => {});
    },
    true
  );
})();
