"""Thin wrapper around the e2b SDK for workspace sandboxes.

e2b is imported lazily inside each function so the rest of the package (and the
unit tests, which mock these functions) does not require e2b to be installed.
"""

import logging

logger = logging.getLogger(__name__)

# Sandbox states we track ourselves on the workspace row.
RUNNING = "running"
PAUSED = "paused"
KILLED = "killed"

# Keep an idle sandbox alive by pausing (not killing) it when the timeout hits,
# so its filesystem + memory survive until the workspace is deleted.
_IDLE_TIMEOUT_SECONDS = 60 * 60


def create_sandbox() -> str:
    """Create a base Ubuntu e2b sandbox and return its id.

    The sandbox auto-pauses on idle timeout so it persists for the life of the
    workspace instead of being killed.
    """
    from e2b import Sandbox

    sbx = Sandbox.create(
        timeout=_IDLE_TIMEOUT_SECONDS,
        lifecycle={"on_timeout": "pause", "auto_resume": False},
    )
    logger.info("Created sandbox %s", sbx.sandbox_id)
    return sbx.sandbox_id


def pause_sandbox(sandbox_id: str) -> None:
    """Pause a running sandbox, preserving its state."""
    from e2b import Sandbox

    Sandbox.connect(sandbox_id).pause()
    logger.info("Paused sandbox %s", sandbox_id)


def resume_sandbox(sandbox_id: str) -> None:
    """Resume a paused sandbox (connecting resumes it)."""
    from e2b import Sandbox

    Sandbox.connect(sandbox_id)
    logger.info("Resumed sandbox %s", sandbox_id)


def kill_sandbox(sandbox_id: str) -> None:
    """Permanently delete a sandbox."""
    from e2b import Sandbox

    Sandbox.kill(sandbox_id)
    logger.info("Killed sandbox %s", sandbox_id)


def get_sandbox_state(sandbox_id: str) -> str:
    """Query e2b for a sandbox's real state without resuming it.

    Returns RUNNING, PAUSED, or KILLED (when the sandbox no longer exists).
    Uses Sandbox.list() because connecting to a paused sandbox would resume it.
    """
    from e2b import Sandbox, SandboxQuery, SandboxState

    paginator = Sandbox.list(
        query=SandboxQuery(state=[SandboxState.RUNNING, SandboxState.PAUSED]),
    )
    while paginator.has_next:
        for item in paginator.next_items():
            if item.sandbox_id == sandbox_id:
                return RUNNING if item.state == SandboxState.RUNNING else PAUSED
    return KILLED
