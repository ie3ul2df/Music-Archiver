(function () {
  "use strict";

  function csvSet(str) {
    return new Set(
      (str || "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
    );
  }

  function readState() {
    const playlistMeta = document.getElementById("playlist-meta");
    const stateMeta = document.getElementById("state-meta");
    return {
      inSet: csvSet(playlistMeta ? playlistMeta.dataset.inIds : ""),
      favSet: csvSet(stateMeta ? stateMeta.dataset.favIds : ""),
      mySet: csvSet(stateMeta ? stateMeta.dataset.myIds : ""),
    };
  }

  function hydrate(root) {
    const { inSet, favSet, mySet } = readState();
    const scope = root || document;

    scope.querySelectorAll(".track-card[data-track-id]").forEach((card) => {
      const tid = card.getAttribute("data-track-id");
      if (!tid) return;

      // ♥ Favourite button
      const favBtn = card.querySelector(".js-fav");
      if (favBtn) {
        const fav = favSet.has(tid);
        favBtn.classList.toggle("btn-danger", fav);
        favBtn.classList.toggle("btn-outline-danger", !fav);
        favBtn.setAttribute("aria-pressed", fav ? "true" : "false");
        favBtn.textContent = fav ? "♥" : "♡";
      }

      // 💾 / 🗃 Save button
      const saveBtn = card.querySelector(".js-save");
      if (saveBtn) {
        const inMine = mySet.has(tid);
        // only swap visible icon; keep attributes/tooltips intact
        saveBtn.textContent = inMine ? "🗃️" : "💾";
      }

      // ✓ / ➕ Playlist button (kept consistent with your existing approach)
      const plBtn = card.querySelector(".add-to-playlist");
      if (plBtn) {
        const inpl = inSet.has(tid);
        plBtn.classList.toggle("btn-success", inpl);
        plBtn.classList.toggle("btn-outline-success", !inpl);
        plBtn.setAttribute("data-in", inpl ? "1" : "0");
        plBtn.setAttribute("aria-pressed", inpl ? "true" : "false");
        plBtn.textContent = inpl ? "✓" : "➕";
      }
    });
  }

  // Run on page load
  document.addEventListener("DOMContentLoaded", () => hydrate(document));

  // Auto-hydrate any content inserted later (AJAX, tabs, etc.)
  const mo = new MutationObserver((muts) => {
    for (const m of muts) {
      m.addedNodes.forEach((node) => {
        if (!(node instanceof Element)) return;
        if (node.matches(".track-card,[data-track-id]") || node.querySelector(".track-card")) {
          hydrate(node);
        }
      });
    }
  });
  mo.observe(document.documentElement, { childList: true, subtree: true });

  // Expose manual hook if you want to call it explicitly
  window.hydrateTrackButtons = hydrate;
})();
