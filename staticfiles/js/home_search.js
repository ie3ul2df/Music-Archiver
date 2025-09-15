(function () {
  "use strict";

  const form = document.getElementById("search-form");
  if (!form) return;

  const qInput = document.getElementById("q");
  const tSelect = document.getElementById("t");
  const results = document.getElementById("search-results");
  const summary = document.getElementById("search-summary");
  const loading = document.getElementById("search-loading");

  let debounceId = null;

  function setLoading(state) {
    if (!loading) return;
    loading.classList.toggle("d-none", !state);
  }

  function buildUrl(q, t) {
    const url = new URL(form.action || window.location.href, window.location.origin);
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (t && t !== "all") params.set("t", t);
    url.search = params.toString();
    return url.toString();
  }

  async function doSearch(pushState = true) {
    const q = qInput.value.trim();
    const t = (tSelect.value || "all").toLowerCase();

    setLoading(true);
    try {
      const url = buildUrl(q, t);
      const res = await fetch(url, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      if (!res.ok) throw new Error("Network error");
      const data = await res.json();

      if (summary) summary.innerHTML = data.html.summary || "";
      if (results) {
        const hasAny =
          (data.html.albums && data.html.albums.trim()) || (data.html.tracks && data.html.tracks.trim()) || (data.html.users && data.html.users.trim());
        results.innerHTML = hasAny ? data.html.albums + data.html.tracks + data.html.users : data.html.empty || "";
      }

      if (pushState) {
        // keep the URL in sync so it’s shareable / back-button friendly
        window.history.replaceState({}, "", buildUrl(q, t));
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  function debounceSearch() {
    clearTimeout(debounceId);
    debounceId = setTimeout(() => doSearch(true), 300);
  }

  // Submit -> intercept
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    doSearch(true);
  });

  // Live typing -> debounce
  qInput.addEventListener("input", debounceSearch);

  // Scope change -> immediate search
  tSelect.addEventListener("change", () => doSearch(true));
})();
