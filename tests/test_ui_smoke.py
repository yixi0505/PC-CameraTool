import tkinter as tk
import unittest

import numpy as np

from camera_tool.camera import CameraDevice
from camera_tool.ui import CameraToolWindow


class FakeMultiCameraService:
    def __init__(self) -> None:
        self.devices = [CameraDevice(0), CameraDevice(1), CameraDevice(2)]
        self.opened: set[int] = set()
        self.frame = np.zeros((48, 64, 3), dtype=np.uint8)

    @property
    def active_indexes(self) -> tuple[int, ...]:
        return tuple(sorted(self.opened))

    def discover(self) -> list[CameraDevice]:
        return self.devices

    def open(self, device: CameraDevice) -> bool:
        self.opened.add(device.index)
        return True

    def read(self, index: int):
        return self.frame if index in self.opened else None

    def close(self, index: int | None = None) -> None:
        if index is None:
            self.opened.clear()
        else:
            self.opened.discard(index)


class CameraToolWindowSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"当前环境无法创建 Tk 窗口：{exc}")
        self.root.withdraw()
        self.window = CameraToolWindow(self.root, FakeMultiCameraService())

    def tearDown(self) -> None:
        if hasattr(self, "root") and self.root.winfo_exists():
            self.window.close()

    def test_window_has_no_application_minimum_size(self):
        self.assertEqual(self.root.minsize(), (1, 1))

    def test_switch_camera_after_render_then_switch_modes(self):
        self.window.refresh_devices()
        self.window._update_frames()
        self.assertEqual(self.window.drawer_button.winfo_manager(), "")

        self.window.camera_combo.current(1)
        self.window.open_selected_camera()
        self.window._update_frames()

        self.window.mode_var.set("multi")
        self.window._on_mode_changed()
        self.assertTrue(self.window._drawer_visible)
        self.assertEqual(self.window.drawer_button.cget("text"), "多路设置")
        self.assertEqual(self.window.drawer_button.winfo_manager(), "pack")
        self.assertEqual(self.window.tiles, {})

        self.window.apply_multi_selection()
        self.assertEqual(set(self.window.tiles), {0, 1, 2})
        self.assertFalse(self.window._drawer_visible)
        self.window._update_frames()

        self.window._toggle_multi_drawer()
        self.assertTrue(self.window._drawer_visible)
        three_camera_grid = self.window.video_grid
        self.window._multi_vars[2].set(False)
        self.window.apply_multi_selection()
        self.assertEqual(set(self.window.tiles), {0, 1})
        self.assertFalse(self.window._drawer_visible)
        self.assertFalse(three_camera_grid.winfo_exists())
        self.assertEqual(self.window.video_grid.grid_size(), (2, 1))

        self.window._toggle_multi_drawer()
        two_camera_grid = self.window.video_grid
        self.window._multi_vars[1].set(False)
        self.window.apply_multi_selection()
        self.assertEqual(set(self.window.tiles), {0})
        self.assertFalse(two_camera_grid.winfo_exists())
        self.assertEqual(self.window.video_grid.grid_size(), (1, 1))

        self.window.mode_var.set("single")
        self.window._on_mode_changed()
        self.assertEqual(set(self.window.tiles), {1})
        self.assertFalse(self.window._drawer_visible)
        self.assertEqual(self.window.drawer_button.winfo_manager(), "")
        self.window._update_frames()
        self.assertIsNotNone(self.window.tiles[1]._photo)
        self.assertLessEqual(self.window.tiles[1].video.winfo_reqwidth(), 2)
        self.assertLessEqual(self.window.tiles[1].video.winfo_reqheight(), 2)


if __name__ == "__main__":
    unittest.main()
