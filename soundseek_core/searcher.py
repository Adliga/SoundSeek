"""Совместимый фасад поискового движка.

Новая реализация живёт в пакете :mod:`soundseek_core.search`; этот модуль
оставлен, чтобы старые скрипты и внешние импорты продолжали работать.
"""

from __future__ import annotations

from .search import SearchEngine


class Searcher(SearchEngine):
    pass


__all__ = ["Searcher", "SearchEngine"]
