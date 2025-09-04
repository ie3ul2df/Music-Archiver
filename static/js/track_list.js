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
  const albumCard = container.closest(".album");

  // If we're inside an album card with a numeric ID, reorder album tracks.
  const albumId = albumCard ? parseInt(albumCard.dataset.id, 10) : NaN;
  if (!isNaN(albumId)) {
    const ids = Array.from(container.querySelectorAll("li[data-atid]")).map((li) => parseInt(li.dataset.atid, 10));

    console.log("Saving album order:", ids);

    fetch(`/albums/${albumId}/tracks/reorder/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({ order: ids }),
    })
      .then((r) => r.json())
      .then((data) => console.log("Server response:", data))
      .catch(console.error);
    return;
  }

  // Otherwise fall back to global track reordering
  const ids = Array.from(container.querySelectorAll("li[data-id]")).map((li) => parseInt(li.dataset.id, 10));

  console.log("Saving new order:", ids);

  fetch("/tracks/api/tracks/reorder/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken"),
    },
    body: JSON.stringify({ order: ids }),
  })
    .then((r) => r.json())
    .then((data) => {
      console.log("Server response:", data);
    })
    .catch(console.error);
}

document.addEventListener("DOMContentLoaded", () => {
  makeSortable(document.getElementById("albums"), ".album");
  document.querySelectorAll(".tracks").forEach((ul) => makeSortable(ul, "li"));
});

document.addEventListener("dragend", () => {
  // nothing here; music_player.js listens and rebuilds queue
});
