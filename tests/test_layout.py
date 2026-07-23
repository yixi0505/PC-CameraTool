import unittest

from camera_tool.layout import fit_size, grid_positions, grid_shape


class GridLayoutTests(unittest.TestCase):
    def test_fit_size_upscales_to_available_area(self):
        self.assertEqual(fit_size(640, 480, 1280, 900), (1200, 900))

    def test_fit_size_downscales_and_preserves_aspect_ratio(self):
        self.assertEqual(fit_size(1920, 1080, 800, 600), (800, 450))

    def test_fit_size_handles_portrait_viewport(self):
        self.assertEqual(fit_size(640, 480, 400, 700), (400, 300))

    def test_fit_size_handles_unavailable_geometry(self):
        self.assertEqual(fit_size(640, 480, 0, 0), (1, 1))

    def test_grid_shapes_are_balanced(self):
        expected = {
            0: (0, 0),
            1: (1, 1),
            2: (1, 2),
            3: (2, 2),
            4: (2, 2),
            5: (2, 3),
            6: (2, 3),
            7: (3, 3),
        }
        for item_count, shape in expected.items():
            with self.subTest(item_count=item_count):
                self.assertEqual(grid_shape(item_count), shape)

    def test_positions_fill_rows_from_left_to_right(self):
        self.assertEqual(
            grid_positions(5),
            [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1)],
        )


if __name__ == "__main__":
    unittest.main()
