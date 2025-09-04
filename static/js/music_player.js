//--------------------------- static/js/music_player.js ---------------------------//
(function () {
  "use strict";

  // --- Elements ---
  const $ = (id) => document.getElementById(id);
  const audio = $("player");
  if (!audio) return; // no player on this page

  const np = $("nowplaying");
  const playpause = $("playpause");
  const nextBtn = $("next");
  const prevBtn = $("prev");
  const shuffleBtn = $("shuffle");
  const progress = $("progress"); // <input type="range" ...>
  const vol = $("volume"); // <input type="range" ...>
  const curTimeEl = $("currenttime"); // <span id="currenttime">
  const durEl = $("duration"); // <span id="duration">
  const playerCard = $("player-card"); // holds data-* URLs for external JS

  // --- Config from data-* attributes (NO inline <script>) ---
  const TRACKS_JSON_URL = playerCard?.dataset.tracksUrl || null;
  const LOG_PLAY_URL_TMPL = playerCard?.dataset.logPlayUrl || null;

  // --- State ---
  let tracks = [];
  let idx = -1;
  let shuffled = localStorage.getItem("player_shuffle") === "1";

  // Convenience: are we on a page with checkboxes (track list)?
  const checkboxMode = () => !!document.querySelector(".track-check");

  // --- Utils ---
  const clampIndex = (i) => (tracks.length ? (i + tracks.length) % tracks.length : -1);
  const fmt = (s) => {
    if (!isFinite(s) || s < 0) return "0:00";
    const m = Math.floor(s / 60);
    const r = Math.floor(s % 60);
    return m + ":" + (r < 10 ? "0" + r : r);
  };

  const setPlaypauseLabel = () => {
    if (!playpause) return;
    playpause.textContent = audio.paused ? "▶ Play" : "⏸ Pause";
    playpause.setAttribute("aria-pressed", (!audio.paused).toString());
  };

  const updateShuffleUI = () => {
    if (!shuffleBtn) return;
    shuffleBtn.classList.toggle("active", shuffled);
    shuffleBtn.setAttribute("aria-pressed", shuffled.toString());
  };

  const highlightActiveButton = () => {
    const btns = document.querySelectorAll(".play-btn");
    const statuses = document.querySelectorAll(".track-playing-status");

    // clear all highlights + statuses
    btns.forEach((b) => b.classList.remove("is-playing"));
    statuses.forEach((s) => (s.innerHTML = ""));

    if (idx >= 0 && tracks[idx]) {
      const t = tracks[idx];

      // find *all* matching buttons
      const matchingBtns = Array.from(btns).filter((b) => b.dataset.src === t.src || (t.id && String(b.dataset.id) === String(t.id)));

      matchingBtns.forEach((activeBtn) => {
        activeBtn.classList.add("is-playing");

        const li = activeBtn.closest("li");
        const statusEl = li?.querySelector(".track-playing-status");
        if (statusEl) {
          statusEl.innerHTML = `
          <div class="d-flex align-items-center gap-1 small text-muted">
            <span class="track-current">0:00</span>
            <input type="range" class="track-progress" min="0" max="100" value="0" style="flex:1">
            <span class="track-duration">0:00</span>
          </div>`;

          // attach seek event for this row’s slider
          const prog = statusEl.querySelector(".track-progress");
          prog.addEventListener("input", () => {
            if (audio.duration > 0) {
              const pct = Math.min(Math.max(parseFloat(prog.value) || 0, 0), 100);
              audio.currentTime = (pct / 100) * audio.duration;
            }
          });
        }
      });
    }
  };

  const setNowPlaying = (prefix = "Now") => {
    if (!np) return;
    if (idx < 0 || !tracks[idx]) {
      np.textContent = "Idle";
      return;
    }
    const t = tracks[idx];
    np.textContent = `${prefix}: ${t.name || "Untitled"}`;
  };

  const fillId = (urlTmpl, id) => (urlTmpl ? urlTmpl.replace(/\/\d+\/?$/, "/" + id + "/") : null);

  function logPlay(trackId) {
    if (!trackId || !LOG_PLAY_URL_TMPL) return;
    const url = fillId(LOG_PLAY_URL_TMPL, trackId);
    if (!url) return;
    const csrf = typeof getCookie === "function" ? getCookie("csrftoken") : "";
    fetch(url, { method: "POST", headers: { "X-CSRFToken": csrf } }).catch(() => {});
  }

  // --- Build queue from checked rows (DOM order) ---
  function getCheckedTracksInDOMOrder() {
    const albums = document.querySelectorAll(".album");
    const arr = [];
    albums.forEach((album) => {
      const lis = album.querySelectorAll(".tracks > li");
      lis.forEach((li) => {
        const cb = li.querySelector(".track-check");
        if (cb && cb.checked) {
          const btn = li.querySelector(".play-btn");
          const src = btn?.dataset.src || "";
          if (!src) return; // skip rows without audio source
          const id = btn?.dataset.id || li.dataset.id || null;
          const name = btn?.dataset.name || li.querySelector("span")?.textContent?.trim() || "Untitled";
          arr.push({ id, name, src });
        }
      });
    });
    // de-dup by src
    const seen = new Set();
    return arr.filter((t) => {
      if (!t.src || seen.has(t.src)) return false;
      seen.add(t.src);
      return true;
    });
  }

  function rebuildQueueFromChecks({ maintainCurrent = true, autoplay = false } = {}) {
    if (!checkboxMode()) return;

    const currentSrc = tracks[idx]?.src || null;
    const newQ = getCheckedTracksInDOMOrder();
    tracks = newQ;

    if (!tracks.length) {
      idx = -1;
      audio.pause();
      audio.removeAttribute("src");
      setNowPlaying();
      setPlaypauseLabel();
      highlightActiveButton();
      return;
    }

    const newIndex = maintainCurrent && currentSrc ? tracks.findIndex((t) => t.src === currentSrc) : -1;

    if (newIndex !== -1) {
      idx = newIndex;
      setNowPlaying("Now");
      highlightActiveButton();
      setPlaypauseLabel();
    } else {
      idx = 0;
      setNowPlaying("Ready");
      setPlaypauseLabel();
      if (autoplay) load(0, true);
    }
  }

  // --- Core ---
  function load(i, autoplay = true) {
    if (!tracks.length) return;
    idx = clampIndex(i);
    const t = tracks[idx];
    if (!t) return;

    audio.src = t.src;
    setNowPlaying("Now");
    highlightActiveButton();

    if (autoplay) {
      const p = audio.play();
      if (p && typeof p.catch === "function") p.catch(() => {});
    }
    setPlaypauseLabel();

    if (t.id != null) logPlay(t.id);
  }

  function next() {
    if (!tracks.length) return;
    if (shuffled) {
      if (tracks.length === 1) return load(idx, true);
      let r;
      do {
        r = Math.floor(Math.random() * tracks.length);
      } while (r === idx);
      return load(r, true);
    }
    return load(idx + 1, true);
  }

  function prev() {
    if (!tracks.length) return;
    return load(idx - 1, true);
  }

  function togglePlayPause() {
    if (!audio.src) {
      // If no source yet, build queue from checks (if any) and start
      if (!tracks.length && checkboxMode()) {
        rebuildQueueFromChecks({ maintainCurrent: false, autoplay: true });
        return;
      }
      if (tracks.length) {
        load(0, true);
        return;
      }
    }
    if (audio.paused) audio.play();
    else audio.pause();
    setPlaypauseLabel();
  }

  // --- Transport events ---
  if (playpause) playpause.addEventListener("click", togglePlayPause);
  if (nextBtn) nextBtn.addEventListener("click", next);
  if (prevBtn) prevBtn.addEventListener("click", prev);

  if (shuffleBtn) {
    updateShuffleUI();
    shuffleBtn.addEventListener("click", () => {
      shuffled = !shuffled;
      localStorage.setItem("player_shuffle", shuffled ? "1" : "0");
      updateShuffleUI();
    });
  }

  // --- Audio events ---
  audio.addEventListener("ended", next);
  audio.addEventListener("play", setPlaypauseLabel);
  audio.addEventListener("pause", setPlaypauseLabel);

  audio.addEventListener("loadedmetadata", () => {
    if (durEl) durEl.textContent = fmt(audio.duration);
  });

  audio.addEventListener("timeupdate", () => {
    if (curTimeEl) curTimeEl.textContent = fmt(audio.currentTime);
    if (progress && audio.duration > 0) {
      progress.value = ((audio.currentTime / audio.duration) * 100).toFixed(2);
    }

    // update ALL active row indicators
    const activeLis = document.querySelectorAll("li .play-btn.is-playing");
    activeLis.forEach((btn) => {
      const li = btn.closest("li");
      const cur = li?.querySelector(".track-current");
      const dur = li?.querySelector(".track-duration");
      const prog = li?.querySelector(".track-progress");
      if (cur) cur.textContent = fmt(audio.currentTime);
      if (dur && isFinite(audio.duration)) dur.textContent = fmt(audio.duration);
      if (prog && audio.duration > 0) {
        prog.value = ((audio.currentTime / audio.duration) * 100).toFixed(2);
      }
    });
  });

  // --- Progress + volume ---
  if (progress) {
    const scrub = () => {
      if (audio.duration > 0) {
        const pct = Math.min(Math.max(parseFloat(progress.value) || 0, 0), 100);
        audio.currentTime = (pct / 100) * audio.duration;
      }
    };
    progress.addEventListener("input", scrub);
    progress.addEventListener("change", scrub);
  }

  if (vol) {
    const clamp01 = (v) => Math.min(Math.max(v, 0), 1);
    const savedVol = parseFloat(localStorage.getItem("player_volume"));
    const initial = isFinite(savedVol) ? clamp01(savedVol) : typeof vol.value !== "undefined" ? clamp01(parseFloat(vol.value) || audio.volume) : audio.volume;

    audio.volume = initial;
    if (typeof vol.value !== "undefined") vol.value = String(initial);
    const setVol = () => {
      const v = clamp01(parseFloat(vol.value) || 0);
      audio.volume = v;
      localStorage.setItem("player_volume", String(v));
    };
    vol.addEventListener("input", setVol);
    vol.addEventListener("change", setVol);
  }

  // --- Keyboard shortcuts (space, arrows) ---
  document.addEventListener("keydown", (e) => {
    const tag = document.activeElement?.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA") return;
    if (e.code === "Space") {
      e.preventDefault();
      togglePlayPause();
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      next();
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      prev();
    }
  });

  // --- Bootstrap initial queue ---
  document.addEventListener("DOMContentLoaded", () => {
    if (checkboxMode()) {
      // Build initial queue from any pre-checked rows
      rebuildQueueFromChecks({ maintainCurrent: false, autoplay: false });

      // Rebuild when user checks/unticks
      document.addEventListener("change", (e) => {
        if (e.target.classList?.contains("track-check") || e.target.classList?.contains("check-all")) {
          rebuildQueueFromChecks({ maintainCurrent: true, autoplay: false });
        }
      });

      // Rebuild when user finishes a drag (tracks or albums)
      const albumsEl = document.getElementById("albums");
      if (albumsEl) albumsEl.addEventListener("dragend", () => rebuildQueueFromChecks({ maintainCurrent: true }));
    } else if (TRACKS_JSON_URL) {
      // Fallback: fetch from JSON if there is no checkbox UI on this page
      fetch(TRACKS_JSON_URL)
        .then((r) => r.json())
        .then((data) => {
          const list = Array.isArray(data?.tracks) ? data.tracks : [];
          tracks = list
            .map((t) => ({
              id: t.id != null ? t.id : null,
              name: t.name || t.title || "Untitled",
              src: t.src || t.file_url || t.url || "",
            }))
            .filter((t) => t.src);

          if (tracks.length) {
            idx = 0;
            setNowPlaying("Ready");
            setPlaypauseLabel();
          } else {
            np && (np.textContent = "No tracks available");
          }
        })
        .catch(() => {
          np && (np.textContent = "Error loading tracks");
        });
    } else {
      np && (np.textContent = "No data source configured");
    }
  });

  // --- Play buttons in lists (event delegation) ---
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".play-btn");
    if (!btn) return;

    const src = btn.dataset.src || "";
    const name = btn.dataset.name || "Untitled";
    const id = btn.dataset.id || null;
    if (!src) return;

    // Try to find in current queue first
    let i = tracks.findIndex((t) => t.src === src || (id && String(t.id) === String(id)));
    if (i === -1) {
      // Not in queue: append it (even if not checked)
      tracks.push({ id: id ? id : null, name, src });
      i = tracks.length - 1;
    }
    load(i, true);
  });
})();
