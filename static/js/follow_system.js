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

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return decodeURIComponent(parts.pop().split(";").shift());
  }
  const csrftoken = getCookie("csrftoken");

  async function post(url) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "X-CSRFToken": csrftoken },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  document.addEventListener("click", async (e) => {
    const btn = e.target.closest("[data-follow-toggle]");
    if (!btn) return;

    const url = btn.getAttribute("data-follow-toggle");
    const countEl = document.querySelector(btn.getAttribute("data-followers-target"));

    btn.disabled = true;
    try {
      const data = await post(url);
      if (data.ok) {
        btn.textContent = data.is_following ? "Unfollow" : "Follow";
        if (countEl && typeof data.followers === "number") {
          countEl.textContent = data.followers;
        }
      } else {
        notify(data.error || "Action failed.", "danger");
      }
    } catch (err) {
      console.error(err);
      notify("Network error.", "danger");
    } finally {
      btn.disabled = false;
    }
  });
})();
