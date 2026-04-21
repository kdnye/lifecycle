(() => {
  const root = document.documentElement;
  const key = "fsi_theme";
  const savedTheme = localStorage.getItem(key);

  if (savedTheme === "light" || savedTheme === "dark") {
    root.setAttribute("data-theme", savedTheme);
  }
})();
