// -------- static/js/toggle_fav_btn.js
(function () {
  function fillId(urlTmpl, id) {
    return urlTmpl.replace(/\/\d+\/?$/, "/" + id + "/");
  }

  const cfg = document.getElementById("player-card");
  const favUrlTmpl = cfg?.dataset.toggleFavUrl;

  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".fav-btn");
    if (!btn || !favUrlTmpl) return;

    const id = btn.dataset.track;
    if (!id) return;

    fetch(fillId(favUrlTmpl, id), {
      method: "POST",
      headers: { "X-CSRFToken": getCookie("csrftoken") },
    })
      .then((r) => r.json())
      .then(({ favorited }) => {
        btn.classList.toggle("active", favorited);
        btn.setAttribute("aria-pressed", favorited ? "true" : "false");
        btn.textContent = favorited ? "♥" : "♡";

        // keep all instances in sync
        document.querySelectorAll(`.fav-btn[data-track="${id}"]`).forEach((b) => {
          if (b === btn) return;
          b.classList.toggle("active", favorited);
          b.setAttribute("aria-pressed", favorited ? "true" : "false");
          b.textContent = favorited ? "♥" : "♡";
        });

        // if in "Your favourites" list, remove on unfavourite
        if (!favorited && btn.closest("[data-fav-list]")) {
          btn.closest("li")?.remove();
        }
      })
      .catch(console.error);
  });
})();

console.log("toggle_fav_btn.js loaded ✅");
