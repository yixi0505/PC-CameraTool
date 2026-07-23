import tkinter as tk

from camera_tool.camera import CameraService
from camera_tool.ui import CameraToolWindow


def main() -> None:
    root = tk.Tk()
    CameraToolWindow(root, CameraService())
    root.mainloop()
