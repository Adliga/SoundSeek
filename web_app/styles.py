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
"""
