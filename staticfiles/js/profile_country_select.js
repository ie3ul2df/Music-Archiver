document.addEventListener("DOMContentLoaded", function () {
  const el = document.getElementById("id_default_country");
  if (!el) return;
  const setColor = () => {
    el.style.color = el.value ? "black" : "#6c757d";
  };
  setColor();
  el.addEventListener("change", setColor);
});
