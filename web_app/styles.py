# """Общие стили Gradio-интерфейса.

# Стили вынесены из ``app.py``, чтобы разметка и оформление не смешивались.
# Отдельное внимание уделено тёмной теме: пользовательские карточки с
# фиксированным светлым фоном всегда получают явный тёмный цвет текста.
# """

# from __future__ import annotations

# APP_CSS = """
# /* Нативные элементы (выпадающие списки, календарь, полосы прокрутки)
#    должны следовать выбранной теме. Без этого в тёмной теме браузер
#    рисовал светлый список с унаследованным светлым текстом. */
# body {
#     color-scheme: light;
# }
# body.dark {
#     color-scheme: dark;
# }

# /* Библиотека прокручивается внутри своего окна, а не растягивает страницу. */
# .library-scroll {
#     max-height: 62vh !important;
#     overflow-y: auto !important;
#     overflow-x: hidden !important;
#     padding-right: 8px !important;
#     border: 1px solid var(--border-color-primary, #dbe3ee) !important;
#     border-radius: 10px !important;
#     background: var(--background-fill-secondary, #f8fafc) !important;
#     scrollbar-gutter: stable;
# }

# .library-scroll .block {
#     border: none !important;
#     box-shadow: none !important;
# }

# /* Светлые карточки внутри тёмной темы не должны наследовать белый текст.
#    Gradio красит все элементы внутри .prose через `color: var(--body-text-color)`,
#    поэтому явные цвета нужны не только карточке, но и каждому потомку. */
# .soundseek-light-card {
#     background: #f8fafc !important;
#     color: #1a2b47 !important;
# }

# .soundseek-light-card * {
#     color: #1a2b47 !important;
# }

# /* Приглушённый текст внутри светлых карточек: класс специфичнее, чем `*`. */
# .soundseek-light-card .soundseek-muted {
#     color: #4d5b70 !important;
# }

# .soundseek-light-card .soundseek-faint {
#     color: #5f6f87 !important;
# }

# /* Предупреждение о пустом результате тоже имеет фиксированный светлый фон. */
# .soundseek-warning-card {
#     background: #fff8e8 !important;
#     color: #5b4300 !important;
# }

# .soundseek-warning-card * {
#     color: #5b4300 !important;
# }

# /* Приглушённый текст в результатах поиска. Цвет берётся из темы,
#    поэтому разбор запроса читается и на светлом, и на тёмном фоне. */
# .soundseek-summary {
#     color: var(--body-text-color, #40506a) !important;
#     opacity: 0.78;
# }

# /* ---------- Карта аудиотеки ---------- */

# .soundseek-map-card {
#     position: relative;
#     background: linear-gradient(180deg, #fbfdff 0%, #f8fafc 100%) !important;
#     border: 1px solid #dbe3ee !important;
#     border-radius: 16px !important;
#     padding: 16px !important;
#     color: #1a2b47 !important;
#     box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
# }

# .soundseek-map-card * {
#     color: #1a2b47 !important;
# }

# .soundseek-map-head {
#     display: flex;
#     align-items: flex-start;
#     justify-content: space-between;
#     gap: 16px;
# }

# .soundseek-map-kicker {
#     color: #64748b !important;
#     font-size: 11px;
#     font-weight: 650;
#     letter-spacing: 0.12em;
#     text-transform: uppercase;
# }

# .soundseek-map-title {
#     margin-top: 3px;
#     font-size: 19px;
#     font-weight: 700;
#     line-height: 1.2;
# }

# .soundseek-map-subtitle {
#     margin-top: 5px;
#     color: #5f6f87 !important;
#     font-size: 12px;
# }

# .soundseek-map-count {
#     flex: 0 0 auto;
#     padding: 5px 10px;
#     border-radius: 999px;
#     background: #eef2f7 !important;
#     color: #40506a !important;
#     font-size: 12px;
#     font-variant-numeric: tabular-nums;
# }

# .soundseek-map-canvas {
#     margin-top: 13px;
#     overflow: hidden;
#     border: 1px solid #e2e8f0;
#     border-radius: 12px;
#     background: #f8fafc;
# }

# .soundseek-map-svg {
#     display: block;
#     width: 100%;
#     height: auto;
# }

# .soundseek-map-point {
#     cursor: pointer;
#     outline: none;
# }

# .soundseek-map-grid {
#     pointer-events: none;
# }

# .soundseek-map-hit {
#     fill: transparent;
#     pointer-events: all;
# }

# .soundseek-map-halo {
#     fill: none;
#     stroke: #0f172a;
#     stroke-width: 2.5;
#     opacity: 0;
#     transition: opacity 140ms ease;
#     pointer-events: none;
# }

# .soundseek-map-dot {
#     stroke: #ffffff;
#     stroke-width: 1.5;
#     transition: r 140ms ease, stroke-width 140ms ease, filter 140ms ease;
#     pointer-events: none;
# }

# .soundseek-map-point:hover .soundseek-map-dot,
# .soundseek-map-point:focus-visible .soundseek-map-dot {
#     r: 9;
#     stroke-width: 2.4;
#     filter: drop-shadow(0 2px 4px rgba(15, 23, 42, 0.28));
# }

# .soundseek-map-point:hover .soundseek-map-halo,
# .soundseek-map-point:focus-visible .soundseek-map-halo {
#     opacity: 0.18;
# }

# .soundseek-map-point.selected .soundseek-map-halo {
#     opacity: 1;
# }

# .soundseek-map-point.selected .soundseek-map-dot {
#     r: 8.5;
#     stroke: #0f172a;
#     stroke-width: 3;
# }

# .soundseek-map-tooltip {
#     position: absolute;
#     z-index: 30;
#     max-width: 280px;
#     padding: 9px 12px;
#     border-radius: 10px;
#     background: #0f172a !important;
#     box-shadow: 0 10px 28px rgba(15, 23, 42, 0.28);
#     opacity: 0;
#     visibility: hidden;
#     pointer-events: none;
#     transform: translate(-50%, -100%);
#     transition: opacity 110ms ease, visibility 110ms ease;
# }

# .soundseek-map-tooltip.below {
#     transform: translate(-50%, 0);
# }

# .soundseek-map-tooltip.visible {
#     opacity: 1;
#     visibility: visible;
# }

# .soundseek-map-card .soundseek-map-tooltip,
# .soundseek-map-card .soundseek-map-tooltip * {
#     color: #f8fafc !important;
# }

# .soundseek-map-tooltip-title {
#     overflow: hidden;
#     font-size: 13px;
#     font-weight: 650;
#     line-height: 1.25;
#     text-overflow: ellipsis;
#     white-space: nowrap;
# }

# .soundseek-map-tooltip-artist {
#     margin-top: 2px;
#     overflow: hidden;
#     color: #cbd5e1 !important;
#     font-size: 11px;
#     line-height: 1.2;
#     text-overflow: ellipsis;
#     white-space: nowrap;
# }

# .soundseek-map-legend-block {
#     margin-top: 13px;
#     padding-top: 11px;
#     border-top: 1px solid #e2e8f0;
# }

# .soundseek-map-legend-title {
#     margin-bottom: 8px;
#     color: #64748b !important;
#     font-size: 11px;
#     font-weight: 650;
#     letter-spacing: 0.08em;
#     text-transform: uppercase;
# }

