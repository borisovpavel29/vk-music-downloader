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

Save to specific directory:

```bash
python vk_audio_downloader.py --track <TRACK_URL> --path ./downloads --token <VK_TOKEN>
```

Choose behavior if file already exists (`skip` by default):

```bash
python vk_audio_downloader.py --playlist <PLAYLIST_URL> --if-exists replace --token <VK_TOKEN>
```

You can set token via environment variable:

Linux/macOS:

```bash
export VK_TOKEN=<VK_TOKEN>
python vk_audio_downloader.py --track <TRACK_URL>
```

Windows PowerShell:

```powershell
$env:VK_TOKEN="<VK_TOKEN>"
python vk_audio_downloader.py --track <TRACK_URL>
```

## Notes

- If `--path` is not provided, files are saved in the current directory.
- Works on Linux and Windows.
- HLS streams from VK (`.m3u8`) are automatically downloaded and converted to `.mp3`.
