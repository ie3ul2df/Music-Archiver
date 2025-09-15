(function () {
  "use strict";

  function ensureContainer() {
    let container = document.getElementById("messages-container");
    if (container) {
      return container;
    }

    container = document.createElement("div");
    container.id = "messages-container";
    container.className = "messages-container";

    const main = document.querySelector("main.container, main");
    if (main) {
      main.prepend(container);
    } else if (document.body) {
      document.body.prepend(container);
    }
    return container;
  }

  function normalizeLevel(level) {
    const val = String(level || "info").toLowerCase();
    switch (val) {
      case "error":
        return "danger";
      case "success":
      case "danger":
      case "warning":
      case "info":
      case "primary":
      case "secondary":
      case "light":
      case "dark":
        return val;
      default:
        return "info";
    }
  }

  function scheduleDismiss(alertEl, delay) {
    if (!delay || delay <= 0) {
      return;
    }
    window.setTimeout(() => {
      if (typeof bootstrap !== "undefined" && bootstrap.Alert) {
        bootstrap.Alert.getOrCreateInstance(alertEl).close();
      } else {
        alertEl.classList.remove("show");
        alertEl.addEventListener(
          "transitionend",
          () => {
            alertEl.remove();
          },
          { once: true }
        );
      }
    }, delay);
  }

  function showMessage(message, level = "info", options = {}) {
    const text = typeof message === "string" ? message : String(message || "");
    if (!text.trim()) {
      return false;
    }

    const container = ensureContainer();
    if (!container) {
      if (typeof window.alert === "function") {
        window.alert(text);
      }
      return false;
    }

    const alertLevel = normalizeLevel(level);

    const alertEl = document.createElement("div");
    alertEl.className = `alert alert-${alertLevel} alert-dismissible fade show`;
    alertEl.setAttribute("role", "alert");

    const span = document.createElement("span");
    span.textContent = text;
    alertEl.appendChild(span);

    const closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.className = "btn-close";
    closeBtn.setAttribute("data-bs-dismiss", "alert");
    closeBtn.setAttribute("aria-label", "Close");
    alertEl.appendChild(closeBtn);

    container.appendChild(alertEl);

    if (options && typeof options === "object" && options.dismissAfter) {
      scheduleDismiss(alertEl, Number(options.dismissAfter));
    }

    return false;
  }

  function clearMessages() {
    const container = document.getElementById("messages-container");
    if (container) {
      container.innerHTML = "";
    }
  }

  window.appMessages = {
    show: showMessage,
    clear: clearMessages,
  };

  window.showMessage = showMessage;
})();
