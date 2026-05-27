/** Shared interactions for APEX HTML prototypes */
document.addEventListener("DOMContentLoaded", () => {
  const palette = document.getElementById("cmd-palette");
  const openBtn = document.querySelector("[data-cmd-open]");
  const closeOnBg = palette?.querySelector("[data-cmd-close]");

  function togglePalette(open) {
    if (!palette) return;
    palette.classList.toggle("open", open);
    if (open) palette.querySelector("input")?.focus();
  }

  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "k") {
      e.preventDefault();
      togglePalette(true);
    }
    if (e.key === "Escape") togglePalette(false);
  });

  openBtn?.addEventListener("click", () => togglePalette(true));
  closeOnBg?.addEventListener("click", (e) => {
    if (e.target === closeOnBg) togglePalette(false);
  });

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      const group = tab.closest(".card");
      group?.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
    });
  });
});
