import re
import requests
from urllib.parse import urlparse, parse_qs

XROMAPIURL = "https://config.e-droid.net/srv/config.php?v=197&vname=9.8&idapp=3579183&idusu=0&codggp=0&am=0&idlit=&paenv=1&pa=IT&pn=xromtv.italia&fus=01&01=00000000&aid=41fa0c253a5ef255"
XROMSKYOPAGEURL = "https://html.e-droid.net/html/get_html.php?ida=3579183&ids=37001286&fum=1769767566"

DECODEMAP = {
    ' ': '2', '!': 'g', '#': 'h', '$': 'Y', '%': 'f', '&': 'X', '(': 'F', '+': 'Q',
    ',': '_', '-': '4', '/': 'z', '0': 'M', '1': '1', '3': '0', '4': 'U', '5': 'M',
    '6': 'a', '7': 'q', '8': 'T', '9': 'R', ':': '7', ';': '&', '<': 't', '=': '(',
    '>': 'i', '?': 'v', 'A': 'E', 'C': '5', 'D': '8', 'E': 'k', 'F': 'j', 'G': '9',
    'H': '~', 'I': 'w', 'J': 'V', 'K': 'B', 'L': 'Z', 'M': 'C', 'N': 'n', 'O': 'A',
    'R': 'W', 'S': '-', 'T': '3', 'V': '0', 'W': 'D', 'X': 'O', 'Y': 'H', 'Z': 'J',
    '[': 'd', '^': '.', '_': 'e', 'a': 'K', 'b': '/', 'c': 's', 'd': '=', 'e': 'l',
    'f': ')', 'g': '6', 'h': 'r', 'i': 'G', 'k': 'L', 'm': 'b', 'o': 'I', 'p': 'm',
    'q': 'u', 's': 'c', 't': 'P', 'u': 'x', 'w': 'o', 'x': 'N', 'y': 'y', 'z': '?',
    '}': 'p', '~': 'S', ')': '%'
}

def decode_xrom_url(text: str) -> str:
    return ''.join(DECODEMAP.get(char, char) for char in text)

def extract_json_urls(config_text):
    urls = re.findall(r'https://xromtv\.com/[^"\'\s]+\.json', config_text)
    return urls

def extract_m3u_urls(config_text):
    urls = re.findall(r'https://[^"\'\s]+\.m3u', config_text)
    return urls

def fetch_html_page(url):
    try:
        headers = {"User-Agent": "Android Vinebre Software"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Errore durante il fetch della pagina HTML: {e}")
        return None
    

def fetch_xrom_config():
    try:
        config_text = fetch_html_page(XROMAPIURL)
        return config_text        
    except Exception as e:
        print(f"Errore durante il fetch XROM: {e}")
        return None, []
    


def extract_ppv_html_content(config_text):
    import re
    id_pattern = r's(\d+)_idgo=X-SOLO-PPV'
    matches = re.findall(id_pattern, config_text)
    
    if not matches:
        print("Nessun ID con X-SOLO-PPV trovato")
        return

    
    for section_id in matches:
        full_id = f"s{section_id}"
        html_pattern = rf"s{section_id}_html=([\s\S]*?)(?=s\d+_|$)"
        
        html_match = re.search(html_pattern, config_text)
        
        if html_match:
            html_content = html_match.group(1).strip()
            extract_channels_from_html(html_content, config_text)
        else:
            print(f"Nessun HTML trovato per {full_id}")
    
    return matches

def extract_channels_from_html(html_content, config_text):
    # rgex per trovare i tag <a class="canale">
    #channel_pattern = r'<a\s+class="canale"\s+href="go:([^"]+)"[^>]*>.*?<p>([^<]+)</p>.*?</a>'
    channel_pattern = r'<a\s+class="canale[^"]*"\s+href="go:([^"]+)"[^>]*>.*?<p>([^<]+)</p>.*?</a>'
    
    channels = re.findall(channel_pattern, html_content, re.DOTALL)
    
    if not channels:
        print("Nessun canale trovato nell'html")
        return []
    
    
    results = []
    
    for idgo, channel_name in channels:
        idgo_pattern = rf's(\d+)_idgo={re.escape(idgo)}'
        idgo_match = re.search(idgo_pattern, config_text)
        
        if not idgo_match:
            print(f"nessun id trovato per idgo={idgo}")
            continue
        
        section_id = idgo_match.group(1)
        
        url_pattern = rf's{section_id}_url=(.+?)(?=\]\[s\d+_|$)'
        url_match = re.search(url_pattern, config_text)
        
        if not url_match:
            continue
        
        full_url = url_match.group(1)
        
        # @y@@yy1111 sarebbe https:// parte fissa
        if '@y@@yy1111@' in full_url:
            encoded_part = full_url.split('@y@@yy1111@', 1)[1]
            decoded_url = f"https://{decode_xrom_url(encoded_part)}"

        # trova le clearkey
        clearkey_pattern = rf's{section_id}_li=([^\]\[]+)'
        clearkey_match = re.search(clearkey_pattern, config_text)

        clearkey = None
        keyid = None
        key = None

        if clearkey_match:
            clearkey_url = clearkey_match.group(1)
            parsed_url = urlparse(clearkey_url)
            params = parse_qs(parsed_url.query)
            if 'keyid' in params and 'key' in params:
                keyid = params['keyid'][0]
                key = params['key'][0]
                clearkey = f"{keyid}:{key}"

        
        results.append({
            'channel_name': channel_name,
            'url': decoded_url,
            'clearkey': clearkey
        })
    
    print("\n" + "="*80)
    print(f"EVENTI estratti: {len(results)}\n")
    for res in results:
        print(f"Canale: {res['channel_name']}\nURL: {res['url']}\nClearKey: {res['clearkey']}\n{'─'*80}")
    
    return results

def extract_playlist_json_urls(config_text):
        print("\n" + "="*80)
        print("PLAYLIST M3U:")
        playlist = []
        playlist.extend(extract_m3u_urls(fetch_html_page(XROMSKYOPAGEURL)))
        playlist.extend(extract_m3u_urls(config_text))
        playlist.extend(extract_json_urls(config_text))
        print(playlist)

if __name__ == "__main__":
    config_text = fetch_xrom_config()
    if config_text:
        extract_playlist_json_urls(config_text)
        extract_ppv_html_content(config_text)
