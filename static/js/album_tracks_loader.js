document.addEventListener("click", async (e) => {
  const btn = e.target.closest(".js-load-tracks");
  if (!btn) return;

  const url = btn.dataset.url;
  const targetSel = btn.dataset.target;
  const target = document.querySelector(targetSel);
  if (!url || !target) return;

  // First click → fetch HTML, then toggle
  if (!target.dataset.loaded) {
    try {
      const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
      const html = await res.text();
      target.innerHTML = html;
      target.dataset.loaded = "1";
      target.classList.remove("d-none");
      btn.textContent = "Hide tracks";
    } catch (err) {
      console.error("Failed to load tracks:", err);
    }
    return;
  }

  // Subsequent clicks → just toggle visibility
  const hidden = target.classList.toggle("d-none");
  btn.textContent = hidden ? "Show tracks" : "Hide tracks";
});