# .soundseek-map-legend {
#     display: flex;
#     flex-wrap: wrap;
#     gap: 7px 9px;
# }

# .soundseek-map-legend-item {
#     display: inline-flex;
#     align-items: center;
#     gap: 6px;
#     max-width: 100%;
#     padding: 4px 9px;
#     border-radius: 999px;
#     background: #eef2f7 !important;
#     color: #334155 !important;
#     font-size: 12px;
#     line-height: 1.25;
# }

# .soundseek-map-swatch {
#     flex: 0 0 auto;
#     width: 9px;
#     height: 9px;
#     border-radius: 50%;
#     box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.12);
# }

# .soundseek-map-legend-count {
#     color: #64748b !important;
#     font-variant-numeric: tabular-nums;
# }

# .soundseek-map-empty {
#     padding: 22px !important;
#     text-align: center;
# }

# /* ---------- Глобальный плеер ---------- */

# #soundseek-global-player {
#     position: fixed !important;
#     top: 76px !important;
#     right: 18px !important;
#     z-index: 1200 !important;
#     flex-direction: column !important;
#     gap: 10px !important;
#     width: min(340px, calc(100vw - 36px)) !important;
#     max-height: calc(100vh - 96px);
#     overflow-y: auto;
#     padding: 14px 42px 14px 14px !important;
#     border: 1px solid #dbe3ee !important;
#     border-radius: 16px !important;
#     background: #f8fafc !important;
#     color: #1a2b47 !important;
#     box-shadow: 0 18px 45px rgba(15, 23, 42, 0.2) !important;
# }

# #soundseek-global-player * {
#     color: #1a2b47 !important;
# }

# #soundseek-global-player .soundseek-global-title {
#     margin: 0 0 2px !important;
#     font-size: 15px !important;
#     line-height: 1.2 !important;
# }

# #soundseek-global-player .soundseek-global-meta {
#     margin: 0 0 2px !important;
# }

# #soundseek-global-player .soundseek-player-track {
#     color: #1a2b47 !important;
#     font-size: 14px !important;
#     font-weight: 700 !important;
#     line-height: 1.3 !important;
# }

# #soundseek-global-player .soundseek-player-artist {
#     margin-top: 3px;
#     color: #5f6f87 !important;
#     font-size: 11px !important;
#     line-height: 1.35 !important;
# }

# #soundseek-global-player .soundseek-player-error {
#     color: #b42318 !important;
#     font-size: 12px !important;
#     line-height: 1.4 !important;
# }

# #soundseek-global-player .block {
#     border: none !important;
#     box-shadow: none !important;
#     background: transparent !important;
# }

# #soundseek-global-player audio {
#     width: 100%;
# }

# #soundseek-global-close,
# #soundseek-global-close button {
#     position: absolute !important;
#     top: 9px !important;
#     right: 9px !important;
#     display: inline-flex !important;
#     align-items: center !important;
#     justify-content: center !important;
#     width: 28px !important;
#     height: 28px !important;
#     min-width: 28px !important;
#     padding: 0 !important;
#     border: 1px solid #dbe3ee !important;
#     border-radius: 50% !important;
#     background: #ffffff !important;
#     color: #40506a !important;
#     font-size: 14px !important;
#     line-height: 1 !important;
# }

# #soundseek-global-close:hover,
# #soundseek-global-close button:hover {
#     border-color: #f0a5a0 !important;
#     background: #fff1f0 !important;
#     color: #b42318 !important;
# }

# .soundseek-play-button {
#     display: inline-flex;
#     flex: 0 0 auto;
#     align-items: center;
#     justify-content: center;
#     width: 32px;
#     height: 32px;
#     min-width: 32px;
#     margin: 0;
#     padding: 0;
#     border: 0;
#     border-radius: 50%;
#     background: #2563eb !important;
#     color: #ffffff !important;
#     font-size: 12px !important;
#     line-height: 1;
#     cursor: pointer;
#     box-shadow: 0 2px 7px rgba(37, 99, 235, 0.28);
#     transition: background 130ms ease, transform 130ms ease;
# }

# .soundseek-light-card .soundseek-play-button,
# .soundseek-album-detail .soundseek-play-button {
#     background: #2563eb !important;
#     color: #ffffff !important;
# }

# .soundseek-light-card .soundseek-play-button *,
# .soundseek-album-detail .soundseek-play-button * {
#     color: #ffffff !important;
# }

# .soundseek-play-button:hover {
#     background: #1d4ed8 !important;
#     transform: translateY(-1px) scale(1.04);
# }

# .soundseek-play-button:focus-visible {
#     outline: 3px solid rgba(37, 99, 235, 0.38);
#     outline-offset: 2px;
# }

# .soundseek-album-track .soundseek-play-button {
#     width: 26px;
#     height: 26px;
#     min-width: 26px;
#     font-size: 10px !important;
# }

# .soundseek-row-play,
# .soundseek-row-play button {
#     width: 36px !important;
#     height: 36px !important;
#     min-width: 36px !important;
#     padding: 0 !important;
#     border-radius: 50% !important;
#     font-size: 11px !important;
#     line-height: 1 !important;
# }

# .soundseek-map-tooltip-action {
#     margin-top: 4px;
#     color: #93c5fd !important;
#     font-size: 10px;
#     font-weight: 650;
#     letter-spacing: 0.04em;
#     line-height: 1.2;
# }

# @media (max-width: 720px) {
#     #soundseek-global-player {
#         top: 68px !important;
#         right: 10px !important;
#         width: calc(100vw - 20px) !important;
#         max-height: calc(100vh - 88px);
#     }
# }

# /* Пока плеер открыт, освобождаем место справа на широком экране,
#    чтобы он не закрывал элементы управления. */
# @media (min-width: 1280px) {
#     body:has(#soundseek-global-player) .gradio-container main.contain {
#         box-sizing: border-box !important;
#         padding-right: 360px !important;
#     }
# }

# /* ---------- Альбомы ---------- */

# .soundseek-albums-page {
#     display: flex;
#     flex-direction: column;
#     gap: 28px;
# }

# .soundseek-albums-section {
#     display: flex;
#     flex-direction: column;
#     gap: 14px;
# }

# .soundseek-albums-heading {
#     display: flex;
#     align-items: flex-end;
#     justify-content: space-between;
#     gap: 16px;
# }

# .soundseek-albums-kicker {
#     color: var(--body-text-color, #64748b) !important;
#     opacity: 0.62;
#     font-size: 11px;
#     font-weight: 650;
#     letter-spacing: 0.1em;
#     text-transform: uppercase;
# }

# .soundseek-albums-title {
#     margin: 3px 0 0 !important;
#     color: var(--body-text-color, #1a2b47) !important;
#     font-size: 19px;
#     font-weight: 700;
#     line-height: 1.2;
# }

# .soundseek-albums-count {
#     flex: 0 0 auto;
#     padding: 5px 10px;
#     border-radius: 999px;
#     background: var(--background-fill-secondary, #eef2f7) !important;
#     color: var(--body-text-color, #40506a) !important;
#     font-size: 12px;
#     font-variant-numeric: tabular-nums;
# }

