"""JavaScript для HTML-таблицы библиотеки.

Одна делегированная подписка на весь контейнер: клики по `[data-track-play]`
включают трек в глобальном плеере, клики по `[data-track-enrich]` ставят
распознавание в очередь, а клик по строке выбирает трек для формы
редактирования. Все события уходят в Python через ``trigger``.
"""

from __future__ import annotations

LIBRARY_JS = r"""
(() => {
  const root = element;
  if (!root || root.dataset.soundseekLibBound === "1") return;
  root.dataset.soundseekLibBound = "1";

  const SCROLL_KEY = "__soundseekLibraryScrollTop";
  const SCROLL_SELECTOR = ".soundseek-lib-scroll";

  const rememberScroll = () => {
    const scroller = root.querySelector(SCROLL_SELECTOR);
    if (scroller) window[SCROLL_KEY] = scroller.scrollTop;
  };

  const restoreScroll = () => {
    const scroller = root.querySelector(SCROLL_SELECTOR);
    if (!scroller) return;

    if (scroller.dataset.soundseekScrollBound !== "1") {
      scroller.dataset.soundseekScrollBound = "1";
      scroller.addEventListener(
        "scroll",
        () => {
          window[SCROLL_KEY] = scroller.scrollTop;
        },
        { passive: true }
      );
    }

    const savedTop = Number(window[SCROLL_KEY] || 0);
    if (savedTop <= 0) return;

    const apply = () => {
      if (scroller.isConnected) scroller.scrollTop = savedTop;
    };
    apply();
    window.requestAnimationFrame(() => window.requestAnimationFrame(apply));
  };

  restoreScroll();

  // Gradio перерисовывает HTML-таблицу при изменении статуса или выбора
  // трека. Возвращаем прокрутку после каждой такой перерисовки.
  const observer = new MutationObserver(restoreScroll);
  observer.observe(root, { childList: true, subtree: true });

  root.addEventListener("click", (event) => {
    rememberScroll();
    const playBtn = event.target.closest("[data-track-play]");
    if (playBtn && root.contains(playBtn)) {
      event.preventDefault();
      event.stopPropagation();
      const id = playBtn.dataset.trackPlay || "";
      if (id) trigger("track_play", { track_id: id });
      return;
    }

    const enrichBtn = event.target.closest("[data-track-enrich]");
    if (enrichBtn && root.contains(enrichBtn)) {
      event.preventDefault();
      event.stopPropagation();
      const id = enrichBtn.dataset.trackEnrich || "";
      if (!id) return;
      const force = enrichBtn.dataset.trackForce === "1";
      trigger("track_enrich", { track_id: id, force: force });
      return;
    }

    const row = event.target.closest("[data-track-id]");
    if (!row || !root.contains(row)) return;
    event.preventDefault();
    const id = row.dataset.trackId || "";
    if (!id) return;

    root.querySelectorAll(".soundseek-lib-row.is-selected").forEach((item) => {
      item.classList.remove("is-selected");
    });
    row.classList.add("is-selected");
    trigger("track_select", { track_id: id });

    window.setTimeout(() => {
      const panel = document.getElementById("soundseek-edit-panel");
      if (panel) {
        panel.scrollIntoView({ behavior: "smooth", block: "start" });
      }
      const accordion = document.getElementById("soundseek-edit-accordion");
      if (!accordion) return;
      const toggle = accordion.querySelector("button[aria-expanded]");
      if (toggle && toggle.getAttribute("aria-expanded") === "false") {
        toggle.click();
      }
    }, 160);
  });

  root.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const row = event.target.closest("[data-track-id]");
    if (!row || !root.contains(row) || event.target.closest("button")) return;
    event.preventDefault();
    row.click();
  });
})();
"""