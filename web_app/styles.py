"""Общие стили Gradio-интерфейса.

Стили вынесены из ``app.py``, чтобы разметка и оформление не смешивались.
Отдельное внимание уделено тёмной теме: пользовательские карточки с
фиксированным светлым фоном всегда получают явный тёмный цвет текста.
"""

from __future__ import annotations

APP_CSS = """
/* Нативные элементы (выпадающие списки, календарь, полосы прокрутки)
   должны следовать выбранной теме. Без этого в тёмной теме браузер
   рисовал светлый список с унаследованным светлым текстом. */
body {
    color-scheme: light;
}
body.dark {
    color-scheme: dark;
}

/* Библиотека прокручивается внутри своего окна, а не растягивает страницу. */
.library-scroll {
    max-height: 62vh !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    padding-right: 8px !important;
    border: 1px solid var(--border-color-primary, #dbe3ee) !important;
    border-radius: 10px !important;
    background: var(--background-fill-secondary, #f8fafc) !important;
    scrollbar-gutter: stable;
}

.library-scroll .block {
    border: none !important;
    box-shadow: none !important;
}

/* Светлые карточки внутри тёмной темы не должны наследовать белый текст.
   Gradio красит все элементы внутри .prose через `color: var(--body-text-color)`,
   поэтому явные цвета нужны не только карточке, но и каждому потомку. */
.soundseek-light-card {
    background: #f8fafc !important;
    color: #1a2b47 !important;
}

.soundseek-light-card * {
    color: #1a2b47 !important;
}

/* Приглушённый текст внутри светлых карточек: класс специфичнее, чем `*`. */
.soundseek-light-card .soundseek-muted {
    color: #4d5b70 !important;
}

.soundseek-light-card .soundseek-faint {
    color: #5f6f87 !important;
}

/* Предупреждение о пустом результате тоже имеет фиксированный светлый фон. */
.soundseek-warning-card {
    background: #fff8e8 !important;
    color: #5b4300 !important;
}

.soundseek-warning-card * {
    color: #5b4300 !important;
}

/* Приглушённый текст в результатах поиска. Цвет берётся из темы,
   поэтому разбор запроса читается и на светлом, и на тёмном фоне. */
.soundseek-summary {
    color: var(--body-text-color, #40506a) !important;
    opacity: 0.78;
}

/* ---------- Карта аудиотеки ---------- */

.soundseek-map-card {
    position: relative;
    background: linear-gradient(180deg, #fbfdff 0%, #f8fafc 100%) !important;
    border: 1px solid #dbe3ee !important;
    border-radius: 16px !important;
    padding: 16px !important;
    color: #1a2b47 !important;
    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
}

.soundseek-map-card * {
    color: #1a2b47 !important;
}

.soundseek-map-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
}

.soundseek-map-kicker {
    color: #64748b !important;
    font-size: 11px;
    font-weight: 650;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}

.soundseek-map-title {
    margin-top: 3px;
    font-size: 19px;
    font-weight: 700;
    line-height: 1.2;
}

.soundseek-map-subtitle {
    margin-top: 5px;
    color: #5f6f87 !important;
    font-size: 12px;
}

.soundseek-map-count {
    flex: 0 0 auto;
    padding: 5px 10px;
    border-radius: 999px;
    background: #eef2f7 !important;
    color: #40506a !important;
    font-size: 12px;
    font-variant-numeric: tabular-nums;
}

.soundseek-map-canvas {
    margin-top: 13px;
    overflow: hidden;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    background: #f8fafc;
}

.soundseek-map-svg {
    display: block;
    width: 100%;
    height: auto;
}

.soundseek-map-point {
    cursor: pointer;
    outline: none;
}

.soundseek-map-grid {
    pointer-events: none;
}

.soundseek-map-hit {
    fill: transparent;
    pointer-events: all;
}

.soundseek-map-halo {
    fill: none;
    stroke: #0f172a;
    stroke-width: 2.5;
    opacity: 0;
    transition: opacity 140ms ease;
    pointer-events: none;
}

.soundseek-map-dot {
    stroke: #ffffff;
    stroke-width: 1.5;
    transition: r 140ms ease, stroke-width 140ms ease, filter 140ms ease;
    pointer-events: none;
}

.soundseek-map-point:hover .soundseek-map-dot,
.soundseek-map-point:focus-visible .soundseek-map-dot {
    r: 9;
    stroke-width: 2.4;
    filter: drop-shadow(0 2px 4px rgba(15, 23, 42, 0.28));
}

.soundseek-map-point:hover .soundseek-map-halo,
.soundseek-map-point:focus-visible .soundseek-map-halo {
    opacity: 0.18;
}

.soundseek-map-point.selected .soundseek-map-halo {
    opacity: 1;
}

.soundseek-map-point.selected .soundseek-map-dot {
    r: 8.5;
    stroke: #0f172a;
    stroke-width: 3;
}

.soundseek-map-tooltip {
    position: absolute;
    z-index: 30;
    max-width: 280px;
    padding: 9px 12px;
    border-radius: 10px;
    background: #0f172a !important;
    box-shadow: 0 10px 28px rgba(15, 23, 42, 0.28);
    opacity: 0;
    visibility: hidden;
    pointer-events: none;
    transform: translate(-50%, -100%);
    transition: opacity 110ms ease, visibility 110ms ease;
}

.soundseek-map-tooltip.below {
    transform: translate(-50%, 0);
}

.soundseek-map-tooltip.visible {
    opacity: 1;
    visibility: visible;
}

.soundseek-map-card .soundseek-map-tooltip,
.soundseek-map-card .soundseek-map-tooltip * {
    color: #f8fafc !important;
}

.soundseek-map-tooltip-title {
    overflow: hidden;
    font-size: 13px;
    font-weight: 650;
    line-height: 1.25;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.soundseek-map-tooltip-artist {
    margin-top: 2px;
    overflow: hidden;
    color: #cbd5e1 !important;
    font-size: 11px;
    line-height: 1.2;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.soundseek-map-legend-block {
    margin-top: 13px;
    padding-top: 11px;
    border-top: 1px solid #e2e8f0;
}

.soundseek-map-legend-title {
    margin-bottom: 8px;
    color: #64748b !important;
    font-size: 11px;
    font-weight: 650;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.soundseek-map-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 7px 9px;
}

.soundseek-map-legend-item {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    max-width: 100%;
    padding: 4px 9px;
    border-radius: 999px;
    background: #eef2f7 !important;
    color: #334155 !important;
    font-size: 12px;
    line-height: 1.25;
}

.soundseek-map-swatch {
    flex: 0 0 auto;
    width: 9px;
    height: 9px;
    border-radius: 50%;
    box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.12);
}

.soundseek-map-legend-count {
    color: #64748b !important;
    font-variant-numeric: tabular-nums;
}

.soundseek-map-empty {
    padding: 22px !important;
    text-align: center;
}

/* Плеер закреплён в правом верхнем углу и виден только на вкладке карты:
   неактивные вкладки Gradio скрывает вместе с содержимым. */
#soundseek-map-player {
    position: fixed !important;
    top: 76px !important;
    right: 18px !important;
    z-index: 1000 !important;
    width: min(360px, calc(100vw - 36px)) !important;
    padding: 12px !important;
    border: 1px solid #dbe3ee !important;
    border-radius: 16px !important;
    background: #f8fafc !important;
    color: #1a2b47 !important;
    box-shadow: 0 18px 45px rgba(15, 23, 42, 0.18) !important;
}

#soundseek-map-player * {
    color: #1a2b47 !important;
}

#soundseek-map-player .soundseek-map-player-title {
    margin: 0 0 4px !important;
    font-size: 15px !important;
    line-height: 1.2 !important;
}

#soundseek-map-player .soundseek-map-player-hint,
#soundseek-map-player .soundseek-map-player-meta {
    color: #5f6f87 !important;
    font-size: 12px !important;
    line-height: 1.35 !important;
}

#soundseek-map-player .soundseek-map-player-track {
    color: #1a2b47 !important;
    font-size: 13px !important;
    font-weight: 650 !important;
    line-height: 1.3 !important;
}

#soundseek-map-player .soundseek-map-player-artist {
    margin-top: 2px;
    color: #5f6f87 !important;
    font-size: 11px !important;
    line-height: 1.3 !important;
}

#soundseek-map-player .block {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
}

#soundseek-map-player audio {
    width: 100%;
}

/* На широком экране оставляем место справа, чтобы закреплённый плеер
   не закрывал фильтр и правый край карты. */
@media (min-width: 1100px) {
    #soundseek-map-content {
        padding-right: 390px !important;
    }
}

@media (max-width: 720px) {
    #soundseek-map-player {
        top: 68px !important;
        right: 10px !important;
        width: calc(100vw - 20px) !important;
    }
}
"""
