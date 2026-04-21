document.addEventListener("DOMContentLoaded", () => {
  const menuRoot = document.querySelector("[data-account-menu]");
  if (!menuRoot) {
    return;
  }

  const toggle = menuRoot.querySelector("[data-account-menu-toggle]");
  const menuList = menuRoot.querySelector("[data-account-menu-list]");

  if (!toggle || !menuList) {
    return;
  }

  const closeMenu = () => {
    menuList.hidden = true;
    toggle.setAttribute("aria-expanded", "false");
  };

  const openMenu = () => {
    menuList.hidden = false;
    toggle.setAttribute("aria-expanded", "true");
  };

  toggle.addEventListener("click", () => {
    if (menuList.hidden) {
      openMenu();
      return;
    }

    closeMenu();
  });

  document.addEventListener("click", (event) => {
    if (!menuRoot.contains(event.target)) {
      closeMenu();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeMenu();
      toggle.focus();
    }
  });
});
