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

/* ---------- Глобальный плеер ---------- */

#soundseek-global-player {
    position: fixed !important;
    top: 76px !important;
    right: 18px !important;
    z-index: 1200 !important;
    flex-direction: column !important;
    gap: 10px !important;
    width: min(340px, calc(100vw - 36px)) !important;
    max-height: calc(100vh - 96px);
    overflow-y: auto;
    padding: 14px 42px 14px 14px !important;
    border: 1px solid #dbe3ee !important;
    border-radius: 16px !important;
    background: #f8fafc !important;
    color: #1a2b47 !important;
    box-shadow: 0 18px 45px rgba(15, 23, 42, 0.2) !important;
}

#soundseek-global-player * {
    color: #1a2b47 !important;
}

#soundseek-global-player .soundseek-global-title {
    margin: 0 0 2px !important;
    font-size: 15px !important;
    line-height: 1.2 !important;
}

#soundseek-global-player .soundseek-global-meta {
    margin: 0 0 2px !important;
}

#soundseek-global-player .soundseek-player-track {
    color: #1a2b47 !important;
    font-size: 14px !important;
    font-weight: 700 !important;
    line-height: 1.3 !important;
}

#soundseek-global-player .soundseek-player-artist {
    margin-top: 3px;
    color: #5f6f87 !important;
    font-size: 11px !important;
    line-height: 1.35 !important;
}

#soundseek-global-player .soundseek-player-error {
    color: #b42318 !important;
    font-size: 12px !important;
    line-height: 1.4 !important;
}

#soundseek-global-player .block {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
}

#soundseek-global-player audio {
    width: 100%;
}

#soundseek-global-close,
#soundseek-global-close button {
    position: absolute !important;
    top: 9px !important;
    right: 9px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 28px !important;
    height: 28px !important;
    min-width: 28px !important;
    padding: 0 !important;
    border: 1px solid #dbe3ee !important;
    border-radius: 50% !important;
    background: #ffffff !important;
    color: #40506a !important;
    font-size: 14px !important;
    line-height: 1 !important;
}

#soundseek-global-close:hover,
#soundseek-global-close button:hover {
    border-color: #f0a5a0 !important;
    background: #fff1f0 !important;
    color: #b42318 !important;
}

.soundseek-play-button {
    display: inline-flex;
    flex: 0 0 auto;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    min-width: 32px;
    margin: 0;
    padding: 0;
    border: 0;
    border-radius: 50%;
    background: #2563eb !important;
    color: #ffffff !important;
    font-size: 12px !important;
    line-height: 1;
    cursor: pointer;
    box-shadow: 0 2px 7px rgba(37, 99, 235, 0.28);
    transition: background 130ms ease, transform 130ms ease;
}

.soundseek-light-card .soundseek-play-button,
.soundseek-album-detail .soundseek-play-button {
    background: #2563eb !important;
    color: #ffffff !important;
}

.soundseek-light-card .soundseek-play-button *,
.soundseek-album-detail .soundseek-play-button * {
    color: #ffffff !important;
}

.soundseek-play-button:hover {
    background: #1d4ed8 !important;
    transform: translateY(-1px) scale(1.04);
}

.soundseek-play-button:focus-visible {
    outline: 3px solid rgba(37, 99, 235, 0.38);
    outline-offset: 2px;
}

.soundseek-album-track .soundseek-play-button {
    width: 26px;
    height: 26px;
    min-width: 26px;
    font-size: 10px !important;
}

.soundseek-row-play,
.soundseek-row-play button {
    width: 36px !important;
    height: 36px !important;
    min-width: 36px !important;
    padding: 0 !important;
    border-radius: 50% !important;
    font-size: 11px !important;
    line-height: 1 !important;
}

.soundseek-map-tooltip-action {
    margin-top: 4px;
    color: #93c5fd !important;
    font-size: 10px;
    font-weight: 650;
    letter-spacing: 0.04em;
    line-height: 1.2;
}

@media (max-width: 720px) {
    #soundseek-global-player {
        top: 68px !important;
        right: 10px !important;
        width: calc(100vw - 20px) !important;
        max-height: calc(100vh - 88px);
    }
}

/* Пока плеер открыт, освобождаем место справа на широком экране,
   чтобы он не закрывал элементы управления. */
@media (min-width: 1280px) {
    body:has(#soundseek-global-player) .gradio-container main.contain {
        box-sizing: border-box !important;
        padding-right: 360px !important;
    }
}

/* ---------- Альбомы ---------- */

.soundseek-albums-page {
    display: flex;
    flex-direction: column;
    gap: 28px;
}

.soundseek-albums-section {
    display: flex;
    flex-direction: column;
    gap: 14px;
}

.soundseek-albums-heading {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 16px;
}

