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
}

document.addEventListener("DOMContentLoaded", () => {
  makeSortable(document.getElementById("albums"), ".album");
  document.querySelectorAll(".tracks").forEach((ul) => makeSortable(ul, "li"));
});

document.addEventListener("dragend", () => {
  // nothing here; music_player.js listens and rebuilds queue
});
