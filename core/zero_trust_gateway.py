import os
import json
import base64
from Crypto.Cipher import AES
from twofish import Twofish
from Crypto.Hash import Whirlpool
from Crypto.Random import get_random_bytes

class ZeroTrustGateway:
    """
    Secure gateway providing zero-trust encryption layers:
      1. AES-256-GCM for authenticated encryption
      2. Twofish-256 outer shield for transport obfuscation
      3. Whirlpool-512 for integrity verification
    """

    def __init__(self, aes_key=None, twofish_key=None):
        self.aes_key = aes_key or get_random_bytes(32)
        self.twofish_key = twofish_key or get_random_bytes(32)

    def seal(self, data: dict) -> str:
        """Encrypt and wrap data with AES + Twofish + Whirlpool."""
        raw = json.dumps(data).encode()

        # --- AES Encryption ---
        aes_iv = get_random_bytes(12)
        aes_cipher = AES.new(self.aes_key, AES.MODE_GCM, nonce=aes_iv)
        aes_ct, aes_tag = aes_cipher.encrypt_and_digest(raw)
        aes_packet = aes_iv + aes_tag + aes_ct

        # --- Twofish Encryption (outer layer) ---
        tf_iv = get_random_bytes(16)
        tf_cipher = Twofish.new(self.twofish_key, Twofish.MODE_CFB, iv=tf_iv)
        tf_ct = tf_cipher.encrypt(aes_packet)

        # --- Whirlpool Hash for Integrity ---
        wh = Whirlpool.new()
        wh.update(tf_ct)
        checksum = wh.hexdigest()

        payload = {
            "iv": base64.b64encode(tf_iv).decode(),
            "data": base64.b64encode(tf_ct).decode(),
            "hash": checksum
        }
        return base64.b64encode(json.dumps(payload).encode()).decode()

    def unseal(self, packet: str) -> dict:
        """Decrypt and verify zero-trust wrapped data."""
        payload = json.loads(base64.b64decode(packet).decode())
        tf_iv = base64.b64decode(payload["iv"])
        tf_ct = base64.b64decode(payload["data"])
        checksum = payload["hash"]

        # --- Verify Whirlpool ---
        wh = Whirlpool.new()
        wh.update(tf_ct)
        if wh.hexdigest() != checksum:
            raise ValueError("Integrity check failed (Whirlpool mismatch)")

        # --- Twofish Decrypt ---
        tf_cipher = Twofish.new(self.twofish_key, Twofish.MODE_CFB, iv=tf_iv)
        aes_packet = tf_cipher.decrypt(tf_ct)

        # --- AES Decrypt ---
        aes_iv = aes_packet[:12]
        aes_tag = aes_packet[12:28]
        aes_ct = aes_packet[28:]
        aes_cipher = AES.new(self.aes_key, AES.MODE_GCM, nonce=aes_iv)
        data = aes_cipher.decrypt_and_verify(aes_ct, aes_tag)

        return json.loads(data.decode())

# Example usage:
if __name__ == "__main__":
    zt = ZeroTrustGateway()
    original = {"message": "Adaptive Intelligence Core secure channel established"}
    sealed = zt.seal(original)
    print("Sealed:", sealed)
    unsealed = zt.unseal(sealed)
    print("Unsealed:", unsealed)