.soundseek-albums-kicker {
    color: var(--body-text-color, #64748b) !important;
    opacity: 0.62;
    font-size: 11px;
    font-weight: 650;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}

.soundseek-albums-title {
    margin: 3px 0 0 !important;
    color: var(--body-text-color, #1a2b47) !important;
    font-size: 19px;
    font-weight: 700;
    line-height: 1.2;
}

.soundseek-albums-count {
    flex: 0 0 auto;
    padding: 5px 10px;
    border-radius: 999px;
    background: var(--background-fill-secondary, #eef2f7) !important;
    color: var(--body-text-color, #40506a) !important;
    font-size: 12px;
    font-variant-numeric: tabular-nums;
}

.soundseek-album-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(168px, 1fr));
    gap: 18px 16px;
}

.soundseek-album-card {
    display: flex;
    flex-direction: column;
    gap: 8px;
    width: 100%;
    margin: 0;
    padding: 0;
    border: 0;
    outline: none;
    background: transparent;
    color: var(--body-text-color, #1a2b47);
    font: inherit;
    text-align: left;
    cursor: pointer;
}

.soundseek-album-cover {
    position: relative;
    width: 100%;
    aspect-ratio: 1 / 1;
    overflow: hidden;
    border: 1px solid var(--border-color-primary, #dbe3ee);
    border-radius: 14px;
    background: #e2e8f0;
    box-shadow: 0 7px 18px rgba(15, 23, 42, 0.1);
    transition: transform 150ms ease, box-shadow 150ms ease;
}

.soundseek-album-cover img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.soundseek-album-card:hover .soundseek-album-cover {
    transform: translateY(-3px);
    box-shadow: 0 14px 28px rgba(15, 23, 42, 0.17);
}

.soundseek-album-card:focus-visible .soundseek-album-cover {
    outline: 3px solid #2563eb;
    outline-offset: 3px;
}

.soundseek-album-card.selected .soundseek-album-cover {
    outline: 3px solid #2563eb;
    outline-offset: 3px;
    box-shadow: 0 0 0 7px rgba(37, 99, 235, 0.18);
}

.soundseek-album-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 7px;
    width: 100%;
    height: 100%;
    padding: 12px;
    background:
        radial-gradient(circle at 28% 20%, rgba(255, 255, 255, 0.3), transparent 32%),
        linear-gradient(145deg, var(--album-accent, #2563eb), #0f172a);
    color: #ffffff !important;
    text-align: center;
}

.soundseek-album-placeholder-letter {
    font-size: 48px;
    font-weight: 750;
    letter-spacing: -0.05em;
    line-height: 1;
    color: #ffffff !important;
}

.soundseek-album-glyph {
    font-size: 42px;
    line-height: 1;
    color: #ffffff !important;
}

.soundseek-album-placeholder-label {
    max-width: 100%;
    padding: 0 10px;
    overflow: hidden;
    color: #e2e8f0 !important;
    font-size: 10px;
    font-weight: 650;
    letter-spacing: 0.1em;
    line-height: 1.25;
    text-overflow: ellipsis;
    text-transform: uppercase;
    white-space: nowrap;
}

.soundseek-album-caption {
    min-width: 0;
}

.soundseek-album-title {
    display: -webkit-box;
    overflow: hidden;
    color: var(--body-text-color, #1a2b47) !important;
    font-size: 13px;
    font-weight: 650;
    line-height: 1.3;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
}

.soundseek-album-meta {
    margin-top: 2px;
    overflow: hidden;
    color: var(--body-text-color, #5f6f87) !important;
    opacity: 0.66;
    font-size: 11px;
    line-height: 1.3;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.soundseek-albums-empty {
    padding: 16px;
    border: 1px dashed var(--border-color-primary, #cbd5e1);
    border-radius: 12px;
    color: var(--body-text-color, #5f6f87) !important;
    font-size: 13px;
    line-height: 1.45;
}

#soundseek-album-detail {
    scroll-margin-top: 86px;
}

.soundseek-album-detail {
    margin-bottom: 18px;
    padding: 16px;
    border: 1px solid #d0d7e2 !important;
    border-radius: 14px !important;
    background: #ffffff !important;
    color: #1a2b47 !important;
}

.soundseek-album-detail-head {
    display: flex;
    align-items: center;
    gap: 14px;
}

.soundseek-album-detail-cover {
    flex: 0 0 86px;
    width: 86px;
    height: 86px;
    overflow: hidden;
    border-radius: 12px;
    background: #e2e8f0;
    box-shadow: 0 5px 14px rgba(15, 23, 42, 0.13);
}

.soundseek-album-detail-cover img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.soundseek-album-detail-copy {
    min-width: 0;
}

.soundseek-album-detail-kicker {
    color: #64748b !important;
    font-size: 10px;
    font-weight: 650;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}

.soundseek-album-detail-title {
    margin-top: 2px;
    overflow-wrap: anywhere;
    color: #1a2b47 !important;
    font-size: 18px;
    font-weight: 700;
    line-height: 1.25;
}

.soundseek-album-detail-meta {
    margin-top: 3px;
    color: #5f6f87 !important;
    font-size: 12px;
    line-height: 1.35;
}

.soundseek-album-detail-empty {
    padding: 18px;
}

.soundseek-album-tracklist {
    max-height: min(48vh, 520px);
    margin: 14px 0 0;
    padding: 0;
    overflow-y: auto;
    border-top: 1px solid #e2e8f0;
    list-style: none;
}

.soundseek-album-track {
    display: grid;
    grid-template-columns: 34px 26px minmax(0, 1fr) auto;
    gap: 10px;
    align-items: center;
    padding: 8px 4px;
    border-bottom: 1px solid #eef2f7;
}

.soundseek-album-track:last-child {
    border-bottom: 0;
}

.soundseek-album-track-number {
    color: #94a3b8 !important;
    font-size: 11px;
    font-variant-numeric: tabular-nums;
}

.soundseek-album-track-copy {
    min-width: 0;
}

.soundseek-album-track-title {
    display: block;
    overflow: hidden;
    color: #1a2b47 !important;
    font-size: 13px;
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.soundseek-album-track-meta {
    display: block;
    overflow: hidden;
    color: #5f6f87 !important;
    font-size: 11px;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.soundseek-album-track-duration {
    color: #5f6f87 !important;
    font-size: 11px;
    font-variant-numeric: tabular-nums;
}

@media (max-width: 620px) {
    .soundseek-album-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 14px 12px;
    }

    .soundseek-album-detail-cover {
        flex-basis: 64px;
        width: 64px;
        height: 64px;
    }

    .soundseek-album-detail-title {
        font-size: 16px;
    }
}
"""
