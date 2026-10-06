"""Rasterize the existing approved artwork geometry; never generate backgrounds."""

from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


def render_post(content: dict[str, Any], *, assets: Path, fonts: Path) -> bytes:
    template = content["template"]
    spec = template["formats"]["post"]
    name = Path(spec["background"]).name
    background = (assets / name).resolve()
    if background.parent != assets.resolve():
        raise ValueError("Invalid artwork path")
    with Image.open(background) as source:
        artwork = source.convert("RGB").resize((spec["width"], spec["height"]))
    draw = ImageDraw.Draw(artwork)
    for key, box in spec["zones"].items():
        text = content["fields"].get(key, "").strip()
        if not text:
            continue
        x, y, width, height = box
        font_name = (
            "DejaVuSerif.ttf"
            if key == "title" and template["serif"]
            else "DejaVuSans.ttf"
        )
        size = spec["fonts"][key]
        while size >= 10:
            font = ImageFont.truetype(str(fonts / font_name), size)
            lines: list[str] = []
            line = ""
            for word in text.split():
                candidate = f"{line} {word}".strip()
                if draw.textlength(candidate, font=font) > width and line:
                    lines.append(line)
                    line = word
                else:
                    line = candidate
            lines.append(line)
            if len(lines) * size * 1.18 <= height and all(
                draw.textlength(item, font=font) <= width for item in lines
            ):
                break
            size -= 1
        else:
            raise ValueError("Publication text does not fit approved geometry")
        centered = template.get("textAlign") == "center"
        if centered:
            y += max(0, (height - len(lines) * size * 1.18) / 2)
        color = template["accent"] if key in ("kicker", "value") else template["light"]
        for line in lines:
            offset = (width - draw.textlength(line, font=font)) / 2 if centered else 0
            draw.text((x + offset, y), line, font=font, fill=color, anchor="lt")
            y += size * 1.18
    output = BytesIO()
    artwork.save(output, format="PNG", optimize=True)
    return output.getvalue()
