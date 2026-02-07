import requests
import base64
from Cryptodome.Cipher import AES
import hashlib
import json

def decrypt_payload(payload_b64, key_string):
    key = hashlib.sha256(key_string.encode('utf-8')).digest()
    payload_bytes = base64.b64decode(payload_b64)
    iv = payload_bytes[:16]
    ciphertext = payload_bytes[16:]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(ciphertext)
    padding_length = decrypted[-1]
    plaintext = decrypted[:-padding_length]
    try:
        plaintext_str = plaintext.decode('utf-8')
        return plaintext_str
    except UnicodeDecodeError:
        print("errore durante la decodifica")
        return None
def fetch(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text.strip()
    except requests.RequestException as e:
        print(f"errore durante il fetch {e}")
        return None
    
def fetch_and_decrypt(url, key_string):
    try:
        payload_b64 = fetch(url)
        decrypted_content = decrypt_payload(payload_b64, key_string)
        return decrypted_content
    except requests.RequestException as e:
        print(f"errore durante il fetch {e}")
        return None
    except Exception as e:
        print(f"errore: {e}")
        return None


if __name__ == "__main__":
    print("-"*80 + "SKY\n")   
    print(json.loads(fetch("https://sport.alemagno1994alex.workers.dev/"))[0].get("text", ""))

    print("="*40 + "EVENTI"+ "="*40+ "\n")
    print(fetch_and_decrypt("https://eventi.alemagno1994alex.workers.dev/","IPXfJrt68qLZ3J9T4UCU78mS2RzuSvUrt3FKCzyqkDOaw3gF93oeduLByciL"))

    
  

