#!/usr/bin/env python3
import json
import base64
import requests
from typing import Tuple
from urllib.parse import urlparse
from Cryptodome.Cipher import AES

# Password per decriptare i dati ricava da reverse engineering dell'apk
APP_PASSWORD = "oAR80SGuX3EEjUGFRwLFKBTiris="

#lista delle categorie da escludere
#ex {'nba', 'nfl', 'mlb', 'nhl','wwe'}
EXCLUDED_CATEGORIES = {}

# Recupera l'url delle api che cambia continuamente
def get_sportzx_api_url():
    # Recupera Auth Token firebase simulando apk
    install_url = "https://firebaseinstallations.googleapis.com/v1/projects/sportzx-7cc3f/installations"
    install_headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "Cache-Control": "no-cache",
        "Connection": "Keep-Alive",
        "Content-Encoding": "gzip",
        "Content-Type": "application/json",
        "Host": "firebaseinstallations.googleapis.com",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 13; Redmi Note 9 Build/TD1A.221105.001)",
        "X-Android-Cert": "A0047CD121AE5F71048D41854702C52814E2AE2B",
        "X-Android-Package": "com.sportzx.live",
        "x-firebase-client": "H4sIAAAAAAAAAKtWykhNLCpJSk0sKVayio7VUSpLLSrOzM9TslIyUqoFAFyivEQfAAAA",
        "x-goog-api-key": "AIzaSyBa5qiq95T97xe4uSYlKo0Wosmye_UEf6w"
    }
    install_body = {
        "fid": "eOaLWBo8S7S1oN-vb23mkf",
        "appId": "1:446339309956:android:b26582b5d2ad841861bdd1",
        "authVersion": "FIS_v2",
        "sdkVersion": "a:18.0.0"
    }
    try:
        install_response = requests.post(install_url, json=install_body, headers=install_headers)
        install_response.raise_for_status()
        install_data = install_response.json()
        auth_token = install_data.get("authToken", {}).get("token")

        if not auth_token:
            raise ValueError("Errore estrazione auth token")
    except requests.exceptions.RequestException as e:
        print(f"Errore rercupero url api sportzx: {e}")
        return None

    config_url = "https://firebaseremoteconfig.googleapis.com/v1/projects/446339309956/namespaces/firebase:fetch"
    config_headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "Connection": "Keep-Alive",
        "Content-Type": "application/json",
        "Host": "firebaseremoteconfig.googleapis.com",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 13; Redmi Note 9 Build/TD1A.221105.001)",
        "X-Android-Cert": "A0047CD121AE5F71048D41854702C52814E2AE2B",
        "X-Android-Package": "com.sportzx.live",
        "X-Firebase-RC-Fetch-Type": "BASE/1",
        "X-Goog-Api-Key": "AIzaSyBa5qiq95T97xe4uSYlKo0Wosmye_UEf6w",
        "X-Goog-Firebase-Installations-Auth": auth_token,
        "X-Google-GFE-Can-Retry": "yes"
    }

    config_body = {
        "appVersion": "2.1",
        "firstOpenTime": "2025-11-10T16:00:00.000Z",
        "timeZone": "Europe/Rome",
        "appInstanceIdToken": auth_token,
        "languageCode": "it-IT",
        "appBuild": "12",
        "appInstanceId": "eOaLWBo8S7S1oN-vb23mkf",
        "countryCode": "IT",
        "analyticsUserProperties": {},
        "appId": "1:446339309956:android:b26582b5d2ad841861bdd1",
        "platformVersion": "33",
        "sdkVersion": "22.1.2",
        "packageName": "com.sportzx.live"
    }

    #Recupera API URL
    try:
        config_response = requests.post(config_url, json=config_body, headers=config_headers)
        config_response.raise_for_status()
        config_data = config_response.json()
        api_url = config_data.get("entries", {}).get("api_url")
        return api_url
    except requests.exceptions.RequestException as e:
        print(f"Errore recupero api url sportzx: {e}")
        return None


