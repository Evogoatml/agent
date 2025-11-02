# core/key_store.py
import os, json, secrets, base64
from typing import Dict, Optional
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import scrypt

_AKS_MAGIC = b"AKS1"  # Api Key Store v1
_DEFAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "api_keys.enc")

class KeyStore:
    def __init__(self, path: str = _DEFAULT_PATH):
        self.path = path
        self._cache: Dict[str, str] = {}
        self._loaded = False

    # ---- crypto helpers ----
    @staticmethod
    def _kdf(passphrase: str, salt: bytes) -> bytes:
        # scrypt: N=2**15, r=8, p=1 -> ~32MB mem; adjust if needed
        return scrypt(passphrase.encode("utf-8"), salt=salt, key_len=32, N=1 << 15, r=8, p=1)

    @staticmethod
    def _enc(passphrase: str, data: bytes) -> bytes:
        salt = secrets.token_bytes(16)
        key = KeyStore._kdf(passphrase, salt)
        nonce = secrets.token_bytes(12)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        ct, tag = cipher.encrypt_and_digest(data)
        return _AKS_MAGIC + salt + nonce + ct + tag

    @staticmethod
    def _dec(passphrase: str, blob: bytes) -> bytes:
        if not blob or blob[:4] != _AKS_MAGIC:
            raise ValueError("Invalid keystore file.")
        salt = blob[4:20]
        nonce = blob[20:32]
        tag = blob[-16:]
        ct = blob[32:-16]
        key = KeyStore._kdf(passphrase, salt)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ct, tag)

    # ---- file io ----
    def _ensure_parent(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def load(self, passphrase: Optional[str] = None) -> None:
        if self._loaded:
            return
        if passphrase is None:
            passphrase = os.environ.get("KEYSTORE_PASSPHRASE")
        if not passphrase:
            # Empty store in memory; write only on first set with provided pass
            self._cache = {}
            self._loaded = True
            return
        if not os.path.exists(self.path):
            self._ensure_parent()
            self._cache = {}
            self._loaded = True
            return
        with open(self.path, "rb") as f:
            plain = self._dec(passphrase, f.read())
        self._cache = json.loads(plain.decode("utf-8"))
        self._loaded = True

    def _save(self, passphrase: str):
        self._ensure_parent()
        blob = self._enc(passphrase, json.dumps(self._cache).encode("utf-8"))
        tmp = self.path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(blob)
        os.replace(tmp, self.path)

    # ---- public API ----
    def set(self, name: str, value: str, passphrase: Optional[str] = None) -> None:
        if passphrase is None:
            passphrase = os.environ.get("KEYSTORE_PASSPHRASE")
        if not passphrase:
            raise RuntimeError("Missing passphrase; set KEYSTORE_PASSPHRASE or pass --pass.")
        self.load(passphrase=passphrase)
        self._cache[name] = value
        self._save(passphrase)

    def get(self, name: str, default: Optional[str] = None, passphrase: Optional[str] = None) -> Optional[str]:
        self.load(passphrase=passphrase)  # passphrase optional for reading existing cache
        return self._cache.get(name, default)

    def items(self) -> Dict[str, str]:
        self.load()
        return dict(self._cache)

# Singleton
key_store = KeyStore()
