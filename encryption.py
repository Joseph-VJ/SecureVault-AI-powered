import os
import math
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import psutil

CHUNK_SIZE = 1024 * 1024  # 1MB default, adjustable

def measure_data_perplexity(data: bytes) -> float:
    if not data:
        return 0.0
    freq = {}
    for byte in data:
        freq[byte] = freq.get(byte, 0) + 1
    total = len(data)
    entropy = 0.0
    for count in freq.values():
        p = count / total
        entropy -= p * math.log2(p)
    return 2 ** entropy

def encrypt_data_fernet(key: bytes, data: bytes) -> bytes:
    return Fernet(key).encrypt(data)

def decrypt_data_fernet(key: bytes, data: bytes) -> bytes:
    return Fernet(key).decrypt(data)

def encrypt_data_aes(key: bytes, data: bytes, mode: str = "CFB") -> bytes:
    iv = os.urandom(16)
    if mode == "CFB":
        cipher = Cipher(algorithms.AES(key), modes.CFB(iv))
    elif mode == "GCM":
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv))
    else:
        raise ValueError("Unsupported AES mode")
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(data) + encryptor.finalize()
    if mode == "GCM":
        return iv + encryptor.tag + ciphertext  # Include GCM tag for integrity
    return iv + ciphertext

def decrypt_data_aes(key: bytes, data: bytes, mode: str = "CFB") -> bytes:
    if mode == "CFB":
        iv = data[:16]
        cipher = Cipher(algorithms.AES(key), modes.CFB(iv))
        decryptor = cipher.decryptor()
        return decryptor.update(data[16:]) + decryptor.finalize()
    elif mode == "GCM":
        iv = data[:16]
        tag = data[16:32]
        ciphertext = data[32:]
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag))
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()
    else:
        raise ValueError("Unsupported AES mode")

def derive_key_from_password(password: str, salt: bytes, key_length: int) -> bytes:
    """Derive a key from a password using PBKDF2HMAC."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=key_length,
        salt=salt,
        iterations=100000,  # Strong iteration count for security
    )
    return kdf.derive(password.encode())

def encrypt_file_in_chunks(encrypt_func, key, in_path, out_path, progress_tracker=None):
    file_size = os.path.getsize(in_path)
    processed = 0
    # Optimize chunk size based on available memory and file size
    available_memory = psutil.virtual_memory().available
    chunk_size = min(CHUNK_SIZE, max(1024 * 1024, available_memory // 4))

    with open(in_path, "rb") as fin, open(out_path, "wb") as fout:
        while True:
            chunk = fin.read(chunk_size)
            if not chunk:
                break
            encrypted = encrypt_func(key, chunk)
            fout.write(len(encrypted).to_bytes(4, "big"))
            fout.write(encrypted)
            processed += len(chunk)
            if progress_tracker:
                progress_tracker.update_progress(processed, file_size)

def decrypt_file_in_chunks(decrypt_func, key, in_path, out_path, progress_tracker=None):
    file_size = os.path.getsize(in_path)
    processed = 0

    with open(in_path, "rb") as fin, open(out_path, "wb") as fout:
        while True:
            length_bytes = fin.read(4)
            if not length_bytes:
                break
            enc_len = int.from_bytes(length_bytes, "big")
            enc_data = fin.read(enc_len)
            decrypted = decrypt_func(key, enc_data)
            fout.write(decrypted)
            processed += enc_len
            if progress_tracker:
                progress_tracker.update_progress(processed, file_size)

def encrypt_file_with_password(password: str, in_path: str, out_path: str, method: str = "Fernet", progress_tracker=None):
    salt = os.urandom(16)
    if method == "Fernet":
        key = derive_key_from_password(password, salt, 32)
        encrypt_func = encrypt_data_fernet
    elif method.startswith("AES"):
        key_length = 32 if "256" in method else 24 if "192" in method else 16
        key = derive_key_from_password(password, salt, key_length)
        mode = "GCM" if "GCM" in method else "CFB"
        encrypt_func = lambda data: encrypt_data_aes(key, data, mode)
    else:
        raise ValueError("Unsupported method")

    # Header: magic (4 bytes), method (1 byte), salt (16 bytes)
    method_byte = {'Fernet': 'F', 'AES-128': 'A', 'AES-192': 'B', 'AES-256': 'C', 'AES-256-GCM': 'G'}.get(method, 'F')
    header = b'SVEP' + method_byte.encode() + salt
    with open(out_path, "wb") as fout:
        fout.write(header)
    encrypt_file_in_chunks(encrypt_func, key, in_path, out_path, progress_tracker)

def decrypt_file_with_password(password: str, in_path: str, out_path: str, progress_tracker=None):
    with open(in_path, "rb") as fin:
        magic = fin.read(4)
        if magic != b'SVEP':
            raise ValueError("Invalid file format or not password-encrypted")
        method_byte = fin.read(1).decode()
        salt = fin.read(16)
        method_map = {'F': ('Fernet', 32, decrypt_data_fernet),
                      'A': ('AES-128', 16, lambda data: decrypt_data_aes(key, data, "CFB")),
                      'B': ('AES-192', 24, lambda data: decrypt_data_aes(key, data, "CFB")),
                      'C': ('AES-256', 32, lambda data: decrypt_data_aes(key, data, "CFB")),
                      'G': ('AES-256-GCM', 32, lambda data: decrypt_data_aes(key, data, "GCM"))}
        if method_byte not in method_map:
            raise ValueError("Unsupported method in file header")
        method, key_length, decrypt_func = method_map[method_byte]
        key = derive_key_from_password(password, salt, key_length)

    decrypt_file_in_chunks(decrypt_func, key, in_path, out_path, progress_tracker)