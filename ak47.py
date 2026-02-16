import base64
import gzip
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import unpad
import requests
import json
from dataclasses import dataclass
from typing import List, Optional

BASE_URL = ""
AES_KEY = b"l9K5bT5xC1wP7pK1"
AES_IV = b"k5K4nN7oU8hL6l19"


@dataclass
class StreamLink:
    name: str
    url: str
    headers: List[str]
    mpd_key: str
    tokenApi: Optional[str] = None


@dataclass
class Event:
    category: str
    event_name: str
    event_logo: str
    team_a_name: str
    team_b_name: str
    team_a_flag: str
    team_b_flag: str
    date: str
    time: str
    end_date: str
    end_time: str
    visible: bool
    priority: int
    links_path: str
    stream_links: Optional[List[StreamLink]] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            category=data.get('category', ''),
            event_name=data.get('eventName', ''),
            event_logo=data.get('eventLogo', ''),
            team_a_name=data.get('teamAName', ''),
            team_b_name=data.get('teamBName', ''),
            team_a_flag=data.get('teamAFlag', ''),
            team_b_flag=data.get('teamBFlag', ''),
            date=data.get('date', ''),
            time=data.get('time', ''),
            end_date=data.get('end_date', ''),
            end_time=data.get('end_time', ''),
            visible=data.get('visible', False),
            priority=data.get('priority', 0),
            links_path=data.get('links', ''),
            stream_links=None
        )

    def __str__(self):
        return f"{self.event_name}: {self.team_a_name} vs {self.team_b_name}"


def decrypt_aes_cbc(encrypted_base64: str) -> str:
    try:
        encrypted_data = base64.b64decode(encrypted_base64)
        cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
        decrypted = unpad(cipher.decrypt(encrypted_data), AES.block_size)
        return decrypted.decode('utf-8')
    except Exception:
        return ""


def parse_events(app_decoded: str) -> List[Event]:
    try:
        events_array = json.loads(app_decoded)
        events = []

        for item in events_array:
            event_str = item.get("event", "{}")
            event_data = json.loads(event_str)
            events.append(Event.from_dict(event_data))

        return events
    except json.JSONDecodeError:
        return []


def get_link_headers(link: str) -> List[str]:
    headers = []
    parts = link.split("|")
    if len(parts) > 1:
        for part in parts[1:]:
            if "=" in part:
                key, value = part.split("=", 1)
                headers.append(f"{key.strip()}={value.strip()}")
    return headers

def fetch_links(event: Event) -> List[StreamLink]:
    if not event.links_path:
        return []

    try:
        url = f"{BASE_URL}/{event.links_path}"
        response = requests.get(url, timeout=10)
        decoded_links = decrypt_aes_cbc(response.text)

        if not decoded_links:
            return []

        links_array = json.loads(decoded_links)
        stream_links = []

        for link_data in links_array:
            channel = link_data.get("name", "")
            link = link_data.get("link", "").split("|")[0]
            headers = get_link_headers(link_data.get("link", "")) 
            api = link_data.get("api", "")
            mpd_key = api
            tokenApi = link_data.get("tokenApi", "")
            


            if channel and link:
                stream_links.append(StreamLink(name=channel, url=link, headers=headers, mpd_key=mpd_key, tokenApi=tokenApi))

        return stream_links
    except Exception:
        return []


def get_live_matches() -> List[Event]:
    try:
        response = requests.get(f"{BASE_URL}events.txt", timeout=10)
        app_decoded = decrypt_aes_cbc(response.text)

        if not app_decoded:
            return []

        events = parse_events(app_decoded)
        return events
    except Exception:
        return []


def get_visible_events(events: List[Event]) -> List[Event]:
    return [e for e in events if e.visible]


def get_events_by_category(events: List[Event], category: str) -> List[Event]:
    return [e for e in events if e.category.lower() == category.lower()]


def get_base_url():
    url = "https://firebaseinstallations.googleapis.com/v1/projects/ak47-sports/installations"
    
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "Cache-Control": "no-cache",
        "Connection": "Keep-Alive",
        "Content-Encoding": "gzip",
        "Content-Type": "application/json",
        "Host": "firebaseinstallations.googleapis.com",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 13; Redmi Note 9 Build/TD1A.221105.001)",
        "X-Android-Cert": "0F1EF51278AA9A12884F717F1310F0ECABF9F685",
        "X-Android-Package": "app.aksports.live",
        "x-firebase-client": "H4sIAAAAAAAAAKtWykhNLCpJSk0sKVayio7VUSpLLSrOzM9TslIyUqoFAFyivEQfAAAA",
        "x-goog-api-key": "AIzaSyCOhPo6X5o8517oC_tFtH_L8ka3ElacTu0"
    }
    
    body = {
        "fid": "c_iFxQ-DTGaXn1HmJppfZO",
        "appId": "1:987682933046:android:b0d2f52255416b34cb0b97",
        "authVersion": "FIS_v2",
        "sdkVersion": "a:18.0.0"
    }
    
    compressed_body = gzip.compress(json.dumps(body).encode('utf-8'))
    
    response = requests.post(url, headers=headers, data=compressed_body)
    token = response.json().get("authToken", {}).get("token", "")

    url = "https://firebaseremoteconfig.googleapis.com/v1/projects/987682933046/namespaces/firebase:fetch"
    
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "Connection": "Keep-Alive",
        "Content-Type": "application/json",
        "Host": "firebaseremoteconfig.googleapis.com",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 13; Redmi Note 9 Build/TD1A.221105.001)",
        "X-Android-Cert": "0F1EF51278AA9A12884F717F1310F0ECABF9F685",
        "X-Android-Package": "app.aksports.live",
        "X-Firebase-RC-Fetch-Type": "BASE/1",
        "X-Goog-Api-Key": "AIzaSyCOhPo6X5o8517oC_tFtH_L8ka3ElacTu0",
        "X-Goog-Firebase-Installations-Auth": token,
        "X-Google-GFE-Can-Retry": "yes"
    }
    
    body = {
        "appVersion": "1.2",
        "firstOpenTime": "2026-02-16T21:00:00.000Z",
        "timeZone": "Europe/Rome",
        "appInstanceIdToken": token,
        "languageCode": "it-IT",
        "appBuild": "3",
        "appInstanceId": "c_iFxQ-DTGaXn1HmJppfZO",
        "countryCode": "IT",
        "analyticsUserProperties": {},
        "appId": "1:987682933046:android:b0d2f52255416b34cb0b97",
        "platformVersion": "33",
        "sdkVersion": "22.0.0",
        "packageName": "app.aksports.live"
    }
    
    response = requests.post(url, headers=headers, json=body)
    return response.json().get("entries", {}).get("api_url", {})


if __name__ == "__main__":
    BASE_URL = get_base_url()
    print(f"Base URL: {BASE_URL}")
    print("=" * 80)
    print("PARSING EVENTI LIVE")
    print("=" * 80)
    print()

    events = get_live_matches()

    visible = get_visible_events(events)

    for idx, event in enumerate(visible, 1):
        if not 'Football' in event.category:
            continue

        stream_links = fetch_links(event)
        event.stream_links = stream_links

        if not stream_links or stream_links[0].url == "https://no.link":
            continue
        print(f"{event}")
        print(f"   Categoria: {event.category}")
        print(f"   Data/Ora: {event.date} {event.time}")

        if stream_links:
            print(f"   Stream disponibili: {len(stream_links)}")
            for i, link in enumerate(stream_links, 1):
                print(f"     {i}. {link.name}")
                print(f"        URL: {link.url}")
                if link.headers:
                    print(f"        Headers: {', '.join(link.headers)}")
                if link.mpd_key:
                    print(f"        MPD Key: {link.mpd_key}")
        else:
            print("   Nessuno stream disponibile")
