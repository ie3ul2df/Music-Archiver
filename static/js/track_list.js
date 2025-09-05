// --------------------------- static/js/track_list.js ---------------------------//
// Toggle all tracks in an album
document.addEventListener("change", (e) => {
  if (e.target.classList.contains("check-all")) {
    const album = e.target.closest(".album");
    album.querySelectorAll(".track-check").forEach((cb) => (cb.checked = e.target.checked));
  }
});

// Simple drag-and-drop sorting
function makeSortable(container, itemSelector) {
  let dragItem = null;

  container.addEventListener("dragstart", (e) => {
    if (e.target.matches(itemSelector)) {
      dragItem = e.target;
      e.dataTransfer.effectAllowed = "move";
    }
  });

  container.addEventListener("dragover", (e) => {
    e.preventDefault();
    if (!dragItem) return;
    const items = Array.from(container.querySelectorAll(itemSelector));
    const after = items.find((el) => {
      const rect = el.getBoundingClientRect();
      return e.clientY <= rect.top + rect.height / 2 && el !== dragItem;
    });
    if (!after) {
      container.appendChild(dragItem);
    } else {
      container.insertBefore(dragItem, after);
    }
  });

  container.addEventListener("dragend", () => {
    if (dragItem) {
      saveOrder(container);
      dragItem = null;
    }
  });
}

function saveOrder(container) {
  const albumsWrapper = document.getElementById("albums");

  // ---- Case 1: Reorder albums themselves ----
  if (container === albumsWrapper) {
    const ids = Array.from(container.querySelectorAll(".album")).map((el) => parseInt(el.dataset.id, 10));
    const url = container.dataset.reorderUrl;
    if (url) {
      fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({ order: ids }),
      }).catch(console.error);
    }
    return;
  }

  // ---- Case 2: Reorder tracks inside an album / favorites / recent ----
  const albumCard = container.closest(".album");
  const ids = Array.from(container.querySelectorAll("li[data-atid], li[data-id]"))
    .map((li) => parseInt(li.dataset.atid || li.dataset.id, 10))
    .filter((n) => !Number.isNaN(n));

  if (!albumCard) {
    // global fallback (rarely used)
    fetch("/tracks/api/tracks/reorder/", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": getCookie("csrftoken") },
      body: JSON.stringify({ order: ids }),
    }).catch(console.error);
    return;
  }

  const scope = (albumCard.dataset.id || "").toString();
  const explicitUrl = container.dataset.reorderUrl || albumCard.dataset.reorderUrl || null;

  // Numeric album -> track reordering
  if (/^\d+$/.test(scope)) {
    const url = explicitUrl || `/albums/${scope}/tracks/reorder/`;
    fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": getCookie("csrftoken") },
      body: JSON.stringify({ order: ids }),
    }).catch(console.error);
    return;
  }

  // Named scopes: favorites / recent
  let url = explicitUrl;
  if (!url) {
    if (scope === "favorites") url = "/tracks/api/favorites/reorder/";
    else if (scope === "recent") url = "/tracks/api/recent/reorder/";
  }
  if (url) {
    fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": getCookie("csrftoken") },
      body: JSON.stringify({ order: ids }),
    }).catch(console.error);
  } else {
    console.warn("No reorder endpoint for scope:", scope);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const albumsContainer = document.getElementById("albums");
  if (albumsContainer) {
    makeSortable(albumsContainer, ".album");
  }
  document.querySelectorAll(".album").forEach((album) => {
    const list = album.querySelector(".tracks");
    if (list) {
      makeSortable(list, "li");
    }
  });
});

document.addEventListener("dragend", () => {
  // nothing here; music_player.js listens and rebuilds queue
});
