import hashlib

class SecurityEnclave:
    def encrypt(self, data):
        return hashlib.sha256(data.encode()).hexdigest()

    def decrypt(self, data):
        return f"<decrypted hash: {data[:12]}>"
