"""File watcher for live updates to skill tracking file and sessions."""

import threading
import time
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import (
    FileCreatedEvent,
    FileModifiedEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

from .models import SkillInvocation
from .reader import DEFAULT_PROJECTS_DIR, DEFAULT_TRACKING_FILE, SkillReader


class SkillFileHandler(FileSystemEventHandler):
    """Handler for skill tracking file changes."""

    def __init__(
        self,
        file_path: Path,
        callback: Callable[[SkillInvocation], None],
    ):
        self.file_path = file_path
        self.callback = callback
        self.reader = SkillReader(file_path)
        self.last_position = self.reader.get_file_size()
        self._lock = threading.Lock()

    def on_modified(self, event: FileModifiedEvent) -> None:
        """Handle file modification events."""
        if event.is_directory:
            return

        # Check if this is our file
        event_path = Path(event.src_path)
        if event_path.name != self.file_path.name:
            return

        self._read_new_entries()

    def _read_new_entries(self) -> None:
        """Read any new entries since last position."""
        with self._lock:
            current_size = self.reader.get_file_size()

            # Handle file truncation (unlikely but possible)
            if current_size < self.last_position:
                self.last_position = 0

            # Read new entries
            for position, invocation in self.reader.iter_from_position(self.last_position):
                self.last_position = position
                self.callback(invocation)


class SkillWatcher:
    """Watches the skill tracking file for new entries."""

    def __init__(
        self,
        file_path: Optional[Path] = None,
        callback: Optional[Callable[[SkillInvocation], None]] = None,
    ):
        self.file_path = file_path or DEFAULT_TRACKING_FILE
        self.callback = callback or (lambda x: None)
        self.observer: Optional[Observer] = None
        self.handler: Optional[SkillFileHandler] = None

    def start(self) -> None:
        """Start watching the file for changes."""
        if self.observer is not None:
            return  # Already running

        # Ensure parent directory exists
        watch_dir = self.file_path.parent
        if not watch_dir.exists():
            watch_dir.mkdir(parents=True, exist_ok=True)

        self.handler = SkillFileHandler(self.file_path, self.callback)
        self.observer = Observer()
        self.observer.schedule(self.handler, str(watch_dir), recursive=False)
        self.observer.start()

    def stop(self) -> None:
        """Stop watching the file."""
        if self.observer is not None:
            self.observer.stop()
            self.observer.join(timeout=2.0)
            self.observer = None
            self.handler = None

    def __enter__(self) -> "SkillWatcher":
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.stop()


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
