// --------------------------- static/js/track_list.js ---------------------------//

(function () {
  "use strict";

  // ---------------- CSRF (fallback if cookies.js wasn't loaded) ----------------
  function getCookieLocal(name) {
    const m = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return m ? m.pop() : "";
  }
  // Prefer global getCookie if provided by cookies.js, else fallback:
  const getCSRF = (typeof getCookie === "function" ? getCookie : getCookieLocal).bind(null, "csrftoken");

  async function postJSON(url, payload) {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "X-CSRFToken": getCSRF(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
      credentials: "same-origin",
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`POST ${url} → ${res.status} ${res.statusText} ${text.slice(0, 200)}`);
    }
    return res.json().catch(() => ({}));
  }

  // ------------------------------ DRAG HELPERS --------------------------------
  function ensureDraggable(el) {
    if (!el.hasAttribute("draggable")) el.setAttribute("draggable", "true");
  }

  function getAfterElement(container, y, selector) {
    const list = [...container.querySelectorAll(`${selector}:not(.is-dragging)`)];

    return list.reduce(
      (closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - (box.top + box.height / 2);
        // If offset is negative, cursor is above the midline -> this element is after the dragged item
        if (offset < 0 && offset > closest.offset) {
          return { offset, element: child };
        }
        return closest;
      },
      { offset: Number.NEGATIVE_INFINITY, element: null }
    ).element;
  }

  function makeSortable(container, itemSelector, onCommit) {
    // Make sure all children are draggable
    container.querySelectorAll(itemSelector).forEach(ensureDraggable);

    let dragging = null;

    container.addEventListener("dragstart", (e) => {
      const item = e.target.closest(itemSelector);
      if (!item) return;
      dragging = item;
      item.classList.add("is-dragging");
      e.dataTransfer.effectAllowed = "move";
      // Some browsers require data to be set
      try {
        e.dataTransfer.setData("text/plain", "");
      } catch (_) {}
    });

    container.addEventListener("dragover", (e) => {
      if (!dragging) return;
      e.preventDefault(); // allow drop
      const after = getAfterElement(container, e.clientY, itemSelector);
      if (after == null) {
        container.appendChild(dragging);
      } else {
        container.insertBefore(dragging, after);
      }
    });

    container.addEventListener("drop", (e) => {
      // prevent navigating on link drops
      e.preventDefault();
    });

    container.addEventListener("dragend", async () => {
      if (!dragging) return;
      dragging.classList.remove("is-dragging");
      const toSave = dragging; // keep ref for scope resolution
      dragging = null;
      if (typeof onCommit === "function") {
        try {
          await onCommit(container, toSave);
        } catch (err) {
          console.error(err);
        }
      }
    });
  }

  // ------------------------------ SAVE ORDERS ---------------------------------
  async function saveAlbumsOrder(albumsWrapper) {
    const url = albumsWrapper.dataset.reorderUrl;
    if (!url) {
      console.warn("Missing albums reorder URL on #albums");
      return;
    }
    const ids = [...albumsWrapper.querySelectorAll(".album")].map((a) => parseInt(a.dataset.id, 10)).filter(Number.isFinite);
    if (!ids.length) return;
    await postJSON(url, { order: ids });
  }

  async function saveTracksOrder(listUL) {
    // Find the album card hosting this <ul class="tracks">
    const albumCard = listUL.closest(".album");
    if (!albumCard) {
      console.warn("Track list has no .album ancestor");
      return;
    }
    const url = albumCard.dataset.reorderUrl; // should be album:album_reorder_tracks
    if (!url) {
      console.warn("Missing album track reorder URL on .album card");
      return;
    }

    // IMPORTANT: use AlbumTrack IDs for ordering!
    const atIds = [...listUL.querySelectorAll("li.track-item")].map((li) => parseInt(li.dataset.atid, 10)).filter(Number.isFinite);

    if (!atIds.length) return;
    await postJSON(url, { order: atIds });
  }

  // ----------------------------- INIT SORTABLES -------------------------------
  document.addEventListener("DOMContentLoaded", () => {
    // Albums wrapper
    const albumsWrapper = document.getElementById("albums");
    if (albumsWrapper) {
      // Ensure each album card is draggable
      albumsWrapper.querySelectorAll(".album").forEach(ensureDraggable);

      makeSortable(albumsWrapper, ".album", saveAlbumsOrder);

      // Each album's track list
      albumsWrapper.querySelectorAll(".album ul.tracks").forEach((ul) => {
        // Ensure each track item is draggable
        ul.querySelectorAll("li.track-item").forEach(ensureDraggable);
        makeSortable(ul, "li.track-item", saveTracksOrder);
      });
    }

    // Global Check/Uncheck All
    const globalBtn = document.getElementById("check-all-global");
    if (globalBtn) {
      globalBtn.addEventListener("click", () => {
        const checks = document.querySelectorAll(".track-check");
        const allChecked = [...checks].every((cb) => cb.checked);
        checks.forEach((cb) => (cb.checked = !allChecked));
        globalBtn.textContent = allChecked ? "✔ All" : "✖ None";
      });
    }
  });

  // ----------------------- Album-level "Check All" toggle ---------------------
  document.addEventListener("change", (e) => {
    if (!e.target.classList.contains("check-all")) return;
    const album = e.target.closest(".album");
    if (!album) return;
    album.querySelectorAll(".track-check").forEach((cb) => (cb.checked = e.target.checked));
  });

  // No-op, music_player.js may hook into dragend if needed
  document.addEventListener("dragend", () => {});
})();

