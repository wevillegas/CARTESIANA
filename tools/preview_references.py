"""Genera copias JPEG para inspección; nunca escribe dentro de referencias."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools' / 'image_reader'))
from PIL import Image, ImageOps, ImageDraw
import pillow_heif

pillow_heif.register_heif_opener()
output = ROOT / 'docs' / 'reference_previews'
output.mkdir(parents=True, exist_ok=True)
files = sorted((ROOT / 'referencias').glob('*.HEIC'))
sheet = Image.new('RGB', (1600, 420 * ((len(files) + 3) // 4)), '#e8e8e8')
draw = ImageDraw.Draw(sheet)
for index, source in enumerate(files):
    with Image.open(source) as original:
        preview = ImageOps.exif_transpose(original).convert('RGB')
        preview.thumbnail((1600, 1600))
        preview.save(output / (source.stem + '.jpg'), quality=90)
        preview.thumbnail((390, 385))
        x, y = (index % 4) * 400, (index // 4) * 420
        sheet.paste(preview, (x + (400 - preview.width) // 2, y + 25))
        draw.text((x + 10, y + 5), source.name, fill='black')
sheet.save(output / 'contact_sheet.jpg', quality=92)
print(output / 'contact_sheet.jpg')
