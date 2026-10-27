"""Фоновая очередь обогащения треков.

Состояние хранится не только в памяти, но и в ``track.derived.enrich_status``.
Поэтому после перезапуска приложения уже обработанные треки не запускаются
повторно, а ошибки видны в интерфейсе.
"""

from __future__ import annotations

import threading
from collections import deque

from soundseek_core.indexer import AudioIndexer


class EnrichmentQueue:
    def __init__(self, indexer: AudioIndexer):
        self.indexer = indexer
        self._queue: deque[tuple[str, bool]] = deque()
        self._running: str | None = None
        self._running_force = False
        self._lock = threading.Lock()
        self._thread_started = False

    def enqueue(self, track_id: str, force: bool = False) -> None:
        with self._lock:
            if track_id == self._running:
                return
            for index, (queued_id, queued_force) in enumerate(self._queue):
                if queued_id == track_id:
                    if force and not queued_force:
                        self._queue[index] = (track_id, True)
                    return
            self._queue.append((track_id, force))
            if not self._thread_started:
                self._thread_started = True
                threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self) -> None:
        while True:
            with self._lock:
                if not self._queue:
                    self._running = None
                    self._thread_started = False
                    return
                track_id, force = self._queue.popleft()
                self._running = track_id
                self._running_force = force

            track = self.indexer.db.get(track_id)
            if track is None:
                with self._lock:
                    self._running = None
                continue
            try:
                self.indexer.enrich_single_track(track, force=force)
            except Exception as exc:  # pragma: no cover - защита от падения UI
                print(f"Ошибка обогащения {track_id}: {exc}")
                track.derived.enrich_status = "error"
                track.derived.enrich_error = str(exc)
                self.indexer.save()
            finally:
                with self._lock:
                    self._running = None

    def status_map(self) -> dict[str, str]:
        with self._lock:
            queued = {track_id for track_id, _ in self._queue}
            running = self._running
        status: dict[str, str] = {}
        for track in self.indexer.db.snapshot():
            track_id = track.id
            if track_id == running:
                status[track_id] = "running"
            elif track_id in queued:
                status[track_id] = "queued"
            elif track.derived.enrich_status in ("done", "error", "skipped"):
                status[track_id] = track.derived.enrich_status
            elif track.derived.lyrics:
                status[track_id] = "has_lyrics"
            else:
                status[track_id] = "idle"
        return status

    def reset(self) -> bool:
        """Сбрасывает очередь, только если воркер не выполняет трек."""
        with self._lock:
            if self._running is not None:
                return False
            self._queue.clear()
            self._running_force = False
            return True

    def is_busy(self) -> bool:
        with self._lock:
            return self._running is not None or bool(self._queue)
