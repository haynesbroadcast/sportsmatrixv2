"""Pixel-level regression tests for reusable logo keylines and global pips."""
import unittest
from PIL import Image, ImageDraw

from render.logo_contrast import composite_logo
from render.page_indicator import draw_page_indicator


class LogoContrastTests(unittest.TestCase):
    def test_dark_logo_on_dark_background_gets_light_keyline(self):
        frame = Image.new("RGBA", (128, 64), (7, 18, 44, 255))
        logo = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        ImageDraw.Draw(logo).rectangle((2, 2, 5, 5),
                                       fill=(10, 25, 70, 255))
        self.assertTrue(composite_logo(frame, logo, 30, 20))
        self.assertGreater(frame.getpixel((31, 23))[0], 200)
        self.assertEqual(frame.getpixel((33, 23))[:3], (10, 25, 70))
        self.assertEqual(frame.getpixel((30, 20))[:3], (7, 18, 44))

    def test_bright_logo_on_dark_background_preserves_clear_edges(self):
        frame = Image.new("RGBA", (128, 64), (7, 18, 44, 255))
        logo = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        ImageDraw.Draw(logo).rectangle((2, 2, 5, 5),
                                       fill=(255, 255, 255, 255))
        composite_logo(frame, logo, 30, 20)
        self.assertEqual(frame.getpixel((31, 23))[:3], (7, 18, 44))
        self.assertEqual(frame.getpixel((33, 23))[:3], (255, 255, 255))

    def test_transparent_logo_is_ignored(self):
        frame = Image.new("RGBA", (128, 64), (7, 18, 44, 255))
        self.assertFalse(composite_logo(frame, Image.new("RGBA", (5, 5)), 2, 2))


class GlobalPageMarkerTests(unittest.TestCase):
    def test_seven_pages_highlights_fifth(self):
        frame = Image.new("RGB", (128, 64), "#123456")
        draw_page_indicator(frame, 4, 7)
        for index in range(7):
            pixel = frame.getpixel((2 + index * 4, 63))
            self.assertEqual(pixel, (245, 245, 245) if index == 4
                             else (65, 77, 94))

    def test_single_page_omits_marker(self):
        frame = Image.new("RGB", (128, 64), "#123456")
        before = frame.tobytes()
        draw_page_indicator(frame, 0, 1)
        self.assertEqual(frame.tobytes(), before)


if __name__ == "__main__":
    unittest.main()
