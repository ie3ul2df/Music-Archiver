//--------------------------- static/js/music_player.js ---------------------------//
(function () {
  "use strict";

  // --- Elements ---
  const $ = (id) => document.getElementById(id);
  const audio = $("player");
  if (!audio) return; // no player on this page

  const np = $("nowplaying");
  const playpause = $("playpause");
  const stopBtn = $("stop");
  const nextBtn = $("next");
  const prevBtn = $("prev");
  const shuffleBtn = $("shuffle");
  const progress = $("progress"); // <input type="range" ...>
  const vol = $("volume"); // <input type="range" ...>
  const curTimeEl = $("currenttime"); // <span id="currenttime">
  const durEl = $("duration"); // <span id="duration">
  const playerCard = $("player-card"); // holds data-* URLs for external JS
  const checkAllGlobalBtn = $("check-all-global");

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

  const clampPct = (raw) => {
    const val = parseFloat(raw);
    if (!isFinite(val)) return 0;
    return Math.min(Math.max(val, 0), 100);
  };

  const bindInlineSeek = (input) => {
    if (!(input instanceof HTMLInputElement) || input.dataset.seekBound === "1") return;
    const onSeek = () => {
      if (audio.duration > 0) {
        const pct = clampPct(input.value);
        audio.currentTime = (pct / 100) * audio.duration;
      }
    };
    input.addEventListener("input", onSeek);
    input.addEventListener("change", onSeek);
    input.dataset.seekBound = "1";
  };

  const resetTimeline = () => {
    if (curTimeEl) curTimeEl.textContent = fmt(0);
    if (durEl) durEl.textContent = fmt(0);
    if (progress) progress.value = "0";
  };

  const hasSource = () => {
    if (audio.getAttribute("src")) return true;
    const current = audio.currentSrc;
    return !!current && current !== window.location.href;
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
    const btns = document.querySelectorAll(".play-btn, .js-inline-play");
    const progressWraps = document.querySelectorAll(".track-inline-progress");

    // clear all highlights + statuses
    btns.forEach((b) => b.classList.remove("is-playing"));
    progressWraps.forEach((wrap) => {
      wrap.classList.add("d-none");
      wrap.setAttribute("aria-hidden", "true");
      const cur = wrap.querySelector(".track-current");
      if (cur) cur.textContent = fmt(0);
      const dur = wrap.querySelector(".track-duration");
      if (dur) dur.textContent = fmt(0);
      const prog = wrap.querySelector(".track-progress");
      if (prog) prog.value = "0";
    });

    if (idx < 0 || !tracks[idx]) return;

    const current = tracks[idx];

    const matches = Array.from(btns).filter((btn) => {
      if (current.src && btn.dataset.src && btn.dataset.src === current.src) return true;
      if (current.id != null && btn.dataset.id && String(btn.dataset.id) === String(current.id)) return true;
      const row = btn.closest(".track-card, li");
      if (!row) return false;
      if (current.id != null) {
        const rowId = row.dataset.trackId || row.dataset.id;
        if (rowId && String(rowId) === String(current.id)) return true;
      }
      if (current.src) {
        const inlineAudio = row.querySelector("audio.inline-audio");
        const rowSrc = row.dataset.src || inlineAudio?.getAttribute("src");
        if (rowSrc && rowSrc === current.src) return true;
      }
      return false;
    });

    matches.forEach((activeBtn) => {
      activeBtn.classList.add("is-playing");
      const row = activeBtn.closest(".track-card, li");
      if (!row) return;
      const wrap = row.querySelector(".track-inline-progress");
      if (!wrap) return;

      wrap.classList.remove("d-none");
      wrap.setAttribute("aria-hidden", "false");

      const cur = wrap.querySelector(".track-current");
      if (cur) cur.textContent = fmt(audio.currentTime);

      const dur = wrap.querySelector(".track-duration");
      if (dur && isFinite(audio.duration)) dur.textContent = fmt(audio.duration);

      const prog = wrap.querySelector(".track-progress");
      if (prog) {
        bindInlineSeek(prog);
        if (audio.duration > 0) {
          prog.value = ((audio.currentTime / audio.duration) * 100).toFixed(2);
        } else {
          prog.value = "0";
        }
      }
    });
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

  function clearPlayback({ clearQueue = false, clearChecks = false } = {}) {
    audio.pause();
    audio.currentTime = 0;
    audio.src = "";
    audio.removeAttribute("src");
    audio.load();

    if (clearQueue) tracks = [];
    idx = -1;

    setNowPlaying();
    highlightActiveButton();
    resetTimeline();
    setPlaypauseLabel();

    if (clearChecks) {
      document.querySelectorAll(".track-check:checked").forEach((cb) => {
        cb.checked = false;
      });
      document.querySelectorAll(".playlist-check-all, .favorites-check-all, .recent-check-all, .check-all").forEach((el) => {
        if (el instanceof HTMLInputElement) el.checked = false;
      });
      if (checkAllGlobalBtn) checkAllGlobalBtn.textContent = "✔ All";
    }
  }

  function stopPlayback() {
    const useCheckboxQueue = checkboxMode();
    clearPlayback({ clearQueue: useCheckboxQueue, clearChecks: useCheckboxQueue });
  }

  // --- Build queue from checked rows (DOM order) ---
  function getCheckedTracksInDOMOrder(scopeEl = null) {
    const scope = scopeEl || document.querySelector(".tab-pane.show.active") || document;
    const rows = scope.querySelectorAll("ul.tracks li.track-item, ul.tracks li.track-card");
    const arr = [];

    rows.forEach((li) => {
      const cb = li.querySelector(".track-check");
      if (!cb || !cb.checked) return;

      const playBtn = li.querySelector(".play-btn, .js-inline-play");
      const audioEl = li.querySelector("audio.inline-audio");
      const src = playBtn?.dataset?.src || li.dataset.src || (audioEl ? audioEl.getAttribute("src") : "") || "";
      if (!src) return;

      const id = playBtn?.dataset?.id || li.dataset.trackId || li.dataset.id || null;

      const name =
        playBtn?.dataset?.name ||
        li.dataset.name ||
        li.querySelector(".flex-grow-1")?.textContent?.trim() ||
        li.querySelector(".fw-semibold")?.textContent?.trim() ||
        "Untitled";

      arr.push({ id, name, src });
    });

    const seen = new Set();
    return arr.filter((t) => {
      if (!t.src || seen.has(t.src)) return false;
      seen.add(t.src);
      return true;
    });
  }

  function rebuildQueueFromChecks({ maintainCurrent = true, autoplay = false, scope = null } = {}) {
    const currentSrc = tracks[idx]?.src || null;
    const newQ = getCheckedTracksInDOMOrder(scope);
    tracks = newQ;

    if (!tracks.length) {
      clearPlayback({ clearQueue: true });
      return;
    }

    const newIndex = maintainCurrent && currentSrc ? tracks.findIndex((t) => t.src === currentSrc) : -1;

    if (newIndex !== -1) {
      idx = newIndex;
      setNowPlaying("Now");
      highlightActiveButton();
      setPlaypauseLabel();
      if (autoplay) {
        const same = !!audio.currentSrc && tracks[idx] && audio.currentSrc === tracks[idx].src;
        same ? audio.play() : load(idx, true);
        setPlaypauseLabel();
      }
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
    audio.load();
    setNowPlaying("Now");
    highlightActiveButton();
    resetTimeline();

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
    if (hasSource()) {
      if (audio.paused) {
        const p = audio.play();
        if (p && typeof p.catch === "function") p.catch(() => {});
      } else {
        audio.pause();
      }
      setPlaypauseLabel();
      return;
    }
    const pane = document.querySelector(".tab-pane.show.active");
    const anyCheckedInActive = (pane || document).querySelector(".track-check:checked");
    if (anyCheckedInActive) {
      rebuildQueueFromChecks({ maintainCurrent: false, autoplay: true, scope: pane || document });
      return;
    }
    if (tracks.length) load(0, true);
  }

  // --- Transport events ---
  if (playpause) playpause.addEventListener("click", togglePlayPause);
  if (nextBtn) nextBtn.addEventListener("click", next);
  if (prevBtn) prevBtn.addEventListener("click", prev);
  if (stopBtn) stopBtn.addEventListener("click", stopPlayback);

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
  audio.addEventListener("emptied", resetTimeline);

  audio.addEventListener("loadedmetadata", () => {
    if (durEl) durEl.textContent = fmt(audio.duration);
  });

  audio.addEventListener("timeupdate", () => {
    if (curTimeEl) curTimeEl.textContent = fmt(audio.currentTime);
    if (progress && audio.duration > 0) {
      progress.value = ((audio.currentTime / audio.duration) * 100).toFixed(2);
    }

    // update ALL active row indicators
    const activeBtns = document.querySelectorAll(".play-btn.is-playing, .js-inline-play.is-playing");
    activeBtns.forEach((btn) => {
      const row = btn.closest(".track-card, li");
      if (!row) return;
      const wrap = row.querySelector(".track-inline-progress");
      if (!wrap || wrap.classList.contains("d-none")) return;
      const cur = wrap.querySelector(".track-current");
      const dur = wrap.querySelector(".track-duration");
      const prog = wrap.querySelector(".track-progress");
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
        if (e.target.classList?.contains("track-check")) {
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
    const btn = e.target.closest(".play-btn, .js-inline-play");
    if (!btn) return;

    const li = btn.closest("li");
    const audioEl = li?.querySelector("audio.inline-audio");

    const src = btn.dataset.src || li?.dataset.src || (audioEl ? audioEl.getAttribute("src") : "") || "";

    const name =
      btn.dataset.name ||
      li?.dataset.name ||
      li?.querySelector(".flex-grow-1")?.textContent?.trim() ||
      li?.querySelector(".fw-semibold")?.textContent?.trim() ||
      "Untitled";

    const id = btn.dataset.id || li?.dataset.trackId || li?.dataset.id || null;
    if (!src) return;

    let i = tracks.findIndex((t) => t.src === src || (id && String(t.id) === String(id)));

    // Same row → toggle pause/play
    if (i !== -1 && i === idx && hasSource()) {
      if (audio.paused) {
        const p = audio.play();
        if (p && typeof p.catch === "function") p.catch(() => {});
      } else {
        audio.pause();
      }
      setPlaypauseLabel();
      return;
    }

    if (i === -1) {
      tracks.push({ id: id ? id : null, name, src });
      i = tracks.length - 1;
    }
    load(i, true);
  });

  // Playlist/Favourites/Recent "Check All" toggles every row, then rebuild
  // the queue. When switching lists, previously checked tracks in other lists
  // are cleared so only one group plays at a time.
  document.addEventListener("change", (e) => {
    const id = e.target?.id;
    const map = {
      "playlist-check-all": "playlist-tracks",
      "favorites-check-all": "favorites-tracks",
      "recent-check-all": "recent-tracks",
    };
    if (!id || !(id in map)) return;

    const checked = !!e.target.checked;
    const list = document.getElementById(map[id]);
    const pane = list?.closest(".tab-pane");

    if (list) {
      list.querySelectorAll(".track-check").forEach((cb) => {
        cb.checked = checked;
      });
    }

    // Optional: uncheck other groups when one is checked
    if (checked) {
      Object.entries(map).forEach(([otherId, otherListId]) => {
        if (otherId === id) return;
        const otherChk = document.getElementById(otherId);
        if (otherChk) otherChk.checked = false;
        const otherList = document.getElementById(otherListId);
        if (otherList)
          otherList.querySelectorAll(".track-check").forEach((cb) => {
            cb.checked = false;
          });
      });
    }

    // Single rebuild, scoped to the correct tab/list
    rebuildQueueFromChecks({
      maintainCurrent: false,
      autoplay: true, // start immediately if you like
      scope: pane || list || document,
    });
  });

  document.addEventListener("change", (e) => {
    if (e.target.classList?.contains("track-check")) {
      const list = e.target.closest("ul.tracks");
      const pane = e.target.closest(".tab-pane");
      rebuildQueueFromChecks({
        maintainCurrent: true,
        autoplay: false,
        scope: pane || list || document,
      });
    }
  });
})();
