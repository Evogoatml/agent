# core/bootstrap.py
import os
from core.key_store import key_store

KNOWN_EXPORTS = ("APILAYER_KEY", "RAPIDAPI_KEY", "HF_KEY")

def init_runtime() -> None:
    """
    Loads the encrypted keystore using KEYSTORE_PASSPHRASE.
    Exports known keys into process env so any lib can access them.
    """
    key_store.load()
    for name in KNOWN_EXPORTS:
        val = key_store.get(name)
        if val:
            os.environ[name] = val

def get_key(name: str) -> str:
    v = key_store.get(name)
    if not v:
        raise RuntimeError(f"Missing key: {name}")
    return v
