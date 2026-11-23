import base64
import json
from pathlib import Path
from .main import catalog

ROOT = Path(__file__).parent


def render(server=False):
    text = (ROOT / 'studio.html').read_text()
    art = {p.stem: 'data:image/webp;base64,' + base64.b64encode(p.read_bytes()).decode() for p in sorted((ROOT/'art').glob('*.webp'))}
    for key, value in [('__ART_DATA__', json.dumps(art)), ('__CATALOG_DATA__', json.dumps(catalog()).replace('<', r'\u003c')), ('__ENGINE__', (ROOT/'engine.js').read_text()), ('__UI__', 'window.STUDIO_SERVER='+json.dumps(server)+';\n'+(ROOT/'ui.js').read_text())]:
        text = text.replace(key, value)
    return text
