/* jshint esversion: 11 */
/* global bootstrap */
(function () {
  "use strict";

  const globalPlayer = document.getElementById("player");

  // CSRF
  function csrftoken() {
    const m = document.cookie.match(/(?:^|;)\s*csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  function formatTime(seconds) {
    if (!isFinite(seconds) || seconds < 0) return "0:00";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? "0" : ""}${secs}`;
  }

  function findInlinePlayButton(audioEl) {
    const container = audioEl.closest(".track-card, li");
    return container?.querySelector(".js-inline-play") || null;
  }

  function findInlineProgressWrap(audioEl) {
    if (!(audioEl instanceof HTMLAudioElement)) return null;
    return audioEl.closest(".track-card, li")?.querySelector(".track-inline-progress") || null;
  }

  function updateInlineProgress(audioEl) {
    const wrap = findInlineProgressWrap(audioEl);
    if (!wrap) return;

    const cur = wrap.querySelector(".track-current");
    const dur = wrap.querySelector(".track-duration");
    const slider = wrap.querySelector(".track-progress");

    if (cur) cur.textContent = formatTime(audioEl.currentTime || 0);

    if (dur) {
      const duration = audioEl.duration;
      dur.textContent = isFinite(duration) ? formatTime(duration) : formatTime(0);
    }

    if (slider) {
      const duration = audioEl.duration;
      if (isFinite(duration) && duration > 0) {
        const pct = (audioEl.currentTime / duration) * 100;
        slider.value = pct.toFixed(2);
      } else {
        slider.value = "0";
      }
    }
  }

  function showInlineProgress(audioEl) {
    const wrap = findInlineProgressWrap(audioEl);
    if (!wrap) return;

    wrap.classList.remove("d-none");
    wrap.setAttribute("aria-hidden", "false");
    updateInlineProgress(audioEl);
  }

  function hideInlineProgress(audioEl, { reset = false } = {}) {
    const wrap = findInlineProgressWrap(audioEl);
    if (!wrap) return;

    wrap.classList.add("d-none");
    wrap.setAttribute("aria-hidden", "true");

    if (!reset) return;

    const cur = wrap.querySelector(".track-current");
    const dur = wrap.querySelector(".track-duration");
    const slider = wrap.querySelector(".track-progress");

    if (cur) cur.textContent = formatTime(0);
    if (dur) dur.textContent = formatTime(0);
    if (slider) slider.value = "0";
  }

  function bindInlineProgress(audioEl) {
    if (!(audioEl instanceof HTMLAudioElement)) return;
    if (audioEl.dataset.progressBound === "1") return;

    const wrap = findInlineProgressWrap(audioEl);
    if (!wrap) return;

    const slider = wrap.querySelector(".track-progress");
    if (slider && slider.dataset.seekBound !== "1") {
      const onSeek = () => {
        if (!isFinite(audioEl.duration) || audioEl.duration <= 0) return;
        const raw = parseFloat(slider.value);
        const pct = isFinite(raw) ? Math.min(Math.max(raw, 0), 100) : 0;
        audioEl.currentTime = (pct / 100) * audioEl.duration;
      };
      slider.addEventListener("input", onSeek);
      slider.addEventListener("change", onSeek);
      slider.dataset.seekBound = "1";
    }

    audioEl.addEventListener("loadedmetadata", () => updateInlineProgress(audioEl));
    audioEl.addEventListener("timeupdate", () => updateInlineProgress(audioEl));
    audioEl.addEventListener("emptied", () => hideInlineProgress(audioEl, { reset: true }));
    audioEl.addEventListener("ended", () => hideInlineProgress(audioEl, { reset: true }));

    audioEl.dataset.progressBound = "1";
  }

  function setInlineButtonState(audioEl, isPlaying) {
    const btn = findInlinePlayButton(audioEl);
    if (!btn) return;
    btn.textContent = isPlaying ? "⏸" : "▶";
    btn.classList.toggle("is-playing", !!isPlaying);
    btn.setAttribute("aria-pressed", isPlaying ? "true" : "false");
  }

  function pauseOtherAudios(except) {
    document.querySelectorAll("audio").forEach((el) => {
      if (!(el instanceof HTMLAudioElement) || el === except) return;
      el.pause();
      if (el.classList.contains("inline-audio")) {
        setInlineButtonState(el, false);
        hideInlineProgress(el, { reset: true });
      }
    });
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
      const form = document.getElementById("save-to-album-form");
      if (!modalEl || !form || !trackId || !saveUrl) return;

      document.getElementById("save-track-id").value = trackId;
      form.setAttribute("action", saveUrl);

      const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
      modal.show();
    }

    // Inline play/pause
    if (playBtn) {
      if (globalPlayer) {
        return;
      }
      e.preventDefault();
      const row = playBtn.closest(".track-card");
      const audio = row?.querySelector(".inline-audio");
      if (!audio) return;

      audio.classList.remove("d-none");
      bindInlineProgress(audio);

      if (audio.paused) {
        pauseOtherAudios(audio);
        const playPromise = audio.play();
        if (playPromise && typeof playPromise.catch === "function") {
          playPromise.catch(() => {});
        }
        showInlineProgress(audio);
        setInlineButtonState(audio, true);
      } else {
        audio.pause();
        setInlineButtonState(audio, false);
      }
    }
  });

  // Log play on <audio> 'play'
  document.addEventListener(
    "play",
    (e) => {
      const audio = e.target;
      if (!(audio instanceof HTMLAudioElement)) return;
      pauseOtherAudios(audio);
      if (audio.classList.contains("inline-audio")) {
        audio.classList.remove("d-none");
        bindInlineProgress(audio);
        showInlineProgress(audio);
        setInlineButtonState(audio, true);
      }
      const url = audio.dataset.logUrl;
      if (!url) return;
      // fire-and-forget
      fetch(url, { method: "POST", headers: { "X-CSRFToken": csrftoken() } }).catch(() => {});
    },
    true
  );

  document.addEventListener(
    "pause",
    (e) => {
      const audio = e.target;
      if (!(audio instanceof HTMLAudioElement)) return;
      if (audio.classList.contains("inline-audio")) {
        setInlineButtonState(audio, false);
        if (audio.ended) {
          hideInlineProgress(audio, { reset: true });
        }
      }
    },
    true
  );
})();

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".rotate-dropdown-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      btn.classList.toggle("rotate-180");
    });
  });
});
