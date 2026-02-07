import re
import urllib.parse
import requests
import json
import time
import base64

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
                    status = event.get('status', 'unknown')

                    if status == 'offline' or status == 'finished':
                        continue
                    
                    
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
        js = js.replace("\\'", "'").replace('\\"', '"')
        if not js:
            return None

        deob_result = auto_deobfuscate_js(js)

        url = deob_result.get('concatenations', [])[1]['decoded'] if len(deob_result.get('concatenations', [])) > 1 else ''
        #print(deob_result)
        #return find_stream_url(js)
        return {'url': url} 
    except:
        return None
    
def get_streams(channels):
    """
    Recupera gli stream dai canali forniti
    """
    if not channels:
        print("Nessun canale trovato")
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


def normalize_js_code(js_code: str) -> str:
    # pulizia js
    js_code = js_code.replace("\\'", "'").replace('\\"', '"').replace("\'", "'")
    js_code = re.sub(r'\s+', ' ', js_code)
    return js_code

def pum_decode(s: str) -> str:
    s = s.replace('-', '+').replace('_', '/')
    while len(s) % 4 != 0:
        s += '='
    try:
        raw = base64.b64decode(s)
        return raw.decode('utf-8')
    except Exception:
        try:
            raw = base64.b64decode(s)
            return raw.decode('latin-1')
        except Exception:
            return None

def find_decode_function(js_code: str) -> str:
    #print(js_code)
    # pattern di ricerca di fuzioni che usano atob
    patterns = [
        r'function\s+(\w+)\s*\(\s*str\s*\)\s*\{[^}]{0,500}atob',
        r'function\s+(\w+)\s*\(\s*\w+\s*\)\s*\{[^}]{0,500}atob',
        r'(?:const|let|var)\s+(\w+)\s*=\s*function\s*\(\s*str\s*\)\s*\{[^}]{0,500}atob',
        r'function\s+(\w+)\s*\([^)]+\)\s*\{(?:[^}]|[\r\n]){0,500}(?:replace.*atob|atob.*replace)',
    ]

    for pattern in patterns:
        match = re.search(pattern, js_code, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1)

    return None

def extract_base64_strings(js_code: str) -> dict:
    pattern = r'["\']([A-Za-z0-9_\-+=]{8,})["\']' 
    matches = re.findall(pattern, js_code)

    base64_dict = {}
    for match in matches:
        decoded = pum_decode(match)
        #print(decoded)
        if decoded:
            if all(ord(c) < 128 and (c.isprintable() or c in '\\n\\r\\t') for c in decoded):
                base64_dict[match] = decoded

    return base64_dict

def find_variable_assignments(js_code: str) -> dict:
    pattern = r'(?:const|let|var)\s+(\w+)\s*=\s*["\']([^"\']+)["\']'
    matches = re.findall(pattern, js_code)
    return {name: value for name, value in matches}

def find_concatenations(js_code: str, var_dict: dict, decode_func_name: str) -> list:
    pattern = rf'(?:const|let|var)\s+(\w+)\s*=\s*((?:{decode_func_name}\([^)]+\)\s*\+?\s*)+);'
    matches = re.findall(pattern, js_code, re.MULTILINE | re.DOTALL)

    results = []
    for var_name, concat_expr in matches:
        func_calls = re.findall(rf'{decode_func_name}\((\w+)\)', concat_expr)

        decoded_parts = []
        for arg in func_calls:
            if arg in var_dict:
                decoded = pum_decode(var_dict[arg])
                if decoded:
                    decoded_parts.append(decoded)

        if decoded_parts:
            full_string = ''.join(decoded_parts)
            results.append({
                'variable': var_name,
                'parts': func_calls,
                'decoded': full_string
            })

    return results

def auto_deobfuscate_js(js_code: str) -> dict:

    js_code = normalize_js_code(js_code)
    decode_func_name = find_decode_function(js_code)

    if not decode_func_name:
        return {
            'error': 'Nessuna funzione di decode trovata',
            'decode_function': None,
            'variables': {},
            'concatenations': [],
            'all_base64_decoded': {}
        }

    var_dict = find_variable_assignments(js_code)
    concatenations = find_concatenations(js_code, var_dict, decode_func_name)
    all_base64 = extract_base64_strings(js_code)

    return {
        'decode_function': decode_func_name,
        'variables': var_dict,
        'concatenations': concatenations,
        'all_base64_decoded': all_base64
    }

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
    print("Le chiamate all' url della stream devono avere header Origin e Referer = https://cdn-live.tv/")
    get_sports()
    get_live_tv()