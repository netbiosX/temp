from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Util.Padding import pad
import sys

def derive_key(password: bytes, key_size=16):
    hasher = SHA256.new()
    hasher.update(password)
    return hasher.digest()[:key_size]

def encrypt_shellcode(input_path, output_path, password):
    with open(input_path, 'rb') as f:
        shellcode = f.read()

    key = derive_key(password.encode())
    cipher = AES.new(key, AES.MODE_ECB)
    encrypted = cipher.encrypt(pad(shellcode, AES.block_size))

    with open(output_path, 'wb') as f:
        f.write(encrypted)

    print(f"[+] Shellcode encrypted to: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python encrypt_shellcode.py <raw_shellcode.bin> <output.bin> <16_char_key>")
        sys.exit(1)

    encrypt_shellcode(sys.argv[1], sys.argv[2], sys.argv[3])
