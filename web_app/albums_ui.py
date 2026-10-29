"""JavaScript для вкладки «Альбомы».

Клик по карточке отправляет в Python событие ``album_click`` с ключом
альбома. Обработчик возвращает HTML со списком треков.
"""

from __future__ import annotations

ALBUM_JS = r"""
(() => {
  const root = element;
  const CARD_SELECTOR = ".soundseek-album-card";
  let selectedKey = "";

  function applySelection() {
    root.querySelectorAll(CARD_SELECTOR).forEach((card) => {
      card.classList.toggle(
        "selected",
        Boolean(selectedKey) && card.dataset.albumKey === selectedKey
      );
    });
  }

  function selectCard(card) {
    selectedKey = card.dataset.albumKey || "";
    applySelection();
    trigger("album_click", { album_key: selectedKey });

    const detail = document.getElementById("soundseek-album-detail");
    if (detail) {
      window.setTimeout(() => {
        detail.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 60);
    }
  }

  root.addEventListener("click", (event) => {
    const card = event.target.closest(CARD_SELECTOR);
    if (!card || !root.contains(card)) return;
    event.preventDefault();
    selectCard(card);
  });

  root.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const card = event.target.closest(CARD_SELECTOR);
    if (!card || !root.contains(card)) return;
    event.preventDefault();
    selectCard(card);
  });

  if (typeof watch === "function") {
    watch("value", () => {
      window.setTimeout(applySelection, 0);
    });
  }

  applySelection();
})();
"""
