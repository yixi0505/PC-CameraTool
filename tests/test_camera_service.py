import unittest

import cv2

from camera_tool.camera import CameraDevice, CameraService


class FakeCapture:
    def __init__(self, opened: bool, frame=None) -> None:
        self.opened = opened
        self.frame = frame
        self.released = False
        self.properties: list[tuple[int, float]] = []

    def isOpened(self) -> bool:
        return self.opened

    def read(self):
        return self.frame is not None, self.frame

    def release(self) -> None:
        self.released = True

    def set(self, prop_id: int, value: float) -> bool:
        self.properties.append((prop_id, value))
        return True


class CaptureFactory:
    def __init__(self, available: set[tuple[int, int]]) -> None:
        self.available = available
        self.created: list[tuple[int, int, FakeCapture]] = []

    def __call__(self, index: int, backend: int = cv2.CAP_ANY) -> FakeCapture:
        capture = FakeCapture(
            opened=(index, backend) in self.available,
            frame=f"frame-{index}-{backend}",
        )
        self.created.append((index, backend, capture))
        return capture


class CameraServiceTests(unittest.TestCase):
    def test_discover_returns_only_openable_devices_and_releases_probes(self):
        factory = CaptureFactory({(0, cv2.CAP_ANY), (2, cv2.CAP_ANY)})
        service = CameraService(
            max_devices=4, capture_factory=factory, backend=cv2.CAP_ANY
        )

        devices = service.discover()

        self.assertEqual([device.index for device in devices], [0, 2])
        self.assertTrue(all(capture.released for _, _, capture in factory.created))

    def test_open_multiple_devices_and_close_one(self):
        factory = CaptureFactory({(0, cv2.CAP_ANY), (1, cv2.CAP_ANY)})
        service = CameraService(
            max_devices=2, capture_factory=factory, backend=cv2.CAP_ANY
        )

        self.assertTrue(service.open(CameraDevice(0)))
        self.assertTrue(service.open(CameraDevice(1)))
        self.assertEqual(service.active_indexes, (0, 1))
        self.assertEqual(service.read(0), f"frame-0-{cv2.CAP_ANY}")
        self.assertEqual(service.read(1), f"frame-1-{cv2.CAP_ANY}")

        first_capture = factory.created[0][2]
        second_capture = factory.created[1][2]
        service.close(0)

        self.assertTrue(first_capture.released)
        self.assertFalse(second_capture.released)
        self.assertEqual(service.active_indexes, (1,))

        service.close()
        self.assertTrue(second_capture.released)
        self.assertEqual(service.active_indexes, ())

    def test_open_uses_device_backend_then_falls_back(self):
        factory = CaptureFactory({(2, cv2.CAP_DSHOW)})
        service = CameraService(
            max_devices=3, capture_factory=factory, backend=cv2.CAP_DSHOW
        )

        self.assertTrue(service.open(CameraDevice(2, cv2.CAP_MSMF)))

        attempted_backends = [backend for _, backend, _ in factory.created]
        self.assertEqual(attempted_backends, [cv2.CAP_MSMF, cv2.CAP_DSHOW])
        self.assertEqual(service.active_indexes, (2,))

    def test_failed_open_is_released_and_not_marked_active(self):
        factory = CaptureFactory(set())
        service = CameraService(
            max_devices=1, capture_factory=factory, backend=cv2.CAP_ANY
        )

        self.assertFalse(service.open(0))

        self.assertTrue(factory.created[0][2].released)
        self.assertEqual(service.active_indexes, ())


if __name__ == "__main__":
    unittest.main()