def generate_aes_key_iv(s: str) -> Tuple[bytes, bytes]:
    CHARSET = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+!@#$%&="
    def _u32(x: int) -> int:
        return x & 0xFFFFFFFF
    data = s.encode('utf-8')
    n = len(data)

    # Generazione chiave
    u = 0x811c9dc5
    for b in data:
        u = _u32((_u32(u) ^ b) * 0x1000193)

    out1 = bytearray()
    for i in range(16):
        b = data[i % n]
        u = _u32((_u32(u) * 0x1f) + (i ^ b))
        out1.append(CHARSET[u % len(CHARSET)])

    # Generazione IV
    u = 0x811c832a
    for b in data:
        u = _u32((_u32(u) ^ b) * 0x1000193)

    out2 = bytearray()
    idx = 0
    acc = 0
    while idx != 0x30:
        b = data[idx % n]
        u = _u32((_u32(u) * 0x1d) + (acc ^ b))
        out2.append(CHARSET[u % len(CHARSET)])
        idx += 3
        acc = _u32(acc + 7)

    return bytes(out1), bytes(out2)


def decrypt_data(b64_data: str, password: str) -> bytes:
    ct = base64.b64decode(b64_data, validate=False)
    if len(ct) == 0:
        return b""

    key, iv = generate_aes_key_iv(password)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    pt_padded = cipher.decrypt(ct)

    #PKCS#7 padding (alcune volte fallisce)
    pad = pt_padded[-1]
    return pt_padded[:-pad]


def fetch_and_decrypt(url: str):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    json_data = response.json()
    decrypted_bytes = decrypt_data(json_data['data'], APP_PASSWORD)
    return json.loads(decrypted_bytes.decode('utf-8'))


def get_sportzx_channels():
    print("Recupero API URL Sportzx...")
    SPORTZX_BASE_URL = get_sportzx_api_url()

    if not SPORTZX_BASE_URL:
        print("Errore durante il recupero dell'API URL di Sportzx")
        return []

    print(f"API URL: {SPORTZX_BASE_URL}")
    print()

    
    channels_list = []

    print("Cerca eventi Sportzx...")
    try:
        all_events = fetch_and_decrypt(f"{SPORTZX_BASE_URL}/events.json")
        eventi = [
            {'title': e.get('title'), 'id': e.get('id')}
            for e in all_events if 'cat' in e and e['cat'].lower() not in EXCLUDED_CATEGORIES
        ]
        print(f"Trovati {len(eventi)} eventi")
        print(f"Eventi esclusi per categoria: {', '.join(EXCLUDED_CATEGORIES)}")
        print()
    except Exception as e:
        print(f"Errore recupero eventi: {e}")
        return []

    print("Recupero canali per ogni evento...")
    print()

    for event in eventi:
        try:
            channels = fetch_and_decrypt(f"{SPORTZX_BASE_URL}/channels/{event['id']}.json")

            for channel in channels:
                url_completo = channel.get('link')
                link = url_completo.strip().split('|')[0]
                headers = url_completo.strip().split('|')[1] if '|' in url_completo else None
                referer=None
                origin=None
                if headers:
                    headers_parts = headers.replace('|','').split('&')
                    for part in headers_parts:
                        if part.lower().startswith('referer='):
                            referer = part.split('=', 1)[1]
                        elif part.lower().startswith('origin='):
                            origin = part.split('=', 1)[1]
                keyid = None
                key = None
                if channel.get('api'):
                    parts = channel['api'].split(':')
                    if len(parts) == 2:
                        keyid, key = parts

                channels_list.append({
                    'event_title': event['title'],
                    'event_id': event['id'],
                    'channel_title': channel.get('title'),
                    'stream_url': link,
                    'keyid': keyid,
                    'key': key,
                    'api': channel.get('api'),
                    'headers': headers,
                    'referer': referer,
                    'origin': origin,
                })

            print(f"{event['title']}: {len(channels)} canali")

        except Exception as e:
            print(f"{event['title']}: Errori - {e}")

    return channels_list


def print_channels(channels):

    if not channels:
        print("Nessun canale trovato.")
        return

    for idx, channel in enumerate(channels, 1):
        print(f"Evento #{idx}")
        print(f"  Evento:        {channel['event_title']}")
        print(f"  Canale:        {channel['channel_title']}")
        print(f"  URL:           {channel['stream_url']}")
        if channel['keyid'] and channel['key']:
            print(f"  Key ID:        {channel['keyid']}")
            print(f"  Key:           {channel['key']}")
        if channel['headers']:
            print(f"  Headers:       {channel['headers']}")
        if channel['referer']:
            print(f"  Referer:       {channel['referer']}")
        if channel['origin']:
            print(f"  Origin:        {channel['origin']}")
        print()


if __name__ == "__main__":
    try:
        channels = get_sportzx_channels()
        print_channels(channels)
    except Exception as e:
        print(f"\nErrore: {e}")
