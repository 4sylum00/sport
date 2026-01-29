#!/usr/bin/env python3

import base64
import json
import requests
import re
from datetime import datetime, timedelta

ALPHABET_A = ['a','A','b','B','c','C','d','D','e','E','f','F','g','G','h','H','i','I','j','J','k','K','l','L','m','M','n','N','o','O','p','P','q','Q','r','R','s','S','t','T','u','U','v','V','w','W','x','X','y','Y','z','Z']
ALPHABET_B = ['f','F','g','G','j','J','k','K','a','A','p','P','b','B','m','M','o','O','z','Z','e','E','n','N','c','C','d','D','r','R','q','Q','t','T','v','V','u','U','x','X','h','H','i','I','w','W','y','Y','l','L','s','S']

table_d = [chr(0)] * 128
for i in range(len(ALPHABET_A)):
    table_d[ord(ALPHABET_B[i])] = ALPHABET_A[i]

for i in range(128):
    if ord(table_d[i]) == 0:
        table_d[i] = chr(i)

def decodifica(s):
    s = s.replace("\n","").replace("\r","").strip()
    subst = ''.join(table_d[ord(c)] for c in s if ord(c) < 128)
    subst += '=' * ((4 - len(subst) % 4) % 4)
    return base64.b64decode(subst, validate=False).decode('utf-8', errors='ignore')

def unescape(s):
    return s.replace("\\/", "/")

def parse_link_headers(link_str):
    if '|' not in link_str:
        return {'url': link_str, 'headers': {}}
    parts = link_str.split('|', 1)
    url = parts[0]
    headers_str = parts[1]
    headers = {}
    for header_pair in headers_str.split('&'):
        if '=' in header_pair:
            key, val = header_pair.split('=', 1)
            headers[key] = val
    return {'url': url, 'headers': headers}

def parseDateTime(date_str, time_str):
    datetime_str = f"{date_str} {time_str}"
    return datetime.strptime(datetime_str, "%d/%m/%Y %H:%M:%S") + timedelta(hours=1)

def process_events(base_url):
    print("="*80)
    print("EVENTI SPORTIVI")
    print("="*80 + "\n")
    
    app = requests.get(f"{base_url}/app.json", timeout=10).json()
    main_obj = app[0]
    events_encoded = main_obj.get("events", "").replace("\n", "").replace("\r", "")
    events_list = json.loads(events_encoded)
    
    for i, enc_event in enumerate(events_list):
        try:
            event_json = decodifica(enc_event)
            event = json.loads(event_json)
            dateTime = parseDateTime(event.get('date', ''), event.get('time', ''))
            name = f"{event.get('eventName', 'N/A')} - {event.get('teamAName', 'N/A')} vs {event.get('teamBName', 'N/A')} - {dateTime.strftime('%d/%m/%Y %H:%M')}"
            
            # Controlla se l'evento è visibile
            if not event.get('visible', False):
                continue
            
            # Controlla se l'evento è già terminato con +2 ore
            if event.get('end_date') is not None and event.get('end_time') is not None:
                end_event_datetime = parseDateTime(event.get('end_date'), event.get('end_time'))
                nowPlus2Hour = datetime.now() + timedelta(hours=2)
                if end_event_datetime < nowPlus2Hour:
                    continue
            
            links_path = event.get('links', '')
            print(f"{name}")
            
            if links_path:
                url = f"{base_url}/{links_path.lstrip('/')}"
                try:
                    links_resp = requests.get(url, timeout=10).json()
                    enc_links = links_resp.get('links', '')
                    if enc_links:
                        decoded_links = decodifica(enc_links)
                        links_list = json.loads(decoded_links)
                        
                        # esclude tutti i no.link
                        valid_links = [link_obj for link_obj in links_list
                                       if link_obj.get('link', '').strip() != 'https://no.link']
                        
                        if not valid_links:
                            print("  Link non ancora presenti per l'evento\n")
                            continue
                        
                        for idx, link_obj in enumerate(valid_links, 1):
                            channel_name = link_obj.get('name', 'N/A')
                            raw_link = unescape(link_obj.get('link', ''))
                            api = unescape(link_obj.get('api', ''))
                            link_data = parse_link_headers(raw_link)
                            
                            print(f"\n  [{idx}] {channel_name}")
                            print(f"      URL: {link_data['url']}")
                            if link_data['headers']:
                                print(f"      Headers:")
                                for hkey, hval in link_data['headers'].items():
                                    print(f"        {hkey}: {hval}")
                            if api:
                                print(f"      API: {api}")
                        print()
                except Exception as e:
                    print(f"  Errore: {e}\n")
        except Exception as e:
            print(f"{i+1}. Decode error: {e}\n")
    
    print("-"*80 + "\n")

def process_livesport_channels(base_url):
    print("="*80)
    print("CANALI LIVE 24H")
    print("="*80 + "\n")
    
    sports_url = f"{base_url}/channels/Sports.json"
    
    try:
        sports_resp = requests.get(sports_url, timeout=10).json()
        
        for i, channel_obj in enumerate(sports_resp):
            try:
                enc_channel = channel_obj.get('channel', '')
                if not enc_channel:
                    continue
                
                channel_json = decodifica(enc_channel)
                channel = json.loads(channel_json)
                
                channel_name = channel.get('name', 'N/A')
                logo = unescape(channel.get('logo', ''))
                visible = channel.get('visible', False)
                
                # Controlla se il canale è visibile
                if not visible:
                    continue
                
                links_path = channel.get('links', '')
                link_names = channel.get('link_names', [])
                
                print(f"[{i+1}] {channel_name}")
                print(f"    Logo: {logo}")
                
                if links_path:
                    url = f"{base_url}/{links_path.lstrip('/')}"
                    try:
                        links_resp = requests.get(url, timeout=10).json()
                        enc_links = links_resp.get('links', '')
                        if enc_links:
                            decoded_links = decodifica(enc_links)
                            links_list = json.loads(decoded_links)
                            
                            # esclude tutti i no.link
                            valid_links = [link_obj for link_obj in links_list
                                           if link_obj.get('link', '').strip() != 'https://no.link']
                            
                            if not valid_links:
                                print("    Link non ancora presenti per questo canale\n")
                                continue
                            
                            for idx, link_obj in enumerate(valid_links, 1):
                                # Usa il nome dal link_names se disponibile, altrimenti usa il nome del link
                                stream_name = link_names[idx-1] if idx-1 < len(link_names) else link_obj.get('name', 'N/A')
                                raw_link = unescape(link_obj.get('link', ''))
                                api = unescape(link_obj.get('api', ''))
                                link_data = parse_link_headers(raw_link)
                                
                                print(f"\n    Stream [{idx}]: {stream_name}")
                                print(f"        URL: {link_data['url']}")
                                if link_data['headers']:
                                    print(f"        Headers:")
                                    for hkey, hval in link_data['headers'].items():
                                        print(f"          {hkey}: {hval}")
                                if api:
                                    print(f"        API: {api}")
                            print()
                    except Exception as e:
                        print(f"    Errore nel recupero dei link: {e}\n")
                
            except Exception as e:
                print(f"Errore nella decodifica del canale {i+1}: {e}\n")
    
    except Exception as e:
        print(f"Errore nel recupero dei canali live: {e}\n")
    
    print("-"*80 + "\n")

def main():
    base_url = "http://mytflix.xyz"
    
    process_events(base_url)
    
    process_livesport_channels(base_url)

if __name__ == "__main__":
    main()
