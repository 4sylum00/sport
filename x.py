import base64
import hashlib
import re
import requests
import time
import random
from urllib.parse import urlparse, parse_qs, unquote
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import unpad

XROMAPIURL = "https://config.e-droid.net/srv/config.php?v=197&vname=9.8&idapp=3579183&idusu=0&codggp=0&am=0&idlit=&paenv=1&pa=IT&pn=xromtv.italia&fus=01&01=00000000&aid=41fa0c253a5ef255"
PROXY_URL = "https://corsproxy.io/"
PROXY_URL2 = "https://api.codetabs.com/v1/proxy/?quest="
API_CHANNEL_HD = "https://xromtv.com/secure_stream/secure_stream/generate.php"
API_EVENTI = "https://xromtv.com/secure_stream/generate.php"

_KEY_B64 = 'RDdrUDJtUjl2TDRiVDFjUThqRjB3WjVuSDZnUzN5WDdkSjJwTTlmSzF2QzhiTjR3SDVxVjB6VDhyRzN4UjZqTA=='

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

playlist = []
channels = []

def decode_xrom_url(text: str) -> str:
    return ''.join(DECODEMAP.get(char, char) for char in text)

def extract_json_urls(config_text):
    if not config_text:
        return []
    urls = re.findall(r'https://xromtv\.com/[^"\'\s]+\.json', config_text)
    return urls

def extract_m3u_urls(config_text):
    if not config_text:
        return []
    urls = re.findall(r'https://[^"\'\s]+\.m3u', config_text)
    return urls

