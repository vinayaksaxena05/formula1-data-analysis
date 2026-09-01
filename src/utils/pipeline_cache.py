import json
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
STATE_FILE = ROOT_DIR/".pipeline"/"state.json"

def _load_state():
    """Loading pipeline state from disk."""
    
    if not STATE_FILE.exists():
        return {}
    
    try:
        with open(STATE_FILE, "r", encoding="UTF-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return {}

def _save_state(state):
    """Save pipeline state to the disk"""
    
    STATE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )
    
    temp_file = STATE_FILE.with_suffix(".tmp")
    
    with open(temp_file, "w", encoding="UTF-8") as file:
        json.dump(state, file, indent=4)
        
    temp_file.replace(STATE_FILE)

def is_completed(stage, year=2025):
    """
    Check whether a pipeline stage has already completed
    successfully for a given year.
    """

    state = _load_state()

    return (
        str(year) in state
        and stage in state[str(year)]
        and state[str(year)][stage].get("status") == "completed"
    )


def mark_completed(stage, year=2025):
    """Mark a pipeline stage as successfully completed."""

    state = _load_state()

    year = str(year)

    if year not in state:
        state[year] = {}

    state[year][stage] = {
        "status": "completed",
        "timestamp": datetime.now().isoformat()
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