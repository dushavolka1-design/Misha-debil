"""Exact RGB pixel-difference statistics without a Python per-pixel loop."""

from __future__ import annotations

from PIL import Image, ImageChops


def rgb_difference_metrics(image: Image.Image) -> tuple[int, int]:
    """Return (maximum channel delta, number of non-black pixels).

    Combining channels by maximum (not luminance) preserves changes confined
    to a single channel, including a delta of one. A pixel is counted once,
    regardless of how many channels changed. No tolerance is applied here.
    """
    if image.mode != "RGB":
        raise ValueError("Pixel differences must be RGB")
    red, green, blue = image.split()
    maximum = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    histogram = maximum.histogram()
    changed_pixels = sum(histogram[1:])
    max_delta = max((delta for delta, count in enumerate(histogram) if count), default=0)
    return max_delta, changed_pixels
