# VK Audio Downloader

CLI script for downloading audio from VK by direct track URL or playlist URL.

## Requirements

- Python 3.9+
- [VK API token](https://vkhost.github.io/) with access to audio methods
- `ffmpeg` (required for HLS `.m3u8` to `.mp3` conversion)

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Download one track:

```bash
python vk_audio_downloader.py --track https://vk.com/audio142774160_456240188_71b76a487be610b2fb --token <VK_TOKEN>
```

Download a whole playlist:

```bash
python vk_audio_downloader.py --playlist https://vk.com/music/playlist/142774160_74879692_d64ad4a8663b97a847 --token <VK_TOKEN>
```

Download all tracks from user audio:

```bash
python vk_audio_downloader.py --user https://vk.com/audios142774160 --token <VK_TOKEN>
```

Save to specific directory:

```bash
python vk_audio_downloader.py --track <TRACK_URL> --path ./downloads --token <VK_TOKEN>
```

Choose behavior if file already exists (`skip` by default):

```bash
python vk_audio_downloader.py --playlist <PLAYLIST_URL> --if-exists replace --token <VK_TOKEN>
```

Choose file sorting mode (`none` by default):

```bash
python vk_audio_downloader.py --playlist <PLAYLIST_URL> --sort artist-folder --token <VK_TOKEN>
python vk_audio_downloader.py --playlist <PLAYLIST_URL> --sort artist-folder-name --token <VK_TOKEN>
```

Enable metadata enrichment (tries multiple sources in order) and writes ID3 tags for mp3:

```bash
python vk_audio_downloader.py --playlist <PLAYLIST_URL> --metadata-source auto --token <VK_TOKEN>
```

Use specific metadata source:

```bash
python vk_audio_downloader.py --playlist <PLAYLIST_URL> --metadata-source itunes --token <VK_TOKEN>
python vk_audio_downloader.py --playlist <PLAYLIST_URL> --metadata-source deezer --token <VK_TOKEN>
python vk_audio_downloader.py --playlist <PLAYLIST_URL> --metadata-source musicbrainz --token <VK_TOKEN>
python vk_audio_downloader.py --playlist <PLAYLIST_URL> --metadata-source lastfm --token <VK_TOKEN>
python vk_audio_downloader.py --playlist <PLAYLIST_URL> --metadata-source discogs --token <VK_TOKEN>
```

Sort modes:

- `none`: no folder sorting, files are saved as `Artist - Title.mp3` in target directory.
- `artist-folder`: create `%artist%/` subfolder and save file as `Title.mp3`.
- `artist-folder-name`: create `%artist%/` subfolder and save file as `Artist - Title.mp3`.

You can set token via environment variable:

Linux/macOS:

```bash
export VK_TOKEN=<VK_TOKEN>
python vk_audio_downloader.py --track <TRACK_URL>
```

Windows PowerShell:

```powershell
$env:VK_TOKEN="<VK_TOKEN>"
$env:LASTFM_API_KEY="<LASTFM_API_KEY>"   # optional, only for --metadata-source lastfm/auto
$env:DISCOGS_TOKEN="<DISCOGS_TOKEN>"     # optional, only for --metadata-source discogs/auto
python vk_audio_downloader.py --track <TRACK_URL>
```

## Notes

- If `--path` is not provided, files are saved in the current directory.
- Works on Linux and Windows.
- HLS streams from VK (`.m3u8`) are automatically downloaded and converted to `.mp3`.
- Optional metadata enrichment is available via `--metadata-source <source>` or `--metadata-source auto`.
- Metadata sources: `itunes`, `deezer`, `musicbrainz`, `lastfm`, `discogs`, or `auto`.
- `--metadata-source auto` tries sources in this order: `itunes -> deezer -> musicbrainz -> lastfm -> discogs`.
- `lastfm` requires `LASTFM_API_KEY`, `discogs` requires `DISCOGS_TOKEN`.
- If external metadata is not found, script falls back to filename parsing (`Artist - Title.mp3`) for ID3 `artist`/`title`.
- In `--playlist` and `--user` modes, failed tracks are skipped and written to `_skipped.txt` in target directory.
