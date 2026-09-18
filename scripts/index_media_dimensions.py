"""Index local media dimensions for orientation-based work filters."""
from pathlib import Path
import json
import subprocess
from PIL import Image

root = Path(__file__).resolve().parents[1] / 'mirror'
# Remote asset dimensions verified from the loaded gallery image.
dimensions = {'/1200x/78/98/dc/7898dcfc55cc888c7cfd76aa3783dea8.jpg': [750, 1624]}
for path in sorted((root / '_cdn').rglob('*')):
    if not path.is_file():
        continue
    try:
        if path.suffix.lower() in ('.mp4', '.mov', '.webm', '.m4v'):
            result = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'json', str(path)], capture_output=True, text=True, check=True)
            stream = json.loads(result.stdout)['streams'][0]
            size = [stream['width'], stream['height']]
        else:
            with Image.open(path) as media:
                size = list(media.size)
        dimensions['/' + path.relative_to(root).as_posix()] = size
    except (OSError, ValueError, KeyError, IndexError, subprocess.CalledProcessError):
        continue
(root / 'assets/media-dimensions.js').write_text('export default ' + json.dumps(dimensions, separators=(',', ':')) + ';\n')
print(f'Indexed {len(dimensions)} media files')
