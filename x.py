import re
import requests
from urllib.parse import urlparse, parse_qs

XROMAPIURL = "https://config.e-droid.net/srv/config.php?v=197&vname=9.8&idapp=3579183&idusu=0&codggp=0&am=0&idlit=&paenv=1&pa=IT&pn=xromtv.italia&fus=01&01=00000000&aid=41fa0c253a5ef255"
XROMSKYOPAGEURL = "https://html.e-droid.net/html/get_html.php?ida=3579183&ids=37001286&fum=1769767566"
PROXY_URL = "https://xromtv-cors-proxy-m3u.xrtv-friends-only.workers.dev?url="

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
                        channel_name = channel_name.replace('sky','sky ').replace('sport','sport ').replace('cinema','cinema ').replace('plus',' plus').upper()+' FHD'
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

    found_section_ids = [match[0] for match in matches]

    for section_id in found_section_ids:
        html_pattern = rf"s{section_id}_html=([\s\S]*?)(?=s\d+_|$)"
        html_match = re.search(html_pattern, config_text)

        if html_match:
            html_content = html_match.group(1).strip()

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

            channels.extend(extract_channels_from_html(html_content, config_text, section_id))
    print(f"Canali PPV estratti: {len(channels)}")

def extract_playlist_json_urls(config_text):
    sky_page = fetch_html_page(XROMSKYOPAGEURL)
    if sky_page:
        playlist.extend(extract_m3u_urls(sky_page))
    playlist.extend(extract_m3u_urls(config_text))
    playlist.extend(extract_json_urls(config_text))

def download_playlist_via_proxy(url):
    try:
        proxy_url = f"{PROXY_URL}{url}"
        print(f"\nDownloading: {url}")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"}
        response = requests.get(proxy_url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Errore download {url}: {e}")
        return None

def parse_m3u_content(content):
    if not content:
        return []

    channels_parsed = []
    lines = content.strip().split('\n')

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith('#EXTINF'):
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

    lines.append(f'#EXTINF:-1,{name}')
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

def main():
    config_text = fetch_xrom_config()

    if config_text:
        extract_playlist_json_urls(config_text)
        extract_ppv_html_content(config_text, ['X-SOLO-PPV', 'XROM-EVENT', 'X-CAN-SKY'])

    all_channels = []

    for playlist_url in playlist:
        content = download_playlist_via_proxy(playlist_url)
        if content:
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
