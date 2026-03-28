from datetime import datetime

# Estado en memoria. Single-process obligatorio.
# Reiniciar el proceso borra todas las conversaciones activas.
_conversations: dict[str, dict] = {}

_DEFAULT = {"state": "IDLE", "current_list": [], "timestamp": None}


def _ensure(phone: str) -> None:
    if phone not in _conversations:
        _conversations[phone] = {"state": "IDLE", "current_list": [], "timestamp": None}


def get_state(phone: str) -> dict:
    _ensure(phone)
    return _conversations[phone]


def set_state(phone: str, state: str) -> None:
    _ensure(phone)
    _conversations[phone]["state"] = state
    _conversations[phone]["timestamp"] = datetime.now()


def get_lista(phone: str) -> list:
    _ensure(phone)
    return _conversations[phone]["current_list"]


def set_lista(phone: str, lista: list) -> None:
    _ensure(phone)
    _conversations[phone]["current_list"] = lista


def reset(phone: str) -> None:
    _conversations[phone] = {"state": "IDLE", "current_list": [], "timestamp": None}
