(() => {
  const grid = document.querySelector("[data-municipios-acordeon]");
  const expandAllButton = document.getElementById("alternar-todos-municipios");

  if (!grid || !expandAllButton) return;

  const cards = Array.from(grid.querySelectorAll(".municipio-acordeon"));
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function updateExpandAllButton() {
    const allExpanded = cards.length > 0 && cards.every((card) => {
      const toggle = card.querySelector(".municipio-acordeon__toggle");
      return toggle && toggle.getAttribute("aria-expanded") === "true";
    });

    expandAllButton.textContent = allExpanded ? "Contraer todos" : "Expandir todos";
    expandAllButton.setAttribute("aria-expanded", String(allExpanded));
  }

  function setExpanded(card, expanded) {
    const toggle = card.querySelector(".municipio-acordeon__toggle");
    const panel = toggle && document.getElementById(toggle.getAttribute("aria-controls"));

    if (!toggle || !panel || (toggle.getAttribute("aria-expanded") === "true") === expanded) {
      return;
    }

    toggle.setAttribute("aria-expanded", String(expanded));

    if (reducedMotion) {
      panel.hidden = !expanded;
      panel.inert = !expanded;
      panel.style.height = expanded ? "auto" : "";
      return;
    }

    if (expanded) {
      panel.hidden = false;
      panel.inert = false;
      panel.style.height = "0px";
      requestAnimationFrame(() => {
        if (toggle.getAttribute("aria-expanded") === "true") {
          panel.style.height = `${panel.scrollHeight}px`;
        }
      });
    } else {
      panel.style.height = `${panel.getBoundingClientRect().height}px`;
      panel.inert = true;
      panel.offsetHeight;
      panel.style.height = "0px";
    }

    const onTransitionEnd = (event) => {
      if (event.target !== panel || event.propertyName !== "height") return;
      panel.removeEventListener("transitionend", onTransitionEnd);

      if ((toggle.getAttribute("aria-expanded") === "true") !== expanded) return;

      if (expanded) {
        panel.style.height = "auto";
      } else {
        panel.hidden = true;
        panel.style.height = "";
      }
    };

    panel.addEventListener("transitionend", onTransitionEnd);
  }

  grid.addEventListener("click", (event) => {
    const toggle = event.target.closest(".municipio-acordeon__toggle");
    if (!toggle || !grid.contains(toggle)) return;

    const card = toggle.closest(".municipio-acordeon");
    setExpanded(card, toggle.getAttribute("aria-expanded") !== "true");
    updateExpandAllButton();
  });

  expandAllButton.addEventListener("click", () => {
    const shouldExpand = expandAllButton.getAttribute("aria-expanded") !== "true";
    cards.forEach((card) => setExpanded(card, shouldExpand));
    updateExpandAllButton();
  });

  updateExpandAllButton();
})();
