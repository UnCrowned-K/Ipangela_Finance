"""
Server-side storage for per-user optimizer state.

Variables and budget are persisted as a JSON file per user instead of in the
client-side session cookie, keeping the signed cookie small and the data out
of the browser.
"""

import json
import os
from typing import Any, Dict, List, Optional

from flask import current_app, session

_UNSET = object()


def _empty_state() -> Dict[str, Any]:
    """Return a fresh, isolated empty state (no shared mutable defaults)."""
    return {'budget': None, 'variables': []}


def _folder(user_id: Optional[str]) -> str:
    root = current_app.config['OPTIMIZER_STATE_FOLDER']
    return os.path.join(root, str(user_id or 'anonymous'))


def _path(user_id: Optional[str]) -> str:
    return os.path.join(_folder(user_id), 'state.json')


def load_state_for(user_id: Optional[str]) -> Dict[str, Any]:
    """Load the persisted state dict for a user (never raises)."""
    path = _path(user_id)
    if not os.path.exists(path):
        return _empty_state()
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except (OSError, ValueError):
        return _empty_state()
    if not isinstance(data, dict):
        return _empty_state()
    return {
        'budget': data.get('budget'),
        'variables': data.get('variables') or [],
    }


def save_state_for(user_id: Optional[str], budget=_UNSET, variables=_UNSET) -> Dict[str, Any]:
    """Persist a user's optimizer state, returning the new state."""
    state = load_state_for(user_id)
    if budget is not _UNSET:
        state['budget'] = budget
    if variables is not _UNSET:
        state['variables'] = variables or []
    path = _path(user_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(state, f)
    return state


def clear_state_for(user_id: Optional[str]) -> None:
    """Remove a user's optimizer state file, if any."""
    try:
        os.remove(_path(user_id))
    except OSError:
        pass


def _me() -> Optional[str]:
    return session.get('user_id')


def get_budget(default: Optional[int] = None) -> Any:
    """Return the current user's budget or ``default`` when unset."""
    budget = load_state_for(_me())['budget']
    return default if budget is None else budget


def set_budget(budget: int) -> None:
    save_state_for(_me(), budget=budget)


def get_variables() -> List[Dict[str, Any]]:
    """Return the current user's variables list."""
    return load_state_for(_me())['variables']


def set_variables(variables: List[Dict[str, Any]]) -> None:
    save_state_for(_me(), variables=variables)


def clear_state() -> None:
    """Reset the current user's optimizer state."""
    clear_state_for(_me())