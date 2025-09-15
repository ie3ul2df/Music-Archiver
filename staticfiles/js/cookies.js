// ---------------- static/js/cookies.js ----------------
// Utility to safely get a cookie by name (used for CSRF token, etc.)
function getCookie(name) {
  if (!document.cookie) return null;

  const cookies = document.cookie.split(";").map((c) => c.trim());
  for (const cookie of cookies) {
    if (cookie.startsWith(name + "=")) {
      return decodeURIComponent(cookie.slice(name.length + 1));
    }
  }
  return null;
}
