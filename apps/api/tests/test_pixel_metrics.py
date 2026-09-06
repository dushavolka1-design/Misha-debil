"""Exact synthetic raster equivalence; not official-form acceptance."""

import random
import unittest

from PIL import Image

from app.services.forms.fill.pixel_metrics import rgb_difference_metrics


def reference(image: Image.Image) -> tuple[int, int]:
    data = image.tobytes()
    pixels = list(zip(data[0::3], data[1::3], data[2::3], strict=True))
    return max((max(pixel) for pixel in pixels), default=0), sum(pixel != (0, 0, 0) for pixel in pixels)


class PixelMetricsTests(unittest.TestCase):
    def test_black_image_has_no_difference(self) -> None:
        self.assertEqual(rgb_difference_metrics(Image.new("RGB", (8, 5))), (0, 0))

    def test_single_channel_changes_are_not_lost(self) -> None:
        for channel in range(3):
            for delta in (1, 2, 3, 254, 255):
                with self.subTest(channel=channel, delta=delta):
                    pixel = [0, 0, 0]
                    pixel[channel] = delta
                    image = Image.new("RGB", (4, 3))
                    image.putpixel((2, 1), tuple(pixel))
                    self.assertEqual(rgb_difference_metrics(image), (delta, 1))

    def test_changed_pixel_is_counted_once(self) -> None:
        image = Image.new("RGB", (2, 2), (1, 2, 255))
        self.assertEqual(rgb_difference_metrics(image), (255, 4))

    def test_every_delta_is_preserved(self) -> None:
        image = Image.frombytes("RGB", (256, 1), b"".join(bytes((0, i, 0)) for i in range(256)))
        self.assertEqual(rgb_difference_metrics(image), (255, 255))

    def test_deterministic_images_match_original_algorithm(self) -> None:
        rng = random.Random(20260906)
        for size in ((1, 1), (17, 13), (64, 32)):
            with self.subTest(size=size):
                image = Image.frombytes("RGB", size, rng.randbytes(size[0] * size[1] * 3))
                self.assertEqual(rgb_difference_metrics(image), reference(image))

    def test_non_rgb_is_rejected_instead_of_miscounted(self) -> None:
        for mode in ("L", "RGBA", "P", "1"):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                rgb_difference_metrics(Image.new(mode, (2, 2)))


if __name__ == "__main__":
    unittest.main()
