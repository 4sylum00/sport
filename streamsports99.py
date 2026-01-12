import re
import urllib.parse
import requests
import json
import time

def convert_base(s, base):
    result = 0
    for i, digit in enumerate(reversed(s)):
        result += int(digit) * (base ** i)
    return result

def decode_obfuscated_js(html):
    #html.find('}("') + 2
    start = html.find('}("') + 3
    if start == 2:
        return None

    end = html.find('",', start)
    encoded = html[start:end]

    params_pos = end + 2
    params = html[params_pos:params_pos+100]
    m = re.search(r'(\d+),\s*"([^"]+)",\s*(\d+),\s*(\d+),\s*(\d+)', params)

    if not m:
        return None

    charset = m.group(2)
    offset = int(m.group(3))
    base = int(m.group(4))

    decoded = ""
    parts = encoded.split(charset[base])

    for part in parts:
        if part:
            temp = part
            for idx, c in enumerate(charset):
                temp = temp.replace(c, str(idx))

            val = convert_base(temp, base)
            decoded += chr(val - offset)

    return urllib.parse.unquote(decoded)

def find_stream_url(js_code):
    pattern = r'["\']([^"\']*index\.m3u8\?token=[^"\']+)["\']'
    match = re.search(pattern, js_code)

    if not match:
        return None

    url = match.group(1)
    info = {'url': url}

    return info

def fetch_channels_live_tv(api_url, headers=None):
    try:
        r = requests.get(api_url, headers=headers, timeout=120)
        r.raise_for_status()
        data = r.json()
        return data.get('channels', [])
    except:
        return None

def fetch_channels_sports(api_url, headers=None):
    try:
        r = requests.get(api_url, headers=headers, timeout=120)
        r.raise_for_status()
        data = r.json()
        
        flattened_channels = []
        
        if 'cdn-live-tv' in data:
            for sport_category, events in data['cdn-live-tv'].items():
                if not isinstance(events, list):
                    continue
                for event in events:
                    tournament = event.get('tournament', '')
                    home_team = event.get('homeTeam', '')
                    away_team = event.get('awayTeam', '')
                    
                    match_info = f"{tournament} - {home_team} vs {away_team}"
                    
                    for channel in event.get('channels', []):
                        flattened_channel = {
                            'name': f"{match_info} - {channel['channel_name']}",
                            'channel_name': channel['channel_name'],
                            'code': channel['channel_code'],
                            'url': channel['url'],
                            'image': channel.get('image', ''),
                            'tournament': tournament,
                            'home_team': home_team,
                            'away_team': away_team,
                            'match_info': match_info,
                            'sport_category': sport_category,
                            'status': event.get('status', 'unknown'),
                            'start': event.get('start', ''),
                            'time': event.get('time', '')
                        }
                        flattened_channels.append(flattened_channel)
        
        return flattened_channels
    except Exception as e:
        print(f"Errore nel parsing: {e}")
        return None

def get_stream_url(player_url):
    try:
        headers = {'Referer': 'https://streamsports99.su/'}
        r = requests.get(player_url, headers=headers, timeout=15)
        r.raise_for_status()

        js = decode_obfuscated_js(r.text)
        if not js:
            return None

        return find_stream_url(js)
    except:
        return None
    
def get_streams(channels):
    """
    Recupera gli stream dai canali forniti
    """
    if not channels:
        print("Errore recupero canali")
        return

    print(f"Trovati {len(channels)} canali\n")

    results = []

    for i, ch in enumerate(channels, 1):
        #if ch['code'] != 'it': continue

        if ch['status'] == 'offline':
            continue
        #forse si puo comunque provare a prendere lo stream anche se offline

        stream = get_stream_url(ch['url'])
        if not stream:
            continue
        
        print(f"{i}. {ch['name']} ({ch['code']}) - {ch['status']}")
        print(f"   Stream: {stream['url']}")       

def get_live_tv():
    """
    Recupera stream canali TV Live
    """
    api_live_tv = "https://api.cdn-live.tv/api/v1/channels/?user=streamsports99&plan=vip"

    print(f"Recupero canali da {api_live_tv}\n")
    get_streams(fetch_channels_live_tv(api_live_tv))

def get_sports():
    """
    Recupera stream eventi sportivi
    """
    api_sports = "https://api.cdn-live.tv/api/v1/events/sports/?user=streamsports99&plan=vip"

    print(f"Recupero canali da {api_sports}\n")
    get_streams(fetch_channels_sports(api_sports))

if __name__ == "__main__":
    get_sports()
    get_live_tv()
    
