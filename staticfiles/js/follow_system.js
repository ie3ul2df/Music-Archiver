(function () {
  "use strict";

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
        alert(data.error || "Action failed.");
      }
    } catch (err) {
      console.error(err);
      alert("Network error.");
    } finally {
      btn.disabled = false;
    }
  });
})();
