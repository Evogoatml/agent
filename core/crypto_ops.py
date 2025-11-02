from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
from Crypto.Hash import Whirlpool
try:
    from twofish import Twofish
except Exception:
    Twofish = None

def aes_gcm_encrypt(plaintext: bytes, key: bytes, iv: bytes):
    from Crypto.Cipher import AES
    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    ct, tag = cipher.encrypt_and_digest(plaintext)
    return ct, tag

def aes_cbc_encrypt(plaintext: bytes, key: bytes, iv: bytes):
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(plaintext, 16))

def aes_cbc_decrypt(ciphertext: bytes, key: bytes, iv: bytes):
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(ciphertext), 16)

def whirlpool_hash(data: bytes) -> str:
    h = Whirlpool.new()
    h.update(data)
    return h.hexdigest()

def twofish_encrypt(plaintext: bytes, key: bytes):
    if Twofish is None:
        raise RuntimeError("twofish package not available")
    t = Twofish(key[:16])  # Twofish block cipher; using 128-bit key slice
    # ECB one-block example (demo)
    block = plaintext[:16].ljust(16, b"\0")
    return t.encrypt(block)
