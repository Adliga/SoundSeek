"""JavaScript для интерактивной карты аудиотеки.

Gradio-компонент ``gr.HTML`` не исполняет ``<script>`` из разметки, поэтому
обработчики вынесены в ``js_on_load``. Клик по точке отправляет событие
``track_click`` в Python, где обновляется аудиоплеер.
"""

from __future__ import annotations

MAP_JS = r"""
(() => {
  const root = element;
  const POINT_SELECTOR = ".soundseek-map-point";
  let selectedId = "";

  function mapCard() {
    return root.querySelector(".soundseek-map-card") || root;
  }

  function applySelection() {
    root.querySelectorAll(POINT_SELECTOR).forEach((point) => {
      point.classList.toggle(
        "selected",
        Boolean(selectedId) && point.dataset.trackId === selectedId
      );
    });
  }

  function ensureTooltip() {
    const host = mapCard();
    if (!host) return null;
    let node = host.querySelector(".soundseek-map-tooltip");
    if (!node) {
      node = document.createElement("div");
      node.className = "soundseek-map-tooltip";
      node.innerHTML =
        '<div class="soundseek-map-tooltip-title"></div>' +
        '<div class="soundseek-map-tooltip-artist"></div>' +
        '<div class="soundseek-map-tooltip-action">▶ Включить в плеере</div>';
      host.appendChild(node);
    }
    return node;
  }

  function placeTooltip(point) {
    const node = ensureTooltip();
    const host = mapCard();
    if (!node || !host) return;

    const title = node.querySelector(".soundseek-map-tooltip-title");
    const artist = node.querySelector(".soundseek-map-tooltip-artist");
    if (title) title.textContent = point.dataset.title || "Без названия";
    if (artist) artist.textContent = point.dataset.artist || "";

    node.classList.add("visible");

    const pointRect = point.getBoundingClientRect();
    const hostRect = host.getBoundingClientRect();
    const nodeWidth = node.offsetWidth || 190;
    const nodeHeight = node.offsetHeight || 54;
    const centerX =
      pointRect.left - hostRect.left + pointRect.width / 2;
    const half = nodeWidth / 2;
    const left = Math.min(
      Math.max(centerX, half + 8),
      hostRect.width - half - 8
    );

    let top = pointRect.top - hostRect.top - 12;
    let below = false;
    if (top - nodeHeight < 0) {
      top = pointRect.bottom - hostRect.top + 12;
      below = true;
    }

    node.style.left = `${left}px`;
    node.style.top = `${top}px`;
    node.classList.toggle("below", below);
  }

  function hideTooltip() {
    const node = mapCard().querySelector(".soundseek-map-tooltip");
    if (node) node.classList.remove("visible");
  }

  function selectPoint(point) {
    selectedId = point.dataset.trackId || "";
    applySelection();
    trigger("track_click", { track_id: selectedId });
  }

  root.addEventListener("click", (event) => {
    const point = event.target.closest(POINT_SELECTOR);
    if (!point || !root.contains(point)) return;
    event.preventDefault();
    selectPoint(point);
  });

  root.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const point = event.target.closest(POINT_SELECTOR);
    if (!point || !root.contains(point)) return;
    event.preventDefault();
    selectPoint(point);
  });

  root.addEventListener("pointerover", (event) => {
    const point = event.target.closest(POINT_SELECTOR);
    if (!point || !root.contains(point)) return;
    placeTooltip(point);
  });

  root.addEventListener("pointermove", (event) => {
    const point = event.target.closest(POINT_SELECTOR);
    if (!point || !root.contains(point)) return;
    placeTooltip(point);
  });

  root.addEventListener("pointerout", (event) => {
    const point = event.target.closest(POINT_SELECTOR);
    if (!point || !root.contains(point)) return;
    if (event.relatedTarget && point.contains(event.relatedTarget)) return;
    hideTooltip();
  });

  root.addEventListener("focusin", (event) => {
    const point = event.target.closest(POINT_SELECTOR);
    if (point) placeTooltip(point);
  });

  root.addEventListener("focusout", (event) => {
    const point = event.target.closest(POINT_SELECTOR);
    if (point) hideTooltip();
  });

  if (typeof watch === "function") {
    watch("value", () => {
      window.setTimeout(() => {
        applySelection();
        hideTooltip();
      }, 0);
    });
  }

  applySelection();
})();
"""
