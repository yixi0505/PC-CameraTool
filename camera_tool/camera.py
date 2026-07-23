from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import platform
from typing import Callable, Iterator, Protocol

import cv2
from numpy.typing import NDArray


class Capture(Protocol):
    def isOpened(self) -> bool: ...

    def read(self) -> tuple[bool, NDArray | None]: ...

    def release(self) -> None: ...

    def set(self, prop_id: int, value: float) -> bool: ...


CaptureFactory = Callable[..., Capture]


@dataclass(frozen=True, slots=True)
class CameraDevice:
    index: int
    backend: int = cv2.CAP_ANY

    @property
    def display_name(self) -> str:
        return f"摄像头 {self.index}"


class CameraService:
    """负责摄像头发现及一路或多路视频流的生命周期管理。"""

    def __init__(
        self,
        max_devices: int = 10,
        capture_factory: CaptureFactory = cv2.VideoCapture,
        backend: int | None = None,
    ) -> None:
        self.max_devices = max_devices
        self._capture_factory = capture_factory
        self._backends = (
            (backend,) if backend is not None else self._default_backends()
        )
        self._captures: dict[int, Capture] = {}

    @staticmethod
    def _default_backends() -> tuple[int, ...]:
        if platform.system() == "Windows":
            # MSMF 对按编号打开设备的兼容性更好，DSHOW 作为旧设备回退方案。
            return cv2.CAP_MSMF, cv2.CAP_DSHOW
        return (cv2.CAP_ANY,)

    @property
    def active_indexes(self) -> tuple[int, ...]:
        return tuple(self._captures)

    @property
    def active_index(self) -> int | None:
        """兼容单路模式，返回当前首个活动设备编号。"""
        return next(iter(self._captures), None)

    def _create_capture(self, index: int, backend: int) -> Capture:
        if backend == cv2.CAP_ANY:
            return self._capture_factory(index)
        return self._capture_factory(index, backend)

    @staticmethod
    @contextmanager
    def _quiet_opencv() -> Iterator[None]:
        """无效探测编号由应用处理，不把 VideoIO 警告打印到控制台。"""
        get_level = getattr(cv2, "getLogLevel", None)
        set_level = getattr(cv2, "setLogLevel", None)
        if get_level is None or set_level is None:
            yield
            return

        previous_level = get_level()
        try:
            set_level(0)
            yield
        finally:
            set_level(previous_level)

    def _try_backend(self, index: int, backend: int) -> Capture | None:
        capture = self._create_capture(index, backend)
        if capture.isOpened():
            return capture
        capture.release()
        return None

    def discover(self) -> list[CameraDevice]:
        """扫描有限编号范围，并记住各设备实际可用的视频后端。"""
        devices: list[CameraDevice] = []
        with self._quiet_opencv():
            for index in range(self.max_devices):
                for backend in self._backends:
                    capture = self._try_backend(index, backend)
                    if capture is None:
                        continue
                    devices.append(CameraDevice(index=index, backend=backend))
                    capture.release()
                    break
        return devices

    def open(self, device: CameraDevice | int) -> bool:
        """打开指定设备；其他已打开设备保持运行，以支持多路显示。"""
        if isinstance(device, int):
            index = device
            backends = self._backends
        else:
            index = device.index
            preferred = (device.backend,)
            backends = preferred + tuple(
                backend for backend in self._backends if backend not in preferred
            )

        self.close(index)
        with self._quiet_opencv():
            for backend in backends:
                capture = self._try_backend(index, backend)
                if capture is None:
                    continue
                capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                self._captures[index] = capture
                return True
        return False

    def read(self, index: int | None = None) -> NDArray | None:
        if index is None:
            index = self.active_index
        if index is None:
            return None

        capture = self._captures.get(index)
        if capture is None:
            return None
        success, frame = capture.read()
        return frame if success else None

    def close(self, index: int | None = None) -> None:
        if index is None:
            captures = list(self._captures.values())
            self._captures.clear()
            for capture in captures:
                capture.release()
            return

        capture = self._captures.pop(index, None)
        if capture is not None:
            capture.release()