//--------------------------- Drag tracks in favourite list ---------------------------//
(function () {
  "use strict";

  function getCookie(name) {
    const m = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return m ? m.pop() : "";
  }
  const csrftoken = getCookie("csrftoken");

  const list = document.getElementById("fav-tracks");
  if (!list) return;

  let draggingLi = null;

  list.addEventListener("dragstart", (e) => {
    // Only proceed if target is an element
    if (!(e.target instanceof Element)) return;

    const li = e.target.closest("li.track-item");
    if (!li) return;

    draggingLi = li;
    li.classList.add("dragging");

    if (e.dataTransfer) {
      e.dataTransfer.effectAllowed = "move";
      try {
        e.dataTransfer.setData("text/plain", li.dataset.id || "");
      } catch (_) {}
    }
  });

  list.addEventListener("dragend", () => {
    if (draggingLi) {
      draggingLi.classList.remove("dragging");
      draggingLi = null;
    }
  });

  list.addEventListener("dragover", (e) => {
    if (!draggingLi) return;
    e.preventDefault(); // allow drop
    const after = getAfterElement(list, e.clientY);
    if (after == null) {
      list.appendChild(draggingLi);
    } else {
      list.insertBefore(draggingLi, after);
    }
  });

  list.addEventListener("drop", async (e) => {
    if (!draggingLi) return;
    e.preventDefault();

    const order = Array.from(list.querySelectorAll("li.track-item"))
      .map((li) => parseInt(li.dataset.id, 10))
      .filter(Number.isFinite);

    const url = list.dataset.reorderUrl;
    if (!url || !order.length) return;

    try {
      await fetch(url, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrftoken,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ order }),
      });
    } catch (err) {
      console.error("Failed saving favourites order", err);
    }
  });

  function getAfterElement(container, y) {
    const els = [...container.querySelectorAll("li.track-item:not(.dragging)")];
    let closest = null;
    let closestOffset = Number.NEGATIVE_INFINITY;

    for (const el of els) {
      const box = el.getBoundingClientRect();
      const offset = y - (box.top + box.height / 2);
      if (offset < 0 && offset > closestOffset) {
        closestOffset = offset;
        closest = el;
      }
    }
    return closest;
  }
})();
