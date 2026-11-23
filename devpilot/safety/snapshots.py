"""File snapshot manager for checkpointing, undo, and state rollback."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from devpilot.core.logging import get_logger
from devpilot.safety.sandbox import PathSandbox

logger = get_logger("devpilot.safety.snapshots")


@dataclass
class Snapshot:
    id: str
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    description: str = ""
    file_contents: dict[str, bytes | None] = field(
        default_factory=dict
    )  # None represents file was non-existent


class SnapshotManager:
    """Captures and restores filesystem states for rollback safety."""

    def __init__(self, sandbox: PathSandbox) -> None:
        self.sandbox = sandbox
        self.snapshots: dict[str, Snapshot] = {}

    def capture(
        self, snapshot_id: str, files_to_track: list[str], description: str = ""
    ) -> Snapshot:
        """Records the current content of specific files."""
        captured: dict[str, bytes | None] = {}
        for rel_path in files_to_track:
            target = self.sandbox.resolve_safe_path(rel_path)
            if target.exists() and target.is_file():
                captured[rel_path] = target.read_bytes()
            else:
                captured[rel_path] = None

        snap = Snapshot(id=snapshot_id, description=description, file_contents=captured)
        self.snapshots[snapshot_id] = snap
        logger.debug("snapshot_captured", id=snapshot_id, tracked_files=len(captured))
        return snap

    def rollback(self, snapshot_id: str) -> list[str]:
        """Restores tracked files to their captured snapshot state."""
        if snapshot_id not in self.snapshots:
            raise ValueError(f"Snapshot '{snapshot_id}' does not exist")

        snap = self.snapshots[snapshot_id]
        restored_files: list[str] = []

        for rel_path, content in snap.file_contents.items():
            target = self.sandbox.resolve_safe_path(rel_path)
            if content is None:
                # File was created after snapshot: delete it
                if target.exists():
                    target.unlink()
                    restored_files.append(f"deleted:{rel_path}")
            else:
                # Restore original content
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                restored_files.append(f"restored:{rel_path}")

        logger.info("rollback_completed", snapshot=snapshot_id, restored_count=len(restored_files))
        return restored_files
