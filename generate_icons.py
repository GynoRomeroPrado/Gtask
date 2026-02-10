"""Genera iconos PWA para Cerebro Operativo usando PIL/Pillow"""
import sys
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Instalando Pillow...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow", "-q"])
    from PIL import Image, ImageDraw, ImageFont

import os

SIZES = [72, 96, 128, 144, 152, 192, 384, 512]
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "frontend", "icons")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_icon(size):
    """Crea un icono con gradiente morado y emoji de cerebro"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Fondo con gradiente circular (simulado)
    center = size // 2
    for r in range(center, 0, -1):
        ratio = r / center
        # Gradiente de morado oscuro a morado brillante
        red = int(139 * (1 - ratio * 0.6))
        green = int(92 * (1 - ratio * 0.7))
        blue = int(246 * (1 - ratio * 0.3))
        draw.ellipse(
            [center - r, center - r, center + r, center + r],
            fill=(red, green, blue, 255)
        )
    
    # Borde redondeado (esquinas)
    corner_radius = size // 5
    mask = Image.new('L', (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([0, 0, size-1, size-1], corner_radius, fill=255)
    img.putalpha(mask)
    
    # Texto "CO" en el centro
    font_size = size // 3
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except (IOError, OSError):
        try:
            font = ImageFont.truetype("C:\\Windows\\Fonts\\arialbd.ttf", font_size)
        except (IOError, OSError):
            font = ImageFont.load_default()
    
    text = "CO"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (size - tw) // 2
    ty = (size - th) // 2 - bbox[1]
    
    # Sombra
    draw.text((tx + 2, ty + 2), text, fill=(0, 0, 0, 100), font=font)
    # Texto blanco
    draw.text((tx, ty), text, fill=(255, 255, 255, 255), font=font)
    
    return img

for s in SIZES:
    icon = create_icon(s)
    path = os.path.join(OUTPUT_DIR, f"icon-{s}.png")
    icon.save(path, "PNG")
    print(f"✅ icon-{s}.png generado")

print(f"\n🎯 {len(SIZES)} iconos generados en {OUTPUT_DIR}")
