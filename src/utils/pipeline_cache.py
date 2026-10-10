import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
STATE_FILE = ROOT_DIR / ".pipeline" / "state.json"


def _load_state():
    """Loading pipeline state from disk."""

    if not STATE_FILE.exists():
        return {}

    try:
        with open(
            STATE_FILE,
            "r",
            encoding="UTF-8"
        ) as file:
            return json.load(file)

    except (json.JSONDecodeError, OSError):
        return {}


def _save_state(state):
    """Save pipeline state to the disk."""

    STATE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    temp_file = STATE_FILE.with_suffix(".tmp")

    with open(
        temp_file,
        "w",
        encoding="UTF-8"
    ) as file:
        json.dump(
            state,
            file,
            indent=4
        )

    temp_file.replace(STATE_FILE)


def get_file_fingerprint(paths):
    """
    Generate a combined SHA-256 fingerprint for one file or an iterable
    of files.

    A stage's script often imports shared helper modules (schema.py,
    io.py, connection.py); fingerprinting only the entry-point script
    means a bug fix in one of those helpers goes undetected and the
    stage is wrongly skipped as "cache valid". Pass every file whose
    changes should invalidate the stage.

    Missing files are skipped (so a caller can pass an optional extra
    file without checking existence first); if every path is missing,
    returns None. Path order matters -- callers must pass a consistent
    order across runs for the fingerprint to be stable.
    """

    if isinstance(paths, (str, Path)):
        paths = [paths]

    digest = hashlib.sha256()
    found_any = False

    for path in paths:

        path = Path(path)

        if not path.exists():
            continue

        found_any = True

        with open(path, "rb") as file:
            for chunk in iter(
                lambda: file.read(1024 * 1024),
                b""
            ):
                digest.update(chunk)

    if not found_any:
        return None

    return digest.hexdigest()


def get_stage_signature(stage, year=2025):
    """
    Get the completion timestamp for a completed stage.
    """

    state = _load_state()

    stage_state = (
        state
        .get(str(year), {})
        .get(stage, {})
    )

    if stage_state.get("status") != "completed":
        return None

    return stage_state.get("timestamp")


def is_completed(
    stage,
    year=2025,
    fingerprint=None,
    dependencies=None
):
    """
    Check whether a pipeline stage is still valid.

    A stage is valid when:
    - it has completed successfully
    - its script has not changed
    - its dependencies have not changed
    """

    state = _load_state()

    stage_state = (
        state
        .get(str(year), {})
        .get(stage, {})
    )

    # Stage has never completed
    if stage_state.get("status") != "completed":
        return False

    # Check whether the stage script changed
    if fingerprint is not None:

        if stage_state.get("fingerprint") != fingerprint:
            return False

    # Check dependencies
    if dependencies:

        recorded_dependencies = (
            stage_state.get(
                "dependencies",
                {}
            )
        )

        for dependency in dependencies:

            current_signature = get_stage_signature(
                dependency,
                year
            )

            # Dependency has not completed
            if current_signature is None:
                return False

            # Dependency was rerun
            if (
                recorded_dependencies.get(dependency)
                != current_signature
            ):
                return False

    return True


def mark_completed(
    stage,
    year=2025,
    fingerprint=None,
    dependencies=None
):
    """
    Mark a pipeline stage as successfully completed.
    """

    state = _load_state()

    year = str(year)

    if year not in state:
        state[year] = {}

    state[year][stage] = {
        "status": "completed",

        "timestamp": datetime.now().isoformat(),

        "fingerprint": fingerprint,

        "dependencies": {
            dependency: get_stage_signature(
                dependency,
                year
            )
            for dependency in (dependencies or [])
        }
    }

    _save_state(state)


def invalidate(stage, year=2025):
    """Invalidate a previously completed stage."""

    state = _load_state()

    year = str(year)

    if year in state and stage in state[year]:
        del state[year][stage]
        _save_state(state)


def clear_cache(year=None):
    """Clear pipeline cache."""

    if year is None:

        if STATE_FILE.exists():
            STATE_FILE.unlink()

        return

    state = _load_state()

    state.pop(str(year), None)

    _save_state(state)