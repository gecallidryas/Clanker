from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw


REPO_ROOT = Path(__file__).resolve().parents[2]
ASSET_DIR_CANDIDATES = (
    Path(__file__).resolve().parents[1] / "assets" / "petpet",
    REPO_ROOT / "PETTING hand frames and base gif",
)
FRAME_NAMES = tuple(f"frame_{index}_delay-0.06s.gif" for index in range(5))
FRAME_TABLE = (
    (18, 22, 72, 72),
    (15, 28, 76, 66),
    (13, 34, 80, 60),
    (15, 30, 76, 64),
    (18, 24, 72, 70),
)
FRAME_DURATION_MS = 60
CANVAS_SIZE = (107, 106)


def _find_asset_dir() -> Path:
    for candidate in ASSET_DIR_CANDIDATES:
        if all((candidate / name).exists() for name in FRAME_NAMES):
            return candidate
    raise FileNotFoundError("Petpet hand frame assets were not found")


def _load_hand_frames() -> list[Image.Image]:
    asset_dir = _find_asset_dir()
    frames: list[Image.Image] = []
    for name in FRAME_NAMES:
        with Image.open(asset_dir / name) as image:
            frames.append(image.convert("RGBA"))
    return frames


def prepare_image(image_bytes: bytes) -> Image.Image:
    with Image.open(BytesIO(image_bytes)) as image:
        rgba = image.convert("RGBA")

    side = min(rgba.width, rgba.height)
    left = (rgba.width - side) // 2
    top = (rgba.height - side) // 2
    cropped = rgba.crop((left, top, left + side, top + side))
    return cropped.resize((128, 128), Image.Resampling.LANCZOS)


def _render_avatar_frame(avatar: Image.Image, geometry: tuple[int, int, int, int]) -> Image.Image:
    canvas = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    x, y, width, height = geometry
    resized = avatar.resize((width, height), Image.Resampling.LANCZOS)

    avatar_layer = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    avatar_layer.alpha_composite(resized, (x, y))

    mask = Image.new("L", CANVAS_SIZE, 0)
    ImageDraw.Draw(mask).ellipse((x, y, x + width - 1, y + height - 1), fill=255)
    return Image.composite(avatar_layer, canvas, mask)


def render_petpet_frames(image_bytes: bytes) -> list[Image.Image]:
    avatar = prepare_image(image_bytes)
    hand_frames = _load_hand_frames()
    frames: list[Image.Image] = []
    for geometry, hand_frame in zip(FRAME_TABLE, hand_frames):
        frame = _render_avatar_frame(avatar, geometry)
        frame.alpha_composite(hand_frame)
        frames.append(frame)
    return frames


def save_gif(frames: Iterable[Image.Image]) -> bytes:
    frame_list = list(frames)
    if not frame_list:
        raise ValueError("No petpet frames were rendered")

    output = BytesIO()
    frame_list[0].save(
        output,
        format="GIF",
        save_all=True,
        append_images=frame_list[1:],
        duration=FRAME_DURATION_MS,
        loop=0,
        disposal=2,
        transparency=0,
    )
    output.seek(0)
    return output.getvalue()


def make_petpet(image_bytes: bytes) -> bytes:
    return save_gif(render_petpet_frames(image_bytes))
