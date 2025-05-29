import os
import json
import subprocess
from datetime import datetime, timedelta
import re

SOURCE_DIR = r'C:\Temp\SteamTest'
EXPORT_DIR = r'C:\Temp\SteamExports'
APPID_MAP_FILE = r'C:\Temp\appid_map.json'

with open(APPID_MAP_FILE, 'r') as f:
    appid_map = json.load(f)

def parse_folder_name(name):
    match = re.match(r'clip_(\d+)_(\d{8})_(\d{6})', name)
    if not match:
        print(f'[SKIP] Folder "{name}" does not match expected pattern.')
        return None
    appid, date_str, time_str = match.groups()
    dt = datetime.strptime(f'{date_str}_{time_str}', '%Y%m%d_%H%M%S') + timedelta(hours=2)
    game = appid_map.get(appid, f"App_{appid}")
    return appid, game, dt.strftime('%Y-%m-%d_%H.%M.%S')

def get_clip_title_if_cs2(base_path, appid):
    if appid != '730':
        return ''
    
    timeline_dir = os.path.join(base_path, 'timelines')
    if not os.path.exists(timeline_dir):
        return ''

    timeline_file = next((f for f in os.listdir(timeline_dir) if f.endswith('.json')), None)
    if not timeline_file:
        return ''
    
    timeline_path = os.path.join(timeline_dir, timeline_file)

    try:
        with open(timeline_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for entry in data.get('entries', []):
            if (
                entry.get('type') == 'event' and
                entry.get('duration') and
                entry.get('duration') != '0' and
                'title' in entry
            ):
                # Sanitize title: remove bad filename characters
                title = re.sub(r'[<>:"/\\|?*\n\r\t]', '', entry['title'])
                return f"_{title.strip().replace(' ', '_')}"
    except Exception as e:
        print(f'[WARN] Failed to parse timeline for {appid}: {e}')
    
    return ''



def concat_stream(stream_dir, stream_name):
    init = os.path.join(stream_dir, f'init-{stream_name}.m4s')
    if not os.path.exists(init):
        print(f'[ERROR] Missing init file: {init}')
        return None

    chunks = sorted(
        [f for f in os.listdir(stream_dir) if f.startswith(f'chunk-{stream_name}-')],
        key=lambda x: int(re.search(r'(\d+)', x).group())
    )
    if not chunks:
        print(f'[ERROR] No chunk files found for {stream_name} in {stream_dir}')
        return None

    output = os.path.join(stream_dir, f'{stream_name}.m4s')
    with open(output, 'wb') as outfile:
        with open(init, 'rb') as f:
            outfile.write(f.read())
        for chunk in chunks:
            with open(os.path.join(stream_dir, chunk), 'rb') as f:
                outfile.write(f.read())
    return output

found_any = False

for folder in os.listdir(SOURCE_DIR):
    full_path = os.path.join(SOURCE_DIR, folder)
    if not os.path.isdir(full_path):
        continue

    marker_path = os.path.join(full_path, '.processed')
    if os.path.exists(marker_path):
        print(f'[SKIP] Already marked as processed: {folder}')
        continue

    parsed = parse_folder_name(folder)
    if not parsed:
        continue

    appid, game, timestamp = parsed
    video_folder = os.path.join(full_path, 'video')
    inner_folder = None

    for sub in os.listdir(video_folder):
        if sub.startswith(f'bg_{appid}_'):
            inner_folder = os.path.join(video_folder, sub)
            break

    if not inner_folder or not os.path.exists(inner_folder):
        print(f'[SKIP] Inner folder not found in: {video_folder}')
        continue

    output_folder = os.path.join(EXPORT_DIR, game)
    os.makedirs(output_folder, exist_ok=True)
    suffix = get_clip_title_if_cs2(full_path, appid)
    output_file = os.path.join(output_folder, f'{timestamp}{suffix}.mp4')


    if os.path.exists(output_file):
        print(f'[SKIP] Output already exists: {output_file}')
        # Still mark it processed to avoid checking again
        with open(marker_path, 'w') as f:
            f.write('already exported')
        continue

    print(f'[INFO] Processing: {folder} → {game}\\{timestamp}.mp4')

    video_stream = concat_stream(inner_folder, 'stream0')
    audio_stream = concat_stream(inner_folder, 'stream1')

    if not video_stream or not audio_stream:
        print('[ERROR] Failed to build one or both streams.')
        continue

    subprocess.run([
        'ffmpeg', '-y',
        '-i', video_stream,
        '-i', audio_stream,
        '-c', 'copy',
        output_file
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    os.remove(video_stream)
    os.remove(audio_stream)

    with open(marker_path, 'w') as f:
        f.write('processed')

    print(f'[OK] Exported: {output_file}')
    found_any = True

print('[DONE] All valid clips have been checked.')
