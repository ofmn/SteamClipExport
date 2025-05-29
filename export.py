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

def extract_cs2_clip_label(timeline_path):
    try:
        with open(timeline_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        entries = data.get('entries', [])

        # Step 1: Find ALL "Start of round" events in the timeline
        round_starts = []
        
        for i, e in enumerate(entries):
            if (
                e.get('type') == 'event' and
                e.get('title', '').startswith('Start of round') and
                'description' in e
            ):
                round_starts.append({
                    'index': i, 
                    'time': int(e['time']),
                    'map': e['description']
                })

        if not round_starts:
            return ''

        # Step 2: Try rounds starting from the last one, working backwards
        for round_idx in range(len(round_starts) - 1, -1, -1):
            round_start = round_starts[round_idx]
            map_name = round_start['map']
            
            # Find the next round start to define the round boundary (if any)
            round_end_time = None
            if round_idx < len(round_starts) - 1:
                round_end_time = round_starts[round_idx + 1]['time']

            # Step 3: Count kills in this round
            kill_events = []
            multi_kill_events = []
            
            for e in entries[round_start['index']:]:
                t = int(e['time'])
                if round_end_time and t >= round_end_time:
                    break
                if e.get('type') == 'event':
                    title = e.get('title', '')
                    
                    # Collect individual kill events
                    if title.startswith('You killed ') and title != 'You killed yourself' and not any(kw in title for kw in ['Double kill', 'Triple kill', 'Quad kill', 'Ace', 'Multi kill']):
                        kill_events.append({
                            'time': t,
                            'title': title,
                            'type': 'individual'
                        })
                    
                    # Collect multi-kill events
                    elif any(kw in title for kw in ['Double kill', 'Triple kill', 'Quad kill', 'Ace', 'Multi kill']):
                        multi_kill_events.append({
                            'time': t,
                            'title': title,
                            'description': e.get('description', ''),
                            'type': 'multi'
                        })

            # Count kills from individual events
            kill_count = 0
            for event in kill_events:
                title = event['title']
                # Try to extract victim names from "You killed X with Y" or "You killed X and Y with Z"
                match = re.search(r'You killed (.+?)(?:\s+with|$)', title)
                if match:
                    victims_part = match.group(1)
                    # Split by "and" to handle multiple victims in one event
                    victims = re.split(r' and ', victims_part)
                    individual_kills = len([v for v in victims if v.strip()])
                    kill_count += individual_kills
                else:
                    # Fallback: if regex fails, assume it's one kill
                    kill_count += 1

            # Add kills from multi-kill events
            for event in multi_kill_events:
                title = event['title']
                description = event['description']
                
                # Try to extract victim names from description
                multi_kill_count = 0
                if 'You killed' in description:
                    # Try with weapon info first: "You killed X and Y with the Z"
                    match = re.search(r'You killed (.+?) with', description)
                    if match:
                        victims_part = match.group(1)
                        victims = re.split(r' and |, ', victims_part)
                        multi_kill_count = len([v for v in victims if v.strip()])
                    else:
                        # Try without weapon info: "You killed X, Y, and Z"
                        match = re.search(r'You killed (.+)', description)
                        if match:
                            victims_part = match.group(1)
                            victims = re.split(r' and |, ', victims_part)
                            multi_kill_count = len([v for v in victims if v.strip()])
                
                # If we couldn't parse the description, fall back to title-based counting
                if multi_kill_count == 0:
                    if 'Ace' in title:
                        multi_kill_count = 5
                    elif 'Quad kill' in title:
                        multi_kill_count = 4
                    elif 'Triple kill' in title:
                        multi_kill_count = 3
                    elif 'Double kill' in title:
                        multi_kill_count = 2
                    elif 'Multi kill' in title:
                        # For generic "Multi kill", we can't determine count from title alone
                        # This should ideally be parsed from description, so if we get here it's a fallback
                        multi_kill_count = 2  # Conservative estimate
                
                # Add these kills to our total count
                kill_count += multi_kill_count

            # If we found kills in this round, use it!
            if kill_count > 0:
                # Step 4: Classify kill count
                if kill_count >= 5:
                    label = 'Ace'
                elif kill_count == 4:
                    label = 'Quad_kill'
                elif kill_count == 3:
                    label = 'Triple_kill'
                elif kill_count == 2:
                    label = 'Double_kill'
                elif kill_count == 1:
                    label = 'Kill'
                else:
                    label = 'Highlight'

                # Step 5: Sanitize map name
                safe_map = re.sub(r'[<>:"/\\|?*\n\r\t]', '', map_name).strip().replace(' ', '_')
                return f'_{safe_map}-{label}'

        # If no rounds had kills, use the last round as "Highlight"
        if round_starts:
            map_name = round_starts[-1]['map']
            safe_map = re.sub(r'[<>:"/\\|?*\n\r\t]', '', map_name).strip().replace(' ', '_')
            return f'_{safe_map}-Highlight'
        
        return ''

    except Exception as e:
        print(f"[WARN] Failed to extract CS2 label: {e}")
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

    label = ''
    if appid == '730':
        timeline_dir = os.path.join(full_path, 'timelines')
        if os.path.exists(timeline_dir):
            timeline_file = next((f for f in os.listdir(timeline_dir) if f.endswith('.json')), None)
            if timeline_file:
                timeline_path = os.path.join(timeline_dir, timeline_file)
                label = extract_cs2_clip_label(timeline_path)

    output_file = os.path.join(output_folder, f'{timestamp}{label}.mp4')

    if os.path.exists(output_file):
        print(f'[SKIP] Output already exists: {output_file}')
        with open(marker_path, 'w') as f:
            f.write('already exported')
        continue

    print(f'[INFO] Processing: {folder} → {game}\\{timestamp}{label}.mp4')

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
