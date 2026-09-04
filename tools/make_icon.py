"""Generate the Himaya app icon (shield + checkmark) as PNG + ICO."""
from PIL import Image, ImageDraw

S = 512
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# dark rounded square background
d.rounded_rectangle([16, 16, S - 16, S - 16], radius=90, fill=(20, 22, 26, 255))

# shield (green)
shield = [
    (256, 88), (392, 132), (392, 236),
    (392, 330), (256, 428), (120, 330), (120, 236), (120, 132),
]
d.polygon(shield, fill=(46, 204, 113, 255))
# inner darker shield line
inner = [
    (256, 116), (368, 152), (368, 238),
    (368, 316), (256, 398), (144, 316), (144, 238), (144, 152),
]
d.polygon(inner, fill=(34, 175, 95, 255))
# checkmark (dark)
d.line([(198, 258), (240, 306), (322, 196)], fill=(16, 22, 18, 255), width=34,
       joint="curve")
d.ellipse([188, 248, 208, 268], fill=(16, 22, 18, 255))
d.ellipse([230, 296, 250, 316], fill=(16, 22, 18, 255))

img.save("assets/icon.png")
img.save("assets/icon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64),
                                   (128, 128), (256, 256)])
print("icon written")
