from __future__ import annotations

from io import BytesIO
from os import PathLike
from pathlib import Path

from PIL import Image

WORKING_SIZE = 96
CANVAS_SIZE = 112
HAND_DIR = Path(__file__).resolve().parents[1] / "assets" / "petpet"
HAND_FRAME_NAMES = [f"frame_{index}_delay-0.06s.gif" for index in range(5)]


def prepare_image(source: bytes | str | PathLike[str]) -> Image.Image:
    if isinstance(source, (str, PathLike)):
        with Image.open(source) as image:
            base = image.convert("RGBA")
    else:
        with Image.open(BytesIO(source)) as image:
            base = image.convert("RGBA")

    width, height = base.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    cropped = base.crop((left, top, left + side, top + side))
    return cropped.resize((WORKING_SIZE, WORKING_SIZE), Image.Resampling.LANCZOS)


def load_hand_frames() -> list[Image.Image]:
    frames: list[Image.Image] = []
    for name in HAND_FRAME_NAMES:
        path = HAND_DIR / name
        with Image.open(path) as image:
            frame = image.convert("RGBA")
        if frame.size != (CANVAS_SIZE, CANVAS_SIZE):
            frame = frame.resize((CANVAS_SIZE, CANVAS_SIZE), Image.Resampling.LANCZOS)
        frames.append(frame)
    return frames


def render_petpet_frames(base_image: Image.Image, hand_frames: list[Image.Image]) -> list[Image.Image]:
    frame_table = [
        (16, 14, 80, 80, 0),
        (15, 16, 82, 78, 1),
        (14, 18, 84, 74, 2),
        (15, 16, 82, 78, 3),
        (16, 14, 80, 80, 4),
    ]
    frames: list[Image.Image] = []
    for x, y, width, height, hand_index in frame_table:
        canvas = Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (0, 0, 0, 0))
        resized = base_image.resize((width, height), Image.Resampling.LANCZOS)
        canvas.alpha_composite(resized, (x, y))
        canvas.alpha_composite(hand_frames[hand_index], (0, 0))
        frames.append(canvas)
    return frames


def save_gif(frames: list[Image.Image]) -> bytes:
    if not frames:
        raise ValueError("No frames to save.")

    output = BytesIO()
    duration = [45] * len(frames)
    frames[0].save(
        output,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=duration,
        loop=0,
        disposal=2,
        optimize=False,
    )
    return output.getvalue()


def make_petpet(source: bytes | str | PathLike[str]) -> bytes:
    base_image = prepare_image(source)
    hand_frames = load_hand_frames()
    frames = render_petpet_frames(base_image, hand_frames)
    return save_gif(frames)
