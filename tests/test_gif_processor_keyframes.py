from io import BytesIO
import asyncio

from PIL import Image

from utils.gif_processor import _calculate_keyframe_indices, extract_gif_keyframes


def _build_test_gif_bytes() -> bytes:
    frame1 = Image.new("RGB", (32, 32), color=(255, 0, 0))
    frame2 = Image.new("RGB", (32, 32), color=(0, 255, 0))
    output = BytesIO()
    frame1.save(
        output,
        format="GIF",
        save_all=True,
        append_images=[frame2],
        duration=[100, 100],
        loop=0,
    )
    return output.getvalue()


def test_extract_gif_keyframes_from_bytes():
    gif_bytes = _build_test_gif_bytes()
    frames = asyncio.run(
        extract_gif_keyframes(
            gif_bytes,
            max_keyframes=5,
            frame_interval=1,
        )
    )
    assert len(frames) >= 2
    assert frames[0]["mime_type"] == "image/jpeg"
    assert isinstance(frames[0]["data"], str)
    assert frames[0]["total_frames"] == 2


def test_calculate_keyframe_indices_respects_single_frame_cap():
    indices = _calculate_keyframe_indices(total_frames=20, interval=5, max_frames=1)
    assert indices == [0]
