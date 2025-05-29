# Steam Clip Export Tool

A Python script that automatically processes and exports Steam game clips with intelligent labeling for Counter-Strike 2 (CS2) highlights.

## Features

### 🎯 Intelligent CS2 Analysis
- **Accurate Kill Counting**: Analyzes timeline data to count all kills in a round (individual kills + multi-kill events)
- **Smart Map Detection**: Finds the correct map name from the actual game (not warmup/practice rounds)
- **Kill Classification**: Automatically labels clips as Ace (5+ kills), Quad_kill (4), Triple_kill (3), Double_kill (2), Kill (1), or Highlight

### 📁 Automated Processing
- **Batch Processing**: Processes multiple clips automatically
- **Stream Concatenation**: Combines fragmented video/audio streams into complete MP4 files
- **Duplicate Prevention**: Tracks processed clips to avoid re-processing

### 🏷️ Smart File Naming
Generates descriptive filenames like:
- `2025-05-23_21.36.27_Mirage-Quad_kill.mp4`
- `2025-05-21_00.33.23_Anubis-Triple_kill.mp4`
- `2025-05-24_16.03.53_Inferno-Ace.mp4`

## Requirements

- **Python 3.x**
- **FFmpeg** (must be accessible via command line)
- **Steam clips** exported to a local directory
- **App ID mapping file** (JSON format)

## Directory Structure

```
Source Directory (C:\Temp\SteamTest\)
├── clip_730_20250523_193627/
│   ├── video/
│   │   └── bg_730_xxxxx/
│   │       ├── init-stream0.m4s
│   │       ├── chunk-stream0-1.m4s
│   │       ├── chunk-stream0-2.m4s
│   │       ├── init-stream1.m4s
│   │       └── chunk-stream1-x.m4s
│   ├── timelines/
│   │   └── timeline_xxxxx.json
│   └── .processed (created after processing)
└── clip_730_20250524_140353/
    └── ...
```

## Configuration

Edit the following constants in `export.py`:

```python
SOURCE_DIR = r'C:\Temp\SteamTest'           # Where Steam clips are stored
EXPORT_DIR = r'C:\Temp\SteamExports'        # Where processed clips will be saved
APPID_MAP_FILE = r'C:\Temp\appid_map.json'  # App ID to game name mapping
```

### App ID Mapping File

Create `appid_map.json` with game mappings:

```json
{
  "730": "CS2",
  "440": "TF2",
  "570": "Dota2"
}
```

## Usage

1. **Install Requirements**:
   ```bash
   # Install FFmpeg (Windows)
   winget install FFmpeg

   # Or download from https://ffmpeg.org/
   ```

2. **Configure Paths**:
   - Update `SOURCE_DIR`, `EXPORT_DIR`, and `APPID_MAP_FILE` in the script
   - Create your `appid_map.json` file

3. **Run the Script**:
   ```bash
   python export.py
   ```

## How It Works

### 1. **Clip Discovery**
- Scans source directory for folders matching pattern: `clip_{appid}_{date}_{time}`
- Skips already processed clips (marked with `.processed` file)

### 2. **CS2 Timeline Analysis** (for App ID 730)
- Finds the **last trigger event** with `duration > 0` in the timeline
- Works **backwards** to find the nearest "Start of round" event
- Extracts **map name** from the round start description
- Counts **all kills** in that round:
  - Individual kill events: `"You killed PlayerName"`
  - Multi-kill events: `"Double kill"`, `"Triple kill"`, `"Multi kill"`, etc.
  - Parses victim names from descriptions with/without weapon info

### 3. **Video Processing**
- Concatenates fragmented stream files (`init-stream*.m4s` + `chunk-stream*-*.m4s`)
- Combines video and audio streams using FFmpeg
- Outputs final MP4 file with descriptive filename

### 4. **Output Organization**
```
Export Directory (C:\Temp\SteamExports\)
└── CS2/
    ├── 2025-05-23_21.36.27_Mirage-Quad_kill.mp4
    ├── 2025-05-21_00.33.23_Anubis-Triple_kill.mp4
    └── 2025-05-24_16.03.53_Inferno-Ace.mp4
```

## Examples

### Timeline Analysis Example

For a CS2 round with these events:
```json
{"title": "Start of round 9", "description": "Mirage"}
{"title": "You killed -Each-"}
{"title": "Double kill", "description": "You killed Relkon and JAKOBO with the AK-47"}
{"title": "You killed Umulig1"}
```

**Result**: `2025-05-23_21.36.27_Mirage-Quad_kill.mp4`
- **Map**: Mirage (from round start)
- **Kills**: 4 total (1 + 2 + 1)
- **Classification**: Quad_kill

### Multi-Kill Event Parsing

Handles various description formats:
- `"You killed Player1 and Player2 with the AK-47"` → 2 kills
- `"You killed kataf, chupacabra298, and Ecke"` → 3 kills
- Generic `"Triple kill"` → 3 kills (fallback)

## Troubleshooting

### Common Issues

1. **FFmpeg not found**:
   - Install FFmpeg and ensure it's in your PATH
   - Test with: `ffmpeg -version`

2. **No clips processed**:
   - Check `SOURCE_DIR` path exists and contains clip folders
   - Verify folder naming pattern: `clip_{appid}_{YYYYMMDD}_{HHMMSS}`
   - Remove `.processed` files to reprocess clips

3. **Missing timeline data**:
   - Ensure timeline JSON files exist in `timelines/` subdirectory
   - Check for events with `duration > 0` in timeline

4. **Incorrect kill counting**:
   - Verify timeline contains proper event structure
   - Check for both individual and multi-kill events in the round

## Supported Games

Currently optimized for:
- **Counter-Strike 2** (App ID 730) - Full timeline analysis
- **Other Steam games** - Basic file processing without timeline analysis

## License

This project is open source. Feel free to modify and distribute.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

**Note**: This tool processes local Steam clip files. Ensure you have proper permissions for the directories you're accessing.