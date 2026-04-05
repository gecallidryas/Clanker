import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))
sys.path.insert(0, str(ROOT))

from utils.petpet import make_petpet


def _build_source_png_bytes(size: tuple[int, int] = (120, 180)) -> bytes:
    image = Image.new("RGBA", size, (240, 120, 160, 255))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


class PetpetTests(unittest.TestCase):
    def test_make_petpet_returns_multi_frame_gif_bytes_from_bytes(self):
        payload = _build_source_png_bytes()

        gif_bytes = make_petpet(payload)

        self.assertIsInstance(gif_bytes, bytes)
        self.assertGreater(len(gif_bytes), 0)

        with Image.open(BytesIO(gif_bytes)) as gif:
            self.assertEqual(gif.format, "GIF")
            self.assertGreater(gif.n_frames, 1)

    def test_make_petpet_accepts_file_path(self):
        payload = _build_source_png_bytes((180, 120))

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
            handle.write(payload)
            temp_path = Path(handle.name)

        try:
            gif_bytes = make_petpet(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

        self.assertIsInstance(gif_bytes, bytes)
        self.assertGreater(len(gif_bytes), 0)

        with Image.open(BytesIO(gif_bytes)) as gif:
            self.assertEqual(gif.format, "GIF")
            self.assertGreater(gif.n_frames, 1)


if __name__ == "__main__":
    unittest.main()
