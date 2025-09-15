(function () {
  "use strict";

  const notify = (message, level) => {
    if (typeof window.showMessage === "function") {
      return window.showMessage(message, level);
    }
    if (typeof window.alert === "function") {
      window.alert(message);
    }
    return false;
  };

  // ---- CSRF from cookie (Django)
  function getCookie(name) {
    const m = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return m ? m.pop() : "";
  }
  const csrftoken = getCookie("csrftoken");

  // ---- Helpers
  function starsIn(widget) {
    return widget.querySelectorAll(".star-btn");
  }
  function setHover(widget, value) {
    starsIn(widget).forEach((btn) => {
      const v = parseInt(btn.dataset.value, 10);
      btn.classList.toggle("is-hover", v <= value);
    });
  }
  function clearHover(widget) {
    starsIn(widget).forEach((btn) => btn.classList.remove("is-hover"));
  }
  function replaceWidget(oldWidget, html) {
    const temp = document.createElement("div");
    temp.innerHTML = html;
    const fresh = temp.firstElementChild;
    if (fresh) oldWidget.replaceWith(fresh);
  }

  // ---- Hover (event delegation)
  document.addEventListener("mouseover", (e) => {
    const btn = e.target.closest(".star-btn");
    if (!btn) return;
    const widget = btn.closest(".star-rating");
    if (!widget) return;
    const val = parseInt(btn.dataset.value, 10);
    setHover(widget, val);
  });

  // Clear hover when leaving the star row
  document.addEventListener(
    "mouseleave",
    (e) => {
      const stars = e.target;
      if (!stars.matches || !stars.matches(".star-rating .stars")) return;
      const widget = stars.closest(".star-rating");
      if (widget) clearHover(widget);
    },
    true
  ); // use capture because mouseleave doesn't bubble

  // ---- Click (rate)
  document.addEventListener("click", async (e) => {
    const btn = e.target.closest(".star-btn");
    if (!btn) return;

    const widget = btn.closest(".star-rating");
    if (!widget) return;

    const type = widget.dataset.type; // "album" | "track"
    const id = widget.dataset.id;
    const value = btn.dataset.value;

    const url = type === "album" ? `/ratings/album/${id}/rate/` : `/ratings/track/${id}/rate/`;

    try {
      widget.classList.add("is-busy");
      const res = await fetch(url, {
        method: "POST",
        headers: { "X-CSRFToken": csrftoken },
        body: new URLSearchParams({ stars: value }),
      });

      if (res.status === 401) {
        notify("Please log in to rate.", "warning");
        return;
      }

      const data = await res.json();
      if (data.ok && data.html) {
        replaceWidget(widget, data.html); // re-rendered HTML already contains correct .is-selected
      } else {
        console.error("Rating failed:", data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      // If widget was replaced, this does nothing (safe).
      widget?.classList?.remove("is-busy");
    }
  });
})();
