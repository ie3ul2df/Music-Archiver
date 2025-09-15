// static/js/cloud.js
(function () {
  const notify = (message, level) => {
    if (typeof window.showMessage === "function") {
      return window.showMessage(message, level);
    }
    if (typeof window.alert === "function") {
      window.alert(message);
    }
    return false;
  };

  // ---- CSRF helper ----
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      for (let c of document.cookie.split(";")) {
        c = c.trim();
        if (c.startsWith(name + "=")) {
          cookieValue = decodeURIComponent(c.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }
  const csrftoken = getCookie("csrftoken");

  // ---- Link folder form ----
  const linkForm = document.getElementById("cloud-link-form");
  if (linkForm) {
    linkForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const fd = new FormData(linkForm);
      const albumId = fd.get("album_id");
      const accountId = fd.get("account_id");
      const folderUrl = fd.get("folder_url");

      if (!albumId || !accountId || !folderUrl) {
        notify("⚠ Please select album, account, and paste a folder URL.", "warning");
        return;
      }

      // Build URL from template (e.g. /cloud/link_album_folder/999999/)
      const tpl = linkForm.getAttribute("data-url-template");
      const url = tpl.replace("999999", albumId);

      try {
        const r = await fetch(url, {
          method: "POST",
          headers: { "X-CSRFToken": csrftoken },
          body: fd,
        });

        // Try to parse JSON; if not JSON, fall back to text so we can show a helpful message
        let data;
        const ct = r.headers.get("content-type") || "";
        if (ct.includes("application/json")) {
          data = await r.json();
        } else {
          const txt = await r.text();
          throw new Error(`Server returned non-JSON (${r.status}) — ${txt.slice(0, 200)}`);
        }

        if (!r.ok || !data.ok) {
          throw new Error(data.error || `Failed to link (HTTP ${r.status})`);
        }

        notify("✅ Folder linked successfully! Use Sync to import files.", "success");
        window.location.reload();
      } catch (err) {
        console.error("Link folder failed:", err);
        notify("❌ " + err.message, "danger");
      }
    });
  }

  // ---- Sync album button ----
  window.syncAlbumFromCloud = async function (btn) {
    const url = btn.getAttribute("data-sync-url");
    if (!url) return;

    btn.disabled = true;
    const original = btn.textContent;
    btn.textContent = "Syncing…";

    try {
      const r = await fetch(url, {
        method: "POST",
        headers: { "X-CSRFToken": csrftoken },
      });

      let data;
      const ct = r.headers.get("content-type") || "";
      if (ct.includes("application/json")) {
        data = await r.json();
      } else {
        const txt = await r.text();
        throw new Error(`Server returned non-JSON (${r.status}) — ${txt.slice(0, 200)}`);
      }

      if (!r.ok || !data.ok) {
        throw new Error(data.error || `Sync failed (HTTP ${r.status})`);
      }

      btn.textContent = `Synced ✓ (${data.imported} new, ${data.updated} updated)`;
    } catch (err) {
      console.error("Sync failed:", err);
      notify("❌ " + err.message, "danger");
      btn.textContent = original;
    } finally {
      btn.disabled = false;
    }
  };
})();
