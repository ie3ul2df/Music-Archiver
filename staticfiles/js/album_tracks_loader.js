document.addEventListener("click", async (e) => {
  const btn = e.target.closest(".js-load-tracks");
  if (!btn) return;

  const url = btn.dataset.url;
  const targetSel = btn.dataset.target;
  const target = document.querySelector(targetSel);
  if (!url || !target) return;

  // Prevent double-click concurrent loads
  if (btn.dataset.loading === "1") return;

  // First click → fetch HTML, then reveal
  if (!target.dataset.loaded) {
    try {
      btn.dataset.loading = "1";
      btn.disabled = true;
      btn.setAttribute("aria-busy", "true");
      const prev = btn.textContent;
      btn.textContent = "Loading…";

      const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const html = await res.text();

      target.innerHTML = html;
      target.dataset.loaded = "1";
      target.classList.remove("d-none");

      // Hydrate newly inserted playlist toggle buttons, if helper exists
      if (window.normalizePlaylistButtons) {
        window.normalizePlaylistButtons(target);
      }

      btn.textContent = "Hide tracks";
      btn.setAttribute("data-prev-label", prev);
    } catch (err) {
      console.error("Failed to load tracks:", err);
      btn.textContent = "Retry load";
      target.classList.add("d-none");
    } finally {
      btn.dataset.loading = "0";
      btn.disabled = false;
      btn.removeAttribute("aria-busy");
    }
    return;
  }

  // Subsequent clicks → just toggle visibility
  const hidden = target.classList.toggle("d-none");
  btn.textContent = hidden ? "Show tracks" : "Hide tracks";
});