def fetch_html_page(url):
    try:
        headers = {"User-Agent": "Android Vinebre Software"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Errore durante il fetch della pagina HTML {url}: {e}")
        return None

def fetch_xrom_config():
    try:
        config_text = fetch_html_page(XROMAPIURL)
        return config_text
    except Exception as e:
        print(f"Errore durante il fetch XROM: {e}")
        return None

def extract_channels_from_html(html_content, config_text, section_id):
    channel_pattern = r'<a\s+class="canale[^"]*"\s+href="go:([^"]+)"[^>]*>.*?<p>([^<]+)</p>.*?</a>'
    data_pattern = r'data-id="(?P<id>[^"]+)".*?data-url="go:(?P<url>[^"]+)"'
    channels_found = re.findall(channel_pattern, html_content, re.DOTALL)
    channel_pattern = r'<div\s+class="btn-item"[^>]*data-url="go:([^"]+)"[^>]*data-id="([^"]+)"'
    channels_found.extend(re.findall(channel_pattern, html_content, re.DOTALL))
    data_channels = {m['url']: m['id'] for m in re.finditer(data_pattern, html_content, re.DOTALL)}
    
    if not channels_found:
        channels_found = list(data_channels.items())
    else:
        channels_found.extend(data_channels.items())

    if not channels_found and not data_channels:
        return []

    results = []
    for idgo, channel_name in channels_found:
        idgo_pattern = rf's(\d+)_idgo={re.escape(idgo)}'
        idgo_match = re.search(idgo_pattern, config_text)

        if not idgo_match:
            idgo_match = re.search(idgo_pattern, html_content)
        if not idgo_match:
            continue

        section_id = idgo_match.group(1)
        url_pattern = rf's{section_id}_url=(.+?)(?=\]\[s\d+_|$)'
        url_match = re.search(url_pattern, config_text)

        if not url_match:
            continue

        full_url = url_match.group(1)

        if '@y@@yy1111@' in full_url:
            encoded_part = full_url.split('@y@@yy1111@', 1)[1]
            decoded_url = f"https://{decode_xrom_url(encoded_part)}"

            clearkey_pattern = rf's{section_id}_li=([^\]\[]+)'
            clearkey_match = re.search(clearkey_pattern, config_text)

            clearkey = None
            license_url = None

            if clearkey_match:
                clearkey_url = clearkey_match.group(1)

                if 'license?id' in clearkey_url:
                    try:
                        channel_name = re.search(r'channel\(([^)]+)\)', decoded_url).group(1)
                        channel_name = channel_name.replace('sky','sky ').replace('sport','sport ').replace('cinema','cinema ').replace('plus',' plus').replace('channel',' channel').replace('network',' network')
                        channel_name = ' '.join(word.capitalize() for word in channel_name.split())+' FHD'
                    except:
                        pass
                    license_url = clearkey_url
                else:
                    parsed_url = urlparse(clearkey_url)
                    params = parse_qs(parsed_url.query)

                    if 'keyid' in params and 'key' in params:
                        keyid = params['keyid'][0]
                        key = params['key'][0]
                        clearkey = f"{keyid}:{key}"
            results.append({
                'channel_name': channel_name,
                'url': decoded_url,
                'clearkey': clearkey,
                'license': license_url
            })
    if results:
        print(f"Canali trovati in sezione {section_id}: {[c['channel_name'] for c in results]}")        
    return results

def extract_ppv_html_content(config_text, id_list):
    print("\n" + "=" * 80)
    print(f"Download e parsing contenuti PPV {id_list}")
    escaped_ids = [re.escape(id_val) for id_val in id_list]
    ids_pattern = '|'.join(escaped_ids)
    id_pattern = rf's(\d+)_idgo=({ids_pattern})'

    matches = re.findall(id_pattern, config_text)

    if not matches:
        print(f"Nessun ID trovato per: {', '.join(id_list)}")
        return []

    print(f"ID trovati per {', '.join(id_list)}: {[match[0] for match in matches]}")
    found_section_ids = [match[0] for match in matches]

    for section_id in found_section_ids:
        print(f"\nElaborazione sezione ID: {section_id}")
        html_pattern = rf"s{section_id}_html=([\s\S]*?)(?=s\d+_|$)"
        html_match = re.search(html_pattern, config_text)

        if html_match:
            html_content = html_match.group(1).strip()
            html_content = html_content.replace('\r\n',' ').replace('@MNQ@','<').replace('@CCORCH@',']')

            if html_content.startswith("GET_"):
                html_code = re.search(r'GET_(\d+)', html_content)

                if html_code:
                    html_page_url = f"https://html.e-droid.net/html/get_html.php?ida=3579183&ids={section_id}&fum={html_code.group(1)}"
                    html_content = fetch_html_page(html_page_url)
                    if html_content:
                        html_content = html_content.replace('@MNQ@','<').replace('@CCORCH@',']')
                        playlist.extend(extract_m3u_urls(html_content))
                        playlist.extend(extract_json_urls(html_content))
                else:
                    continue

            b64_encoding = check_b64(html_content)
            if b64_encoding:
                print(f"Base64 trovato in sezione {section_id}, decodificando...")
                for b64_string in b64_encoding:
                    try:
                        decoded_bytes = base64.b64decode(b64_string)
                        decoded_str = decoded_bytes.decode('utf-8', errors='ignore')
                        playlist.extend(extract_m3u_urls(decoded_str))
                        playlist.extend(extract_json_urls(decoded_str))
                        channels.extend(extract_channels_from_html(decoded_str, config_text, section_id))
                        if check_jsfuck(decoded_str):
                            print(f"JSFuck trovato in Base64 decodificato in sezione {section_id}, decodificando...")
                            playlist_unjsfucked = runBrowser(decoded_str)
                            channels.extend(extract_channels_from_html(html_content, config_text, section_id))
                            if playlist_unjsfucked:
                                playlist.extend(playlist_unjsfucked)
                            else:
                                print(f"Decodifica JSFuck fallita per Base64 in sezione {section_id}")
                    except Exception as e:
                        print(f"Errore decodifica Base64 in sezione {section_id}: {e}")    


            if check_jsfuck(html_content):
                print(f"JSFuck trovato in sezione {section_id}, decodificando...")
                playlist_unjsfucked = runBrowser(html_content)
                if playlist_unjsfucked:
                    playlist.extend(playlist_unjsfucked)
                else:
                    print(f"Decodifica JSFuck fallita per sezione {section_id}")
            channels.extend(extract_channels_from_html(html_content, config_text, section_id))
    print(f"Canali PPV estratti: {len(channels)}")

def check_b64(html):
    b64_regex = r"atob\s*\(\s*['\"]([^'\"]*)['\"]"
    b64_matches = re.findall(b64_regex, html)
    return b64_matches

def check_jsfuck(html_content):
    jsfuck_regex = r'<script[^>]*>\s*(?:/\*(?:.|\n)*?\*/\s*)*\s*([\[!\]\(\)\+]+)\s*(?:/\*(?:.|\n)*?\*/\s*)*\s*</script>'
    jsfuck_matches = re.findall(jsfuck_regex, html_content)
    return jsfuck_matches



def runBrowser(htmlcode):
    sniffed_url = None
    try:
        import os
        import tempfile
        import threading
        from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
        from playwright.sync_api import sync_playwright
        

        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = os.path.join(tmpdir, "index.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(htmlcode)

            class QuietHandler(SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=tmpdir, **kwargs)

                def log_message(self, format, *args):
                    pass

            server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
            port = server.server_address[1]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()

            with sync_playwright() as p:

                def handle_route(route):
                    nonlocal sniffed_url
                    url = route.request.url

                    if "php?token" in url:
                        route.abort()
                        if "https://xrom/" in url:
                            url= url.replace("https://xrom/", "http://xromtv.com/")
                        sniffed_url =url
                        return sniffed_url

                    if url.endswith(".mpd"):
                        route.abort()
                        return

                    route.continue_()

                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()

                context.route("**/*", handle_route)

                page.goto(f"http://127.0.0.1:{port}/index.html", wait_until="networkidle")

                browser.close()

    except Exception as e:
        print(f"runBrowser error: {e}")
        return None
    finally:
        server.shutdown()
        server.server_close()
    return sniffed_url


def extract_playlist_json_urls(config_text):
    playlist.extend(extract_m3u_urls(config_text))
    playlist.extend(extract_json_urls(config_text))
    b64 = check_b64(config_text)
    if b64:
        print(f"Base64 trovato in config, decodificando...")
        for b64_string in b64:
            try:
                decoded_bytes = base64.b64decode(b64_string)
                decoded_str = decoded_bytes.decode('utf-8', errors='ignore')
                playlist.extend(extract_m3u_urls(decoded_str))
                playlist.extend(extract_json_urls(decoded_str))
            except Exception as e:
                print(f"Errore decodifica Base64 in config: {e}")

def download_playlist_via_proxy(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; Redmi Note 9 Build/TD1A.221105.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/144.0.7559.132 Mobile Safari/537.36 Vinebre",
        "Host": "xromtv.com",
        "sec-ch-ua": 'Not(A:Brand";v="8", "Chromium";v="144", "Android WebView";v="144',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "X-Requested-With": "xromtv.italia",
        "Connection": "keep-alive",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7"
        }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:  
        print(e)  
        try:
            proxy_url = f"{PROXY_URL}{url}"      
            response = requests.get(proxy_url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            proxy_url = f"{PROXY_URL2}{url}"      
            response = requests.get(proxy_url, headers=headers, timeout=30)
            return response.text
        
def handle_group_title(line):
    group_title_match = re.search(r'group-title="([^"]+)"', line)
    channel_name = line.split(',', 1)[-1].strip().upper()
    new_group_title = "SKY INTRATTENIMENTO"

    if "SKY SPORT" in channel_name or "CALCIO" in channel_name:
        new_group_title = "SKY SPORT"
    elif "CINEMA" in channel_name:
        new_group_title = "SKY CINEMA"
    elif "SKY" in channel_name and "SPORT" not in channel_name and "CINEMA" not in channel_name:
        new_group_title = "SKY INTRATTENIMENTO"
    elif "DAZN" in channel_name:
        new_group_title = "DAZN"

    if group_title_match:
        group_title = group_title_match.group(1)
        if "EVENTI" in group_title:
            new_group_title = "EVENTI"
        line = line.replace(f'group-title="{group_title}"', f'group-title="{new_group_title}"')

    if 'group-title="' not in line:
        clean_channel_name = channel_name.replace('FHD','')
        tvg_id = '.'.join(word.capitalize() for word in clean_channel_name.split())+'.it'
        line = line.replace('#EXTINF:-1', f'#EXTINF:-1 group-title="{new_group_title}" tvg-id="{tvg_id}"')    
    return line

def parse_m3u_content(content):
    if not content:
        return []

    channels_parsed = []
    lines = content.strip().split('\n')

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith('#EXTINF'):
            
            line = handle_group_title(line)

            channel_info = {
                'extinf': line,
                'kodiprop': [],
                'url': ''
            }

            i += 1
            while i < len(lines):
                next_line = lines[i].strip()

                if next_line.startswith('#KODIPROP'):
                    channel_info['kodiprop'].append(next_line)
                    i += 1
                elif next_line and not next_line.startswith('#'):
                    channel_info['url'] = next_line
                    i += 1
                    break
                else:
                    i += 1

            if channel_info['url']:
                channels_parsed.append(channel_info)
        else:
            i += 1

    return channels_parsed

def merge_channels(all_channels):
    seen_urls = set()
    unique_channels = []

    for channel in all_channels:
        url = channel.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_channels.append(channel)

    return unique_channels

def channel_dict_to_m3u(channel_dict):
    lines = []

    name = channel_dict.get('channel_name', 'Unknown')
    url = channel_dict.get('url', '')
    clearkey = channel_dict.get('clearkey')
    license_url = channel_dict.get('license')
    lines.append(handle_group_title(f'#EXTINF:-1,{name}'))
    lines.append('#KODIPROP:inputstream.adaptive.manifest_type=mpd')

    if license_url:
        lines.append('#KODIPROP:inputstream.adaptive.license_type=com.widevine.alpha')
        lines.append(f'#KODIPROP:inputstream.adaptive.license_key={license_url}')
    elif clearkey:
        lines.append('#KODIPROP:inputstream.adaptive.license_type=clearkey')
        lines.append(f'#KODIPROP:inputstream.adaptive.license_key={clearkey}')

    lines.append(url)

    return '\n'.join(lines)

def write_m3u_file(channels_list, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n\n')

        for channel in channels_list:
            if isinstance(channel, dict) and 'extinf' in channel:
                f.write(channel['extinf'] + '\n')
                for kodiprop in channel.get('kodiprop', []):
                    f.write(kodiprop + '\n')
                f.write(channel['url'] + '\n\n')
            elif isinstance(channel, dict) and 'channel_name' in channel:
                f.write(channel_dict_to_m3u(channel) + '\n\n')

def use_sniff_api(api_url):

    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; Redmi Note 9 Build/TD1A.221105.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/144.0.7559.132 Mobile Safari/537.36 Vinebre",
        "Host": "xromtv.com",
        "sec-ch-ua": 'Not(A:Brand";v="8", "Chromium";v="144", "Android WebView";v="144',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "X-Requested-With": "xromtv.italia",
        "Connection": "keep-alive",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7"
        }
    try:
        html = requests.get(api_url, headers=headers, timeout=60)
        return runBrowser(html.text)
    except Exception as e:
        print(f"Errore durante la richiesta API {api_url}: {e}")
    return None



def decrypt_payload(payload_b64: str) -> str:
    try:
        key_raw = base64.b64decode(_KEY_B64)
        key = hashlib.sha256(key_raw).digest()
        data = base64.b64decode(payload_b64)
        iv = data[:16]
        ciphertext = data[16:]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
        return decrypted.decode('utf-8')
    except Exception:
        return ""


def main():
    config_text = fetch_xrom_config()

    all_channels = []
    SNIFFING_APIS = re.findall(r'_url=(https?://xromtv\.com[^]]+)', config_text)
    for urls in SNIFFING_APIS:
        if 'login' in urls:
            continue
        print(f"\n\nTrovato: {urls}")
        sniffed_url = use_sniff_api(urls)
        print(f"SNIFFED: {sniffed_url}")
        content = download_playlist_via_proxy(sniffed_url)
        if content:
            if 'EXTM3U' not in content:
                content = decrypt_payload(content)
            parsed = parse_m3u_content(content)
            print(f"Canali trovati: {len(parsed)}")
            all_channels.extend(parsed)

    unique_channels = merge_channels(all_channels)
    final_channels = unique_channels + channels
    print(f"\nCanali totali unici: {len(final_channels)}")
    output_file = 'xrom.m3u'
    write_m3u_file(final_channels, output_file)

    print(f"\nFile creato: {output_file}")

if __name__ == "__main__":
    main()