# .soundseek-album-grid {
#     display: grid;
#     grid-template-columns: repeat(auto-fill, minmax(168px, 1fr));
#     gap: 18px 16px;
# }

# .soundseek-album-card {
#     display: flex;
#     flex-direction: column;
#     gap: 8px;
#     width: 100%;
#     margin: 0;
#     padding: 0;
#     border: 0;
#     outline: none;
#     background: transparent;
#     color: var(--body-text-color, #1a2b47);
#     font: inherit;
#     text-align: left;
#     cursor: pointer;
# }

# .soundseek-album-cover {
#     position: relative;
#     width: 100%;
#     aspect-ratio: 1 / 1;
#     overflow: hidden;
#     border: 1px solid var(--border-color-primary, #dbe3ee);
#     border-radius: 14px;
#     background: #e2e8f0;
#     box-shadow: 0 7px 18px rgba(15, 23, 42, 0.1);
#     transition: transform 150ms ease, box-shadow 150ms ease;
# }

# .soundseek-album-cover img {
#     display: block;
#     width: 100%;
#     height: 100%;
#     object-fit: cover;
# }

# .soundseek-album-card:hover .soundseek-album-cover {
#     transform: translateY(-3px);
#     box-shadow: 0 14px 28px rgba(15, 23, 42, 0.17);
# }

# .soundseek-album-card:focus-visible .soundseek-album-cover {
#     outline: 3px solid #2563eb;
#     outline-offset: 3px;
# }

# .soundseek-album-card.selected .soundseek-album-cover {
#     outline: 3px solid #2563eb;
#     outline-offset: 3px;
#     box-shadow: 0 0 0 7px rgba(37, 99, 235, 0.18);
# }

# .soundseek-album-placeholder {
#     display: flex;
#     flex-direction: column;
#     align-items: center;
#     justify-content: center;
#     gap: 7px;
#     width: 100%;
#     height: 100%;
#     padding: 12px;
#     background:
#         radial-gradient(circle at 28% 20%, rgba(255, 255, 255, 0.3), transparent 32%),
#         linear-gradient(145deg, var(--album-accent, #2563eb), #0f172a);
#     color: #ffffff !important;
#     text-align: center;
# }

# .soundseek-album-placeholder-letter {
#     font-size: 48px;
#     font-weight: 750;
#     letter-spacing: -0.05em;
#     line-height: 1;
#     color: #ffffff !important;
# }

# .soundseek-album-glyph {
#     font-size: 42px;
#     line-height: 1;
#     color: #ffffff !important;
# }

# .soundseek-album-placeholder-label {
#     max-width: 100%;
#     padding: 0 10px;
#     overflow: hidden;
#     color: #e2e8f0 !important;
#     font-size: 10px;
#     font-weight: 650;
#     letter-spacing: 0.1em;
#     line-height: 1.25;
#     text-overflow: ellipsis;
#     text-transform: uppercase;
#     white-space: nowrap;
# }

# .soundseek-album-caption {
#     min-width: 0;
# }

# .soundseek-album-title {
#     display: -webkit-box;
#     overflow: hidden;
#     color: var(--body-text-color, #1a2b47) !important;
#     font-size: 13px;
#     font-weight: 650;
#     line-height: 1.3;
#     -webkit-box-orient: vertical;
#     -webkit-line-clamp: 2;
# }

# .soundseek-album-meta {
#     margin-top: 2px;
#     overflow: hidden;
#     color: var(--body-text-color, #5f6f87) !important;
#     opacity: 0.66;
#     font-size: 11px;
#     line-height: 1.3;
#     text-overflow: ellipsis;
#     white-space: nowrap;
# }

# .soundseek-albums-empty {
#     padding: 16px;
#     border: 1px dashed var(--border-color-primary, #cbd5e1);
#     border-radius: 12px;
#     color: var(--body-text-color, #5f6f87) !important;
#     font-size: 13px;
#     line-height: 1.45;
# }

# #soundseek-album-detail {
#     scroll-margin-top: 86px;
# }

# .soundseek-album-detail {
#     margin-bottom: 18px;
#     padding: 16px;
#     border: 1px solid #d0d7e2 !important;
#     border-radius: 14px !important;
#     background: #ffffff !important;
#     color: #1a2b47 !important;
# }

# .soundseek-album-detail-head {
#     display: flex;
#     align-items: center;
#     gap: 14px;
# }

# .soundseek-album-detail-cover {
#     flex: 0 0 86px;
#     width: 86px;
#     height: 86px;
#     overflow: hidden;
#     border-radius: 12px;
#     background: #e2e8f0;
#     box-shadow: 0 5px 14px rgba(15, 23, 42, 0.13);
# }

# .soundseek-album-detail-cover img {
#     display: block;
#     width: 100%;
#     height: 100%;
#     object-fit: cover;
# }

# .soundseek-album-detail-copy {
#     min-width: 0;
# }

# .soundseek-album-detail-kicker {
#     color: #64748b !important;
#     font-size: 10px;
#     font-weight: 650;
#     letter-spacing: 0.1em;
#     text-transform: uppercase;
# }

# .soundseek-album-detail-title {
#     margin-top: 2px;
#     overflow-wrap: anywhere;
#     color: #1a2b47 !important;
#     font-size: 18px;
#     font-weight: 700;
#     line-height: 1.25;
# }

# .soundseek-album-detail-meta {
#     margin-top: 3px;
#     color: #5f6f87 !important;
#     font-size: 12px;
#     line-height: 1.35;
# }

# .soundseek-album-detail-empty {
#     padding: 18px;
# }

# .soundseek-album-tracklist {
#     max-height: min(48vh, 520px);
#     margin: 14px 0 0;
#     padding: 0;
#     overflow-y: auto;
#     border-top: 1px solid #e2e8f0;
#     list-style: none;
# }

# .soundseek-album-track {
#     display: grid;
#     grid-template-columns: 34px 26px minmax(0, 1fr) auto;
#     gap: 10px;
#     align-items: center;
#     padding: 8px 4px;
#     border-bottom: 1px solid #eef2f7;
# }

# .soundseek-album-track:last-child {
#     border-bottom: 0;
# }

# .soundseek-album-track-number {
#     color: #94a3b8 !important;
#     font-size: 11px;
#     font-variant-numeric: tabular-nums;
# }

# .soundseek-album-track-copy {
#     min-width: 0;
# }

# .soundseek-album-track-title {
#     display: block;
#     overflow: hidden;
#     color: #1a2b47 !important;
#     font-size: 13px;
#     font-weight: 600;
#     text-overflow: ellipsis;
#     white-space: nowrap;
# }

# .soundseek-album-track-meta {
#     display: block;
#     overflow: hidden;
#     color: #5f6f87 !important;
#     font-size: 11px;
#     text-overflow: ellipsis;
#     white-space: nowrap;
# }

# .soundseek-album-track-duration {
#     color: #5f6f87 !important;
#     font-size: 11px;
#     font-variant-numeric: tabular-nums;
# }

# @media (max-width: 620px) {
#     .soundseek-album-grid {
#         grid-template-columns: repeat(2, minmax(0, 1fr));
#         gap: 14px 12px;
#     }

#     .soundseek-album-detail-cover {
#         flex-basis: 64px;
#         width: 64px;
#         height: 64px;
#     }

#     .soundseek-album-detail-title {
#         font-size: 16px;
#     }
# }
# """

"""Общие стили Gradio-интерфейса — тёмная пастельно-бирюзовая тема.

Вся палитра вынесена в CSS-переменные ``--ss-*``. Это позволяет
перекрашивать интерфейс в одном месте, не трогая разметку. Пользовательские
карточки (результаты поиска, альбомы, плеер) больше не имеют фиксированных
светлых цветов — в тёмной теме они выглядят как часть поверхности.
"""

from __future__ import annotations

APP_CSS = """
/* =========================================================================
   SoundSeek — тёмная пастельно-бирюзовая палитра
   ========================================================================= */

:root,
body,
body.light,
body.dark,
.gradio-container,
.gradio-container.light,
.gradio-container.dark {
    --ss-bg:        #0a1116;
    --ss-bg-soft:   #0f1820;
    --ss-surface:   #141e28;
    --ss-surface-2: #19242f;
    --ss-surface-3: #223242;

    --ss-line:        rgba(94, 234, 212, 0.10);
    --ss-line-strong: rgba(94, 234, 212, 0.24);

    --ss-text:       #e2ecf2;
    --ss-text-soft:  #9fb2c1;
    --ss-text-muted: #657c8e;

    --ss-accent:      #2dd4bf;
    --ss-accent-deep: #0d9488;
    --ss-accent-soft: rgba(45, 212, 191, 0.12);
    --ss-accent-glow: rgba(45, 212, 191, 0.32);
    --ss-coral:       #f87171;
    --ss-coral-soft:  rgba(248, 113, 113, 0.14);

    --ss-radius-lg: 18px;
    --ss-radius-md: 12px;
    --ss-radius-sm: 8px;

    --ss-shadow-sm: 0 2px 10px rgba(0, 0, 0, 0.28);
    --ss-shadow-md: 0 10px 30px rgba(0, 0, 0, 0.42);
    --ss-shadow-lg: 0 24px 60px rgba(0, 0, 0, 0.55);

    /* ---- Подмена переменных Gradio ---- */
    --body-background-fill: var(--ss-bg) !important;
    --body-text-color: var(--ss-text) !important;
    --body-text-color-subdued: var(--ss-text-soft) !important;

    --background-fill-primary: var(--ss-bg-soft) !important;
    --background-fill-secondary: var(--ss-surface) !important;

    --block-background-fill: var(--ss-surface) !important;
    --block-border-color: var(--ss-line) !important;
    --block-label-background-fill: var(--ss-surface-2) !important;
    --block-label-text-color: var(--ss-text-soft) !important;
    --block-title-text-color: var(--ss-text-soft) !important;

    --border-color-primary: var(--ss-line) !important;
    --border-color-accent: var(--ss-accent) !important;

    --input-background-fill: var(--ss-surface-2) !important;
    --input-border-color: var(--ss-line) !important;
    --input-border-color-focus: var(--ss-accent) !important;
    --input-text-color: var(--ss-text) !important;
    --input-placeholder-color: var(--ss-text-muted) !important;

    --button-primary-background-fill: var(--ss-accent-deep) !important;
    --button-primary-background-fill-hover: var(--ss-accent) !important;
    --button-primary-text-color: #041a18 !important;
    --button-primary-border-color: transparent !important;

    --button-secondary-background-fill: var(--ss-surface-2) !important;
    --button-secondary-background-fill-hover: var(--ss-surface-3) !important;
    --button-secondary-text-color: var(--ss-text) !important;
    --button-secondary-border-color: var(--ss-line) !important;

    --color-accent: var(--ss-accent) !important;
    --color-accent-soft: var(--ss-accent-soft) !important;

    color-scheme: dark !important;
}

body {
    background: var(--ss-bg) !important;
    color: var(--ss-text) !important;
}

.gradio-container {
    background: var(--ss-bg) !important;
    color: var(--ss-text) !important;
    font-family: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
}

/* Заголовки — солидный цвет, без gradient-clip.
   Gradio перекрывает background у .prose h1, из-за чего при
   -webkit-text-fill-color: transparent буквы становились невидимыми. */
.gradio-container h1,
.gradio-container .prose h1 {
    color: var(--ss-text) !important;
    background: none !important;
    -webkit-text-fill-color: currentColor !important;
    font-weight: 700;
    letter-spacing: -0.015em;
}

.gradio-container h1::after,
.gradio-container .prose h1::after {
    content: "";
    display: block;
    width: 64px;
    height: 3px;
    margin-top: 12px;
    border-radius: 3px;
    background: linear-gradient(90deg, var(--ss-accent) 0%, transparent 100%);
}

.gradio-container h2,
.gradio-container h3,
.gradio-container .prose h2,
.gradio-container .prose h3 {
    color: var(--ss-text) !important;
    -webkit-text-fill-color: currentColor !important;
    background: none !important;
    font-weight: 650;
    letter-spacing: -0.005em;
}

/* ---------- Карточка-поверхность ---------- */

.soundseek-card {
    background: var(--ss-surface) !important;
    color: var(--ss-text) !important;
    border: 1px solid var(--ss-line) !important;
    border-radius: var(--ss-radius-lg) !important;
    box-shadow: var(--ss-shadow-sm);
}

.soundseek-card * {
    color: inherit;
}

/* ---------- Разбор запроса ---------- */

.soundseek-summary {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 10px;
    margin-bottom: 16px;
    padding: 10px 14px;
    background: var(--ss-surface) !important;
    border: 1px solid var(--ss-line) !important;
    border-radius: var(--ss-radius-md) !important;
    font-size: 13px;
    color: var(--ss-text-soft) !important;
}

.soundseek-summary-label {
    padding: 3px 9px;
    background: var(--ss-accent-soft) !important;
    border-radius: 999px;
    color: var(--ss-accent) !important;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

.soundseek-summary-text {
    color: var(--ss-text-soft) !important;
    line-height: 1.4;
}

/* ---------- Пустой результат ---------- */

.soundseek-empty-card {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 20px 22px;
    background: var(--ss-surface) !important;
    border: 1px dashed var(--ss-line-strong) !important;
    border-radius: var(--ss-radius-lg) !important;
    color: var(--ss-text-soft) !important;
    font-size: 13px;
    line-height: 1.55;
}

.soundseek-empty-icon {
    flex: 0 0 auto;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    background: var(--ss-accent-soft) !important;
    border-radius: 50%;
    color: var(--ss-accent) !important;
    font-size: 18px;
}

.soundseek-empty-text {
    color: var(--ss-text-soft) !important;
}

/* ---------- Карточки результатов поиска ---------- */

.soundseek-results {
    display: flex;
    flex-direction: column;
    gap: 14px;
}

.soundseek-result-card {
    position: relative;
    padding: 18px 20px;
    background: var(--ss-surface) !important;
    border: 1px solid var(--ss-line) !important;
    border-radius: var(--ss-radius-lg) !important;
    box-shadow: var(--ss-shadow-sm);
    transition: border-color 150ms ease, box-shadow 150ms ease,
                transform 150ms ease;
}

.soundseek-result-card:hover {
    border-color: var(--ss-line-strong) !important;
    box-shadow: var(--ss-shadow-md);
    transform: translateY(-1px);
}

.soundseek-result-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
}

.soundseek-result-title {
    display: flex;
    align-items: baseline;
    gap: 12px;
    min-width: 0;
}

.soundseek-result-index {
    color: var(--ss-text-muted) !important;
    font-size: 12px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
}

.soundseek-result-name {
    color: var(--ss-text) !important;
    font-size: 16px;
    font-weight: 650;
    line-height: 1.3;
    overflow-wrap: anywhere;
}

.soundseek-result-meta {
    margin-top: 4px;
    color: var(--ss-text-soft) !important;
    font-size: 13px;
    line-height: 1.4;
}

.soundseek-result-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 12px;
}

.soundseek-chip {
    display: inline-flex;
    align-items: baseline;
    gap: 4px;
    padding: 4px 10px;
    background: var(--ss-surface-2) !important;
    border: 1px solid var(--ss-line) !important;
    border-radius: 999px;
    color: var(--ss-text-soft) !important;
    font-size: 12px;
    line-height: 1.3;
}

.soundseek-chip b {
    color: var(--ss-text) !important;
    font-weight: 600;
}

.soundseek-chip-source {
    color: var(--ss-text-muted) !important;
    font-size: 11px;
}

.soundseek-result-score {
    display: flex;
    align-items: baseline;
    gap: 12px;
    margin-top: 12px;
    padding: 8px 14px;
    background: var(--ss-accent-soft) !important;
    border-radius: var(--ss-radius-md);
}

.soundseek-score-value {
    color: var(--ss-accent) !important;
    font-size: 18px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    line-height: 1;
}

.soundseek-score-detail {
    color: var(--ss-text-soft) !important;
    font-size: 12px;
    line-height: 1.4;
}

.soundseek-result-why {
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--ss-line);
    color: var(--ss-text-soft) !important;
    font-size: 13px;
}

.soundseek-result-why-label {
    display: inline-block;
    margin-bottom: 6px;
    color: var(--ss-text-muted) !important;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.soundseek-result-why ul {
    margin: 0;
    padding-left: 18px;
}

.soundseek-result-why li {
    margin: 3px 0;
    line-height: 1.45;
    color: var(--ss-text-soft) !important;
}

.soundseek-result-extra {
    margin-top: 10px;
    padding: 8px 12px;
    background: var(--ss-surface-2) !important;
    border-radius: var(--ss-radius-sm);
    color: var(--ss-text-soft) !important;
    font-size: 12px;
    line-height: 1.5;
}

.soundseek-result-extra-label {
    display: inline-block;
    margin-right: 8px;
    color: var(--ss-accent) !important;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

/* ---------- Глобальный плеер ---------- */

/* Узкий (260 px) симметричный плеер: top == right == 20px.
   Крестик позиционирован абсолютно и в layout не участвует. */
#soundseek-global-player {
    position: fixed !important;
    top: 20px !important;
    right: 20px !important;
    z-index: 1200 !important;
    display: flex !important;
    flex-direction: column !important;
    gap: 10px !important;
    width: 260px !important;
    max-width: calc(100vw - 40px) !important;
    max-height: calc(100vh - 40px);
    overflow-y: auto;
    padding: 12px !important;
    border: 1px solid var(--ss-line-strong) !important;
    border-radius: 14px !important;
    background: linear-gradient(160deg,
        var(--ss-surface-2) 0%, var(--ss-surface) 100%) !important;
    color: var(--ss-text) !important;
    box-shadow: var(--ss-shadow-lg),
                0 0 0 1px rgba(94, 234, 212, 0.05) inset !important;
    backdrop-filter: blur(16px);
}

/* Заголовок «Сейчас играет» скрываем — экономит ~26 px по высоте. */
#soundseek-global-player .soundseek-global-title {
    display: none !important;
}

/* Метаданные: место справа под крестик, но без лишнего паддинга. */
#soundseek-global-player .soundseek-global-meta {
    margin: 0 !important;
    padding: 0 26px 0 0 !important;
    min-width: 0;
}

#soundseek-global-player .soundseek-player-track {
    color: var(--ss-text) !important;
    font-size: 13px !important;
    font-weight: 650 !important;
    line-height: 1.3 !important;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

#soundseek-global-player .soundseek-player-artist {
    margin-top: 2px;
    color: var(--ss-text-soft) !important;
    font-size: 10.5px !important;
    line-height: 1.35 !important;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

#soundseek-global-player .soundseek-player-error {
    color: var(--ss-coral) !important;
    font-size: 12px !important;
    line-height: 1.4 !important;
}

/* Все внутренние блоки Gradio — без собственных отступов и рамок,
   чтобы содержимое стояло ровно по краям контейнера. */
#soundseek-global-player .block {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    margin: 0 !important;
    padding: 0 !important;
}

#soundseek-global-audio,
#soundseek-global-audio > div {
    margin: 0 !important;
    padding: 0 !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    width: 100% !important;
}

/* ======================================================================
   ВОЛНА → ТОНКАЯ ЛИНИЯ.
   Высота 10 px превращает волновой рисунок в горизонтальную полосу.
   Клик и перемотка продолжают работать (это родительский контейнер).
   ====================================================================== */
#soundseek-global-audio .waveform-container,
#soundseek-global-audio .waveform-wrapper,
#soundseek-global-audio [class*="waveform"] {
    height: 10px !important;
    min-height: 10px !important;
    max-height: 10px !important;
    margin: 2px 0 4px !important;
    background: rgba(94, 234, 212, 0.10) !important;
    border-radius: 5px !important;
    overflow: hidden !important;
}

#soundseek-global-audio .waveform-container canvas,
#soundseek-global-audio .waveform-container svg,
#soundseek-global-audio .waveform-container img {
    height: 10px !important;
    max-height: 10px !important;
    border-radius: 5px !important;
}

/* ---------------------------------------------------------------
   Строка управления: скорость слева, громкость справа.
   Кнопки становятся компактнее — плеер выглядит аккуратнее.
   --------------------------------------------------------------- */
#soundseek-global-audio button {
    min-width: 24px !important;
    min-height: 24px !important;
    padding: 3px !important;
}

/* Play/pause — аккуратный кружок на 28 px. */
#soundseek-global-audio button[aria-label*="play" i],
#soundseek-global-audio button[aria-label*="pause" i],
#soundseek-global-audio button[aria-label*="воспр" i],
#soundseek-global-audio button[aria-label*="ауз" i] {
    width: 28px !important;
    height: 28px !important;
    min-width: 28px !important;
    border-radius: 50% !important;
    background: linear-gradient(135deg,
        var(--ss-accent) 0%, var(--ss-accent-deep) 100%) !important;
    color: #041a18 !important;
    box-shadow: 0 2px 8px var(--ss-accent-glow) !important;
}

/* Громкость — прижимаем к правому краю строки управления. */
#soundseek-global-audio button[aria-label*="olume" i],
#soundseek-global-audio button[aria-label*="ромк" i],
#soundseek-global-audio .volume-control,
#soundseek-global-audio [data-testid="volume"] {
    margin-left: auto !important;
}

/* Время под волной — табличные цифры, мелкий шрифт. */
#soundseek-global-audio [class*="time"],
#soundseek-global-audio .timecode {
    color: var(--ss-text-muted) !important;
    font-size: 10px !important;
    font-variant-numeric: tabular-nums;
}

/* Кнопка закрытия — 26-пиксельный кружок в углу контейнера. */
#soundseek-global-close {
    position: absolute !important;
    top: 10px !important;
    right: 10px !important;
    z-index: 10 !important;
    width: 26px !important;
    height: 26px !important;
    min-width: 26px !important;
    padding: 0 !important;
    margin: 0 !important;
}

#soundseek-global-close button {
    width: 26px !important;
    height: 26px !important;
    min-width: 26px !important;
    padding: 0 !important;
    margin: 0 !important;
    border: 1px solid var(--ss-line) !important;
    border-radius: 50% !important;
    background: var(--ss-surface-3) !important;
    color: var(--ss-text-soft) !important;
    font-size: 12px !important;
    line-height: 1 !important;
    transition: all 140ms ease;
}

#soundseek-global-close button:hover {
    border-color: var(--ss-coral) !important;
    background: var(--ss-coral-soft) !important;
    color: var(--ss-coral) !important;
}

@media (max-width: 720px) {
    #soundseek-global-player {
        top: 14px !important;
        right: 14px !important;
        width: calc(100vw - 28px) !important;
        max-height: calc(100vh - 28px);
    }
}

@media (min-width: 1280px) {
    body:has(#soundseek-global-player) .gradio-container main.contain {
        box-sizing: border-box !important;
        padding-right: 300px !important;
    }
}

/* ---------- Круглая кнопка воспроизведения ---------- */

.soundseek-play-button {
    display: inline-flex;
    flex: 0 0 auto;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    min-width: 34px;
    margin: 0;
    padding: 0;
    border: 0;
    border-radius: 50%;
    background: linear-gradient(135deg,
        var(--ss-accent) 0%, var(--ss-accent-deep) 100%) !important;
    color: #041a18 !important;
    font-size: 12px !important;
    line-height: 1;
    cursor: pointer;
    box-shadow: 0 2px 10px var(--ss-accent-glow);
    transition: transform 140ms ease, box-shadow 140ms ease,
                filter 140ms ease;
}

.soundseek-play-button:hover {
    transform: translateY(-1px) scale(1.06);
    box-shadow: 0 6px 18px var(--ss-accent-glow);
    filter: brightness(1.08);
}

.soundseek-play-button:focus-visible {
    outline: 3px solid var(--ss-accent-glow);
    outline-offset: 2px;
}

.soundseek-album-track .soundseek-play-button {
    width: 28px;
    height: 28px;
    min-width: 28px;
    font-size: 10px !important;
}

.soundseek-row-play,
.soundseek-row-play button {
    width: 36px !important;
    height: 36px !important;
    min-width: 36px !important;
    padding: 0 !important;
    border-radius: 50% !important;
    background: linear-gradient(135deg,
        var(--ss-accent) 0%, var(--ss-accent-deep) 100%) !important;
    color: #041a18 !important;
    font-size: 11px !important;
    line-height: 1 !important;
    box-shadow: 0 2px 10px var(--ss-accent-glow);
}

/* ---------- Карта аудиотеки ---------- */

.soundseek-map-card {
    position: relative;
    padding: 18px !important;
    background: linear-gradient(180deg,
        var(--ss-surface-2) 0%, var(--ss-surface) 100%) !important;
    border: 1px solid var(--ss-line) !important;
    border-radius: var(--ss-radius-lg) !important;
    color: var(--ss-text) !important;
    box-shadow: var(--ss-shadow-sm);
}

.soundseek-map-card * {
    color: inherit;
}

.soundseek-map-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
}

.soundseek-map-kicker {
    color: var(--ss-text-muted) !important;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
}

.soundseek-map-title {
    margin-top: 3px;
    color: var(--ss-text) !important;
    font-size: 19px;
    font-weight: 700;
    line-height: 1.2;
}

.soundseek-map-subtitle {
    margin-top: 5px;
    color: var(--ss-text-soft) !important;
    font-size: 12px;
    line-height: 1.4;
}

.soundseek-map-count {
    flex: 0 0 auto;
    padding: 5px 10px;
    background: var(--ss-accent-soft) !important;
    border-radius: 999px;
    color: var(--ss-accent) !important;
    font-size: 12px;
    font-variant-numeric: tabular-nums;
    font-weight: 600;
}

.soundseek-map-canvas {
    margin-top: 13px;
    overflow: hidden;
    border: 1px solid var(--ss-line);
    border-radius: var(--ss-radius-md);
    background: var(--ss-surface) !important;
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
    stroke: var(--ss-accent);
    stroke-width: 2.5;
    opacity: 0;
    transition: opacity 140ms ease;
    pointer-events: none;
}

.soundseek-map-dot {
    stroke: var(--ss-surface);
    stroke-width: 1.5;
    transition: r 140ms ease, stroke-width 140ms ease, filter 140ms ease;
    pointer-events: none;
}

.soundseek-map-point:hover .soundseek-map-dot,
.soundseek-map-point:focus-visible .soundseek-map-dot {
    r: 9;
    stroke-width: 2.4;
    filter: drop-shadow(0 2px 5px rgba(45, 212, 191, 0.55));
}

.soundseek-map-point:hover .soundseek-map-halo,
.soundseek-map-point:focus-visible .soundseek-map-halo {
    opacity: 0.28;
}

.soundseek-map-point.selected .soundseek-map-halo {
    opacity: 1;
}

.soundseek-map-point.selected .soundseek-map-dot {
    r: 8.5;
    stroke: var(--ss-accent);
    stroke-width: 3;
}

.soundseek-map-tooltip {
    position: absolute;
    z-index: 30;
    max-width: 280px;
    padding: 10px 13px;
    background: var(--ss-surface-3) !important;
    border: 1px solid var(--ss-line-strong) !important;
    border-radius: var(--ss-radius-md);
    box-shadow: var(--ss-shadow-lg);
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
    color: var(--ss-text) !important;
}

.soundseek-map-tooltip-title {
    overflow: hidden;
    color: var(--ss-text) !important;
    font-size: 13px;
    font-weight: 650;
    line-height: 1.3;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.soundseek-map-tooltip-artist {
    margin-top: 2px;
    overflow: hidden;
    color: var(--ss-text-soft) !important;
    font-size: 11px;
    line-height: 1.3;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.soundseek-map-tooltip-action {
    margin-top: 6px;
    color: var(--ss-accent) !important;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.06em;
    line-height: 1.2;
    text-transform: uppercase;
}

.soundseek-map-legend-block {
    margin-top: 14px;
    padding-top: 12px;
    border-top: 1px solid var(--ss-line);
}

.soundseek-map-legend-title {
    margin-bottom: 8px;
    color: var(--ss-text-muted) !important;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
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
    padding: 4px 10px;
    background: var(--ss-surface-3) !important;
    border-radius: 999px;
    color: var(--ss-text-soft) !important;
    font-size: 12px;
    line-height: 1.3;
}

.soundseek-map-swatch {
    flex: 0 0 auto;
    width: 9px;
    height: 9px;
    border-radius: 50%;
    box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.4);
}

.soundseek-map-legend-count {
    color: var(--ss-text-muted) !important;
    font-variant-numeric: tabular-nums;
}

.soundseek-map-empty {
    padding: 24px !important;
    text-align: center;
}

/* ---------- Прокручиваемая библиотека ---------- */

.library-scroll {
    max-height: 62vh !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    padding: 4px 10px 4px 8px !important;
    background: var(--ss-surface) !important;
    border: 1px solid var(--ss-line) !important;
    border-radius: var(--ss-radius-lg) !important;
    scrollbar-gutter: stable;
}

.library-scroll .block {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
}

.library-scroll::-webkit-scrollbar { width: 8px; }
.library-scroll::-webkit-scrollbar-track {
    background: var(--ss-surface);
    border-radius: 4px;
}
.library-scroll::-webkit-scrollbar-thumb {
    background: var(--ss-surface-3);
    border-radius: 4px;
}
.library-scroll::-webkit-scrollbar-thumb:hover {
    background: var(--ss-accent-deep);
}

/* ---------- Полоса фильтров ---------- */

.soundseek-filter-bar {
    padding: 12px !important;
    background: var(--ss-surface) !important;
    border: 1px solid var(--ss-line) !important;
    border-radius: var(--ss-radius-lg) !important;
    gap: 10px !important;
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
    color: var(--ss-text-muted) !important;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}

.soundseek-albums-title {
    margin: 3px 0 0 !important;
    color: var(--ss-text) !important;
    font-size: 19px;
    font-weight: 700;
    line-height: 1.2;
}

.soundseek-albums-count {
    flex: 0 0 auto;
    padding: 5px 10px;
    background: var(--ss-accent-soft) !important;
    border-radius: 999px;
    color: var(--ss-accent) !important;
    font-size: 12px;
    font-weight: 600;
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
    gap: 9px;
    width: 100%;
    margin: 0;
    padding: 0;
    border: 0;
    outline: none;
    background: transparent;
    color: var(--ss-text);
    font: inherit;
    text-align: left;
    cursor: pointer;
}

.soundseek-album-cover {
    position: relative;
    width: 100%;
    aspect-ratio: 1 / 1;
    overflow: hidden;
    border: 1px solid var(--ss-line);
    border-radius: var(--ss-radius-lg);
    background: var(--ss-surface-2);
    box-shadow: var(--ss-shadow-sm);
    transition: transform 160ms ease, box-shadow 160ms ease,
                border-color 160ms ease;
}

.soundseek-album-cover img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.soundseek-album-card:hover .soundseek-album-cover {
    transform: translateY(-3px);
    border-color: var(--ss-line-strong);
    box-shadow: var(--ss-shadow-md),
                0 0 0 1px var(--ss-accent-soft) inset;
}

.soundseek-album-card:focus-visible .soundseek-album-cover {
    outline: 3px solid var(--ss-accent);
    outline-offset: 3px;
}

.soundseek-album-card.selected .soundseek-album-cover {
    border-color: var(--ss-accent);
    outline: 2px solid var(--ss-accent);
    outline-offset: 3px;
    box-shadow: 0 0 0 6px var(--ss-accent-soft);
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
        radial-gradient(circle at 28% 20%,
            rgba(255, 255, 255, 0.15), transparent 32%),
        linear-gradient(145deg, var(--album-accent, #2563eb), #0b1116);
    color: #ffffff !important;
    text-align: center;
}

.soundseek-album-placeholder-letter {
    font-size: 46px;
    font-weight: 750;
    letter-spacing: -0.05em;
    line-height: 1;
    color: #ffffff !important;
}

.soundseek-album-glyph {
    font-size: 40px;
    line-height: 1;
    color: #ffffff !important;
}

.soundseek-album-placeholder-label {
    max-width: 100%;
    padding: 0 10px;
    overflow: hidden;
    color: #e6eef5 !important;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
    line-height: 1.3;
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
    color: var(--ss-text) !important;
    font-size: 13px;
    font-weight: 650;
    line-height: 1.35;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
}

.soundseek-album-meta {
    margin-top: 2px;
    overflow: hidden;
    color: var(--ss-text-muted) !important;
    font-size: 11px;
    line-height: 1.35;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.soundseek-albums-empty {
    padding: 16px;
    background: var(--ss-surface) !important;
    border: 1px dashed var(--ss-line-strong) !important;
    border-radius: var(--ss-radius-md) !important;
    color: var(--ss-text-soft) !important;
    font-size: 13px;
    line-height: 1.5;
}

#soundseek-album-detail {
    scroll-margin-top: 86px;
}

.soundseek-album-detail {
    margin-bottom: 18px;
    padding: 18px;
    background: var(--ss-surface) !important;
    border: 1px solid var(--ss-line) !important;
    border-radius: var(--ss-radius-lg) !important;
    color: var(--ss-text) !important;
    box-shadow: var(--ss-shadow-sm);
}

.soundseek-album-detail-head {
    display: flex;
    align-items: center;
    gap: 14px;
}

.soundseek-album-detail-cover {
    flex: 0 0 88px;
    width: 88px;
    height: 88px;
    overflow: hidden;
    border-radius: var(--ss-radius-md);
    background: var(--ss-surface-2);
    box-shadow: var(--ss-shadow-sm);
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
    color: var(--ss-text-muted) !important;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}

.soundseek-album-detail-title {
    margin-top: 2px;
    color: var(--ss-text) !important;
    font-size: 18px;
    font-weight: 700;
    line-height: 1.25;
    overflow-wrap: anywhere;
}

.soundseek-album-detail-meta {
    margin-top: 3px;
    color: var(--ss-text-soft) !important;
    font-size: 12px;
    line-height: 1.4;
}

.soundseek-album-detail-empty {
    padding: 22px;
}

.soundseek-album-tracklist {
    max-height: min(48vh, 520px);
    margin: 14px 0 0;
    padding: 0;
    overflow-y: auto;
    border-top: 1px solid var(--ss-line);
    list-style: none;
}

.soundseek-album-track {
    display: grid;
    grid-template-columns: 34px 30px minmax(0, 1fr) auto;
    gap: 10px;
    align-items: center;
    padding: 9px 6px;
    border-bottom: 1px solid var(--ss-line);
    transition: background 120ms ease;
}

.soundseek-album-track:hover {
    background: var(--ss-surface-2);
}

.soundseek-album-track:last-child {
    border-bottom: 0;
}

.soundseek-album-track-number {
    color: var(--ss-text-muted) !important;
    font-size: 11px;
    font-variant-numeric: tabular-nums;
}

.soundseek-album-track-copy {
    min-width: 0;
}

.soundseek-album-track-title {
    display: block;
    overflow: hidden;
    color: var(--ss-text) !important;
    font-size: 13px;
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.soundseek-album-track-meta {
    display: block;
    overflow: hidden;
    color: var(--ss-text-soft) !important;
    font-size: 11px;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.soundseek-album-track-duration {
    color: var(--ss-text-muted) !important;
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

/* ---------- Плейлист ---------- */

.soundseek-playlist {
    padding: 8px 6px;
    background: var(--ss-surface) !important;
    border: 1px solid var(--ss-line) !important;
    border-radius: var(--ss-radius-lg) !important;
}

.soundseek-playlist ol {
    margin: 0;
    padding: 0;
    list-style: none;
}

.soundseek-playlist-row {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 10px 8px;
    border-bottom: 1px solid var(--ss-line);
    transition: background 120ms ease;
}

.soundseek-playlist-row:hover {
    background: var(--ss-surface-2);
}

.soundseek-playlist-row:last-child {
    border-bottom: 0;
}

.soundseek-playlist-copy {
    min-width: 0;
}

.soundseek-playlist-title {
    color: var(--ss-text) !important;
    font-size: 14px;
    font-weight: 650;
    line-height: 1.35;
    overflow-wrap: anywhere;
}

.soundseek-playlist-artist {
    margin-top: 1px;
    color: var(--ss-text-soft) !important;
    font-size: 12px;
    line-height: 1.35;
}

.soundseek-playlist-meta {
    margin-top: 3px;
    color: var(--ss-text-muted) !important;
    font-size: 11px;
    line-height: 1.4;
}

/* ---------- HTML-таблица библиотеки ---------- */

.soundseek-lib {
    background: var(--ss-surface) !important;
    border: 1px solid var(--ss-line) !important;
    border-radius: var(--ss-radius-lg) !important;
    box-shadow: var(--ss-shadow-sm);
    overflow: hidden;
}

.soundseek-lib-scroll {
    max-height: 62vh;
    overflow-y: auto;
    overflow-x: auto;
    scrollbar-gutter: stable;
}

.soundseek-lib-scroll::-webkit-scrollbar { width: 10px; height: 10px; }
.soundseek-lib-scroll::-webkit-scrollbar-track {
    background: var(--ss-surface);
}
.soundseek-lib-scroll::-webkit-scrollbar-thumb {
    background: var(--ss-surface-3);
    border-radius: 6px;
    border: 2px solid var(--ss-surface);
}
.soundseek-lib-scroll::-webkit-scrollbar-thumb:hover {
    background: var(--ss-accent-deep);
}

.soundseek-lib-head,
.soundseek-lib-row {
    display: grid;
    grid-template-columns: 40px 34px minmax(0, 1fr) 96px 110px 120px 220px 70px;
    gap: 14px;
    align-items: center;
    min-width: 740px;
    padding: 10px 18px;
}

.soundseek-lib-head {
    position: sticky;
    top: 0;
    z-index: 2;
    padding-top: 12px;
    padding-bottom: 12px;
    background: var(--ss-surface-2);
    border-bottom: 1px solid var(--ss-line-strong);
    color: var(--ss-text-muted) !important;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    white-space: nowrap;
}

.soundseek-lib-row {
    border-bottom: 1px solid var(--ss-line);
    cursor: pointer;
    transition: background 120ms ease;
}

.soundseek-lib-row.is-selected {
    background: var(--ss-accent-soft);
    box-shadow: inset 3px 0 0 var(--ss-accent);
}

.soundseek-lib-row:focus-visible {
    outline: 2px solid var(--ss-accent);
    outline-offset: -2px;
}

.soundseek-lib-row:last-child {
    border-bottom: 0;
}

.soundseek-lib-row:hover {
    background: var(--ss-surface-2);
}

.soundseek-lib-cell {
    min-width: 0;
    color: var(--ss-text) !important;
    font-size: 13px;
    line-height: 1.4;
}

.soundseek-lib-play {
    display: flex;
    align-items: center;
    justify-content: flex-start;
}

.soundseek-lib-play .soundseek-play-button {
    width: 30px;
    height: 30px;
    min-width: 30px;
    font-size: 11px !important;
}

.soundseek-lib-index {
    color: var(--ss-text-muted) !important;
    font-size: 11px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
}

.soundseek-lib-title {
    overflow: hidden;
    color: var(--ss-text) !important;
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.soundseek-lib-tag {
    display: inline-block;
    padding: 2px 9px;
    background: var(--ss-accent-soft) !important;
    border-radius: 999px;
    color: var(--ss-accent) !important;
    font-size: 11px;
    font-weight: 600;
    line-height: 1.4;
    white-space: nowrap;
}

.soundseek-lib-muted {
    color: var(--ss-text-soft) !important;
    font-size: 13px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.soundseek-lib-duration {
    color: var(--ss-text-muted) !important;
    font-size: 12px;
    font-variant-numeric: tabular-nums;
    text-align: right;
}

.soundseek-lib-status {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: nowrap;
}

.soundseek-lib-vocal {
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    background: var(--ss-surface-3) !important;
    border-radius: 999px;
    color: var(--ss-text-soft) !important;
    font-size: 10px;
    font-weight: 600;
    line-height: 1.5;
    white-space: nowrap;
}

.soundseek-lib-vocal.is-yes {
    background: rgba(45, 212, 191, 0.16) !important;
    color: var(--ss-accent) !important;
}

.soundseek-lib-vocal.is-no {
    background: rgba(148, 163, 184, 0.14) !important;
    color: var(--ss-text-muted) !important;
}

.soundseek-lib-enrich {
    display: inline-flex;
    align-items: center;
    padding: 4px 11px;
    border: 1px solid var(--ss-line-strong);
    border-radius: 999px;
    background: transparent;
    color: var(--ss-text) !important;
    font-size: 11px;
    font-weight: 600;
    line-height: 1.4;
    white-space: nowrap;
    cursor: pointer;
    transition: border-color 140ms ease, background 140ms ease,
                color 140ms ease;
}

.soundseek-lib-enrich:hover {
    border-color: var(--ss-accent);
    background: var(--ss-accent-soft);
    color: var(--ss-accent) !important;
}

.soundseek-lib-enrich[data-state="error"] {
    border-color: rgba(248, 113, 113, 0.45);
    color: var(--ss-coral) !important;
}

.soundseek-lib-enrich[data-state="error"]:hover {
    background: var(--ss-coral-soft);
    border-color: var(--ss-coral);
}

.soundseek-lib-status-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 10px;
    background: var(--ss-surface-3) !important;
    border-radius: 999px;
    color: var(--ss-text-soft) !important;
    font-size: 11px;
    font-weight: 600;
    line-height: 1.4;
    white-space: nowrap;
}

.soundseek-lib-status-chip.is-active {
    background: var(--ss-accent-soft) !important;
    color: var(--ss-accent) !important;
}

.soundseek-lib-status-chip.is-active::before {
    content: "";
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--ss-accent);
    animation: soundseek-pulse 1.2s ease-in-out infinite;
}

.soundseek-lib-status-chip.is-done {
    background: rgba(45, 212, 191, 0.18) !important;
    color: var(--ss-accent) !important;
}

.soundseek-lib-empty {
    padding: 44px 20px;
    background: var(--ss-surface) !important;
    border: 1px dashed var(--ss-line-strong) !important;
    border-radius: var(--ss-radius-lg) !important;
    color: var(--ss-text-soft) !important;
    font-size: 13px;
    text-align: center;
}
"""