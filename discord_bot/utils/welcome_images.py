from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


REPO_ROOT = Path(__file__).resolve().parents[2]
CATMUNCH_DIR_CANDIDATES = (
    REPO_ROOT / "catmunch",
    REPO_ROOT.parents[1] / "catmunch" if len(REPO_ROOT.parents) > 1 else REPO_ROOT / "catmunch",
)
PETPET_ASSET_DIR_CANDIDATES = (
    REPO_ROOT / "PETTING hand frames and base gif",
    REPO_ROOT.parents[1] / "PETTING hand frames and base gif"
    if len(REPO_ROOT.parents) > 1
    else REPO_ROOT / "PETTING hand frames and base gif",
)
PETPET_FRAME_NAMES = tuple(f"frame_{index}_delay-0.06s.gif" for index in range(5))
PETPET_FRAME_TABLE = (
    (18, 22, 72, 72),
    (15, 28, 76, 66),
    (13, 34, 80, 60),
    (15, 30, 76, 64),
    (18, 24, 72, 70),
)
PETPET_FRAME_DURATION_MS = 60
PETPET_CANVAS_SIZE = (107, 106)
CATMUNCH_AVATAR_BBOX = (159, 401, 632, 874)
CATMUNCH_AVATAR_SCALE = 1.0
CATMUNCH_AVATAR_OFFSET_X = 0
CATMUNCH_AVATAR_OFFSET_Y = 0
CATMUNCH_TEXT_CENTER_X = 512
CATMUNCH_TOP_TEXT_Y = 88
CATMUNCH_SUBTITLE_Y = 180
CATMUNCH_BOTTOM_TEXT_Y = 872
CATMUNCH_NAME_FONT_SIZE = 88
CATMUNCH_TEXT_FONT_SIZE = 64
CATMUNCH_TEXT_FILL = "#ffffff"
CATMUNCH_TEXT_STROKE = "#000000"


@dataclass(frozen=True)
class WelcomeImagePayload:
    data: bytes
    filename: str
    content_type: str


def render_welcome_image(
    *,
    template: str,
    avatar_bytes: bytes,
    member_name: str,
    join_ordinal: str,
) -> WelcomeImagePayload:
    normalized = (template or "pettinghand").strip().lower()
    if normalized == "catmunch":
        return _render_catmunch(
            avatar_bytes=avatar_bytes,
            member_name=member_name,
            join_ordinal=join_ordinal,
        )
    if normalized == "pettinghand":
        return WelcomeImagePayload(
            data=make_petpet(avatar_bytes),
            filename="pettinghand.gif",
            content_type="image/gif",
        )
    raise ValueError(f"Unsupported welcome image template: {template}")


def _render_catmunch(*, avatar_bytes: bytes, member_name: str, join_ordinal: str) -> WelcomeImagePayload:
    template_path, font_path = _find_catmunch_assets()

    with Image.open(template_path) as template_image:
        base = template_image.convert("RGBA")

    avatar = prepare_image(avatar_bytes)
    circle_avatar = _render_circle_avatar(avatar)

    composite = Image.new("RGBA", base.size, (0, 0, 0, 0))
    composite.alpha_composite(circle_avatar, CATMUNCH_AVATAR_BBOX[:2])
    composite.alpha_composite(base)

    draw = ImageDraw.Draw(composite)
    name_font = _load_font(font_path, CATMUNCH_NAME_FONT_SIZE)
    text_font = _load_font(font_path, CATMUNCH_TEXT_FONT_SIZE)
    _draw_centered_text(draw, member_name, name_font, CATMUNCH_TOP_TEXT_Y)
    _draw_centered_text(draw, "joined the server", text_font, CATMUNCH_SUBTITLE_Y)
    _draw_centered_text(draw, f"snacknumber#{join_ordinal}", text_font, CATMUNCH_BOTTOM_TEXT_Y)

    buffer = BytesIO()
    composite.save(buffer, format="PNG")
    return WelcomeImagePayload(
        data=buffer.getvalue(),
        filename="catmunch.png",
        content_type="image/png",
    )


def _render_circle_avatar(avatar: Image.Image) -> Image.Image:
    left, top, right, bottom = CATMUNCH_AVATAR_BBOX
    width = right - left
    height = bottom - top
    x, y, size = _compute_catmunch_avatar_geometry()
    resized = avatar.resize((size, size), Image.Resampling.LANCZOS)
    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    mask = Image.new("L", (width, height), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((x, y, x + size - 1, y + size - 1), fill=255)
    avatar_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    avatar_layer.alpha_composite(resized, (x, y))
    return Image.composite(avatar_layer, layer, mask)


def _compute_catmunch_avatar_geometry() -> tuple[int, int, int]:
    left, top, right, bottom = CATMUNCH_AVATAR_BBOX
    width = right - left
    height = bottom - top
    opening = min(width, height)
    size = int(round(opening * CATMUNCH_AVATAR_SCALE))
    x = ((width - size) // 2) + CATMUNCH_AVATAR_OFFSET_X
    y = ((height - size) // 2) + CATMUNCH_AVATAR_OFFSET_Y
    return x, y, size


def _find_catmunch_assets() -> tuple[Path, Path]:
    for candidate in CATMUNCH_DIR_CANDIDATES:
        template_path = candidate / "cattomunch (2).png"
        font_path = candidate / "ArtistsAlleyBB.otf"
        if template_path.exists() and font_path.exists():
            return template_path, font_path
    raise FileNotFoundError("Catmunch welcome image assets were not found")


def _load_font(font_path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(font_path), size=size)


def _draw_centered_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, y: int) -> None:
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=4)
    width = bbox[2] - bbox[0]
    x = CATMUNCH_TEXT_CENTER_X - (width // 2)
    draw.text(
        (x, y),
        text,
        font=font,
        fill=CATMUNCH_TEXT_FILL,
        stroke_width=4,
        stroke_fill=CATMUNCH_TEXT_STROKE,
    )


def prepare_image(image_bytes: bytes) -> Image.Image:
    with Image.open(BytesIO(image_bytes)) as image:
        rgba = image.convert("RGBA")

    side = min(rgba.width, rgba.height)
    left = (rgba.width - side) // 2
    top = (rgba.height - side) // 2
    cropped = rgba.crop((left, top, left + side, top + side))
    return cropped.resize((128, 128), Image.Resampling.LANCZOS)


def make_petpet(image_bytes: bytes) -> bytes:
    return _save_gif(_render_petpet_frames(image_bytes))


def _find_petpet_asset_dir() -> Path:
    for candidate in PETPET_ASSET_DIR_CANDIDATES:
        if all((candidate / name).exists() for name in PETPET_FRAME_NAMES):
            return candidate
    raise FileNotFoundError("Petpet hand frame assets were not found")


def _load_petpet_frames() -> list[Image.Image]:
    asset_dir = _find_petpet_asset_dir()
    frames: list[Image.Image] = []
    for name in PETPET_FRAME_NAMES:
        with Image.open(asset_dir / name) as image:
            frames.append(image.convert("RGBA"))
    return frames


def _render_petpet_frames(image_bytes: bytes) -> list[Image.Image]:
    avatar = prepare_image(image_bytes)
    hand_frames = _load_petpet_frames()
    frames: list[Image.Image] = []
    for geometry, hand_frame in zip(PETPET_FRAME_TABLE, hand_frames):
        frame = _render_petpet_avatar_frame(avatar, geometry)
        frame.alpha_composite(hand_frame)
        frames.append(frame)
    return frames


def _render_petpet_avatar_frame(avatar: Image.Image, geometry: tuple[int, int, int, int]) -> Image.Image:
    canvas = Image.new("RGBA", PETPET_CANVAS_SIZE, (0, 0, 0, 0))
    x, y, width, height = geometry
    resized = avatar.resize((width, height), Image.Resampling.LANCZOS)

    avatar_layer = Image.new("RGBA", PETPET_CANVAS_SIZE, (0, 0, 0, 0))
    avatar_layer.alpha_composite(resized, (x, y))

    mask = Image.new("L", PETPET_CANVAS_SIZE, 0)
    ImageDraw.Draw(mask).ellipse((x, y, x + width - 1, y + height - 1), fill=255)
    return Image.composite(avatar_layer, canvas, mask)


def _save_gif(frames: Iterable[Image.Image]) -> bytes:
    frame_list = list(frames)
    if not frame_list:
        raise ValueError("No petpet frames were rendered")

    output = BytesIO()
    frame_list[0].save(
        output,
        format="GIF",
        save_all=True,
        append_images=frame_list[1:],
        duration=PETPET_FRAME_DURATION_MS,
        loop=0,
        disposal=2,
        transparency=0,
    )
    output.seek(0)
    return output.getvalue()
