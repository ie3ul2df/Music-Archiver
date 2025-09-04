// --- static\js\cookies.js ---
// --- CSRF helper ---
function getCookie(name) {
  const m = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
  return m ? m[2] : null;
}
const CSRF = getCookie("csrftoken");
