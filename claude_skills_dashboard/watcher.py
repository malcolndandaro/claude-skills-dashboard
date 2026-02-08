"""File watcher for live updates to session files."""

import threading
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import (
    FileCreatedEvent,
    FileModifiedEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

from .reader import DEFAULT_PROJECTS_DIR


class SessionFileHandler(FileSystemEventHandler):
    """Handler for session file changes in the projects directory."""

    def __init__(self, callback: Callable[[], None], debounce_seconds: float = 1.0):
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self._last_callback_time = 0.0
        self._lock = threading.Lock()
        self._pending_callback = False
        self._timer: Optional[threading.Timer] = None

    def _should_handle(self, path: Path) -> bool:
        """Check if this file change should trigger a refresh."""
        name = path.name
        # Watch for session files and index files
        return name.endswith(".jsonl") or name == "sessions-index.json"

    def _schedule_callback(self) -> None:
        """Schedule a debounced callback."""
        with self._lock:
            # Cancel any pending timer
            if self._timer is not None:
                self._timer.cancel()

            # Schedule new callback
            self._timer = threading.Timer(self.debounce_seconds, self._execute_callback)
            self._timer.start()

    def _execute_callback(self) -> None:
        """Execute the callback."""
        with self._lock:
            self._timer = None
        self.callback()

    def on_modified(self, event: FileModifiedEvent) -> None:
        """Handle file modification events."""
        if event.is_directory:
            return
        if self._should_handle(Path(event.src_path)):
            self._schedule_callback()

    def on_created(self, event: FileCreatedEvent) -> None:
        """Handle file creation events."""
        if event.is_directory:
            return
        if self._should_handle(Path(event.src_path)):
            self._schedule_callback()


class SessionWatcher:
    """Watches the projects directory for session changes."""

    def __init__(
        self,
        projects_dir: Optional[Path] = None,
        callback: Optional[Callable[[], None]] = None,
        debounce_seconds: float = 1.0,
    ):
        self.projects_dir = projects_dir or DEFAULT_PROJECTS_DIR
        self.callback = callback or (lambda: None)
        self.debounce_seconds = debounce_seconds
        self.observer: Optional[Observer] = None
        self.handler: Optional[SessionFileHandler] = None

    def start(self) -> None:
        """Start watching the projects directory for changes."""
        if self.observer is not None:
            return  # Already running

        if not self.projects_dir.exists():
            return  # No projects directory yet

        self.handler = SessionFileHandler(self.callback, self.debounce_seconds)
        self.observer = Observer()
        # Watch recursively to catch all project subdirectories
        self.observer.schedule(self.handler, str(self.projects_dir), recursive=True)
        self.observer.start()

    def stop(self) -> None:
        """Stop watching the directory."""
        if self.observer is not None:
            self.observer.stop()
            self.observer.join(timeout=2.0)
            self.observer = None
            self.handler = None

    def __enter__(self) -> "SessionWatcher":
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.stop()
