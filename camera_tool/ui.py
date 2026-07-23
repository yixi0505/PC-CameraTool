from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

import cv2
from PIL import Image, ImageTk

from camera_tool.camera import CameraDevice, CameraService
from camera_tool.layout import fit_size, grid_positions, grid_shape


class VideoTile:
    """单个视频子窗口；画面尺寸不参与父级布局计算。"""

    def __init__(self, parent: tk.Widget, device: CameraDevice) -> None:
        self.device = device
        self.frame = tk.Frame(
            parent,
            bg="#1f2937",
            highlightbackground="#374151",
            highlightthickness=1,
        )
        self.title = tk.Label(
            self.frame,
            text=device.display_name,
            bg="#1f2937",
            fg="#e5e7eb",
            anchor=tk.W,
            padx=10,
            pady=6,
            font=("Microsoft YaHei UI", 9),
        )
        self.title.pack(fill=tk.X)
        self.video = tk.Canvas(
            self.frame,
            bg="#030712",
            width=1,
            height=1,
            borderwidth=0,
            highlightthickness=0,
        )
        self.video.pack(fill=tk.BOTH, expand=True)
        self._image_item = self.video.create_image(
            0, 0, anchor=tk.CENTER, state=tk.HIDDEN
        )
        self._message_item = self.video.create_text(
            0,
            0,
            text="正在连接…",
            fill="#9ca3af",
            font=("Microsoft YaHei UI", 12),
            anchor=tk.CENTER,
        )
        self.video.bind("<Configure>", self._on_canvas_resize)
        self._photo: ImageTk.PhotoImage | None = None

    def _on_canvas_resize(self, event: tk.Event) -> None:
        center = event.width / 2, event.height / 2
        self.video.coords(self._image_item, *center)
        self.video.coords(self._message_item, *center)

    def show_frame(self, bgr_frame) -> None:
        rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb_frame)
        available_width = max(self.video.winfo_width(), 1)
        available_height = max(self.video.winfo_height(), 1)
        target_size = fit_size(
            image.width,
            image.height,
            available_width,
            available_height,
        )
        if image.size != target_size:
            image = image.resize(target_size, Image.Resampling.BILINEAR)
        photo = ImageTk.PhotoImage(image=image, master=self.video)
        self.video.itemconfigure(
            self._image_item, image=photo, state=tk.NORMAL
        )
        self.video.itemconfigure(self._message_item, state=tk.HIDDEN)
        self.video.coords(
            self._image_item,
            available_width / 2,
            available_height / 2,
        )
        self._photo = photo

    def show_message(self, text: str) -> None:
        # 必须先让控件解除对 Tcl 图片的引用，再释放 Python PhotoImage。
        self.video.itemconfigure(
            self._image_item, image="", state=tk.HIDDEN
        )
        self.video.itemconfigure(
            self._message_item, text=text, state=tk.NORMAL
        )
        self._photo = None

    def destroy(self) -> None:
        self.video.itemconfigure(self._image_item, image="")
        self.frame.destroy()
        self._photo = None


class CameraToolWindow:
    FRAME_INTERVAL_MS = 30
    MAX_READ_FAILURES = 10

    def __init__(self, root: tk.Tk, camera_service: CameraService) -> None:
        self.root = root
        self.camera_service = camera_service
        self.devices: list[CameraDevice] = []
        self.tiles: dict[int, VideoTile] = {}
        self._frame_job: str | None = None
        self._read_failures: dict[int, int] = {}
        self._multi_vars: dict[int, tk.BooleanVar] = {}
        self._drawer_visible = False

        self.mode_var = tk.StringVar(value="single")
        self.camera_var = tk.StringVar()
        self.status_var = tk.StringVar(value="正在初始化…")

        self._configure_window()
        self._build_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(100, self.refresh_devices)

    def _configure_window(self) -> None:
        self.root.title("PC 摄像头工具")
        self.root.geometry("1100x760")
        self.root.minsize(760, 540)
        self.root.configure(background="#111827")

        style = ttk.Style(self.root)
        style.configure("Toolbar.TFrame", background="#1f2937")
        style.configure(
            "Title.TLabel",
            background="#1f2937",
            foreground="#f9fafb",
            font=("Microsoft YaHei UI", 14, "bold"),
        )
        style.configure(
            "Status.TLabel",
            background="#111827",
            foreground="#d1d5db",
            font=("Microsoft YaHei UI", 9),
        )

    def _build_widgets(self) -> None:
        toolbar = ttk.Frame(self.root, style="Toolbar.TFrame", padding=(18, 12))
        toolbar.pack(fill=tk.X)

        ttk.Label(toolbar, text="摄像头预览", style="Title.TLabel").pack(side=tk.LEFT)

        self.mode_group = tk.Frame(toolbar, bg="#374151")
        self.mode_group.pack(side=tk.LEFT, padx=(16, 0))
        for value, text in (("single", "单路显示"), ("multi", "多路显示")):
            tk.Radiobutton(
                self.mode_group,
                text=text,
                value=value,
                variable=self.mode_var,
                command=self._on_mode_changed,
                indicatoron=False,
                selectcolor="#2563eb",
                bg="#374151",
                fg="white",
                activebackground="#4b5563",
                activeforeground="white",
                padx=12,
                pady=5,
                borderwidth=0,
                font=("Microsoft YaHei UI", 9),
            ).pack(side=tk.LEFT, padx=1, pady=1)

        self.drawer_button = ttk.Button(
            toolbar,
            text="多路设置",
            command=self._toggle_multi_drawer,
        )

        self.refresh_button = ttk.Button(
            toolbar, text="重新扫描", command=self.refresh_devices
        )
        self.refresh_button.pack(side=tk.RIGHT)

        self.single_controls = tk.Frame(toolbar, bg="#1f2937")
        self.single_controls.pack(side=tk.RIGHT, padx=(0, 12))
        tk.Label(
            self.single_controls,
            text="选择设备",
            bg="#1f2937",
            fg="#d1d5db",
            font=("Microsoft YaHei UI", 9),
        ).pack(side=tk.LEFT, padx=(0, 8))

        self.camera_combo = ttk.Combobox(
            self.single_controls,
            textvariable=self.camera_var,
            state="readonly",
            width=18,
            font=("Microsoft YaHei UI", 10),
        )
        self.camera_combo.pack(side=tk.LEFT)
        self.camera_combo.bind("<<ComboboxSelected>>", self._on_camera_selected)

        self.multi_controls = tk.Frame(self.root, bg="#1f2937", padx=18, pady=8)

        self.video_container = tk.Frame(self.root, bg="#111827", padx=18, pady=18)
        self.video_container.pack(fill=tk.BOTH, expand=True)
        self.video_grid = self._new_video_grid()

        status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            style="Status.TLabel",
            padding=(18, 0, 18, 12),
        )
        status_bar.pack(fill=tk.X)

    def refresh_devices(self) -> None:
        self._stop_preview()
        self.refresh_button.configure(state=tk.DISABLED)
        self.camera_combo.configure(state=tk.DISABLED)
        self.camera_var.set("")
        self.status_var.set("正在扫描已接入的摄像头…")
        self.root.update_idletasks()

        try:
            self.devices = self.camera_service.discover()
        except Exception as exc:
            self.devices = []
            messagebox.showerror("扫描失败", f"扫描摄像头时发生错误：\n{exc}")
        finally:
            self.refresh_button.configure(state=tk.NORMAL)

        self.camera_combo["values"] = [
            device.display_name for device in self.devices
        ]
        self._rebuild_multi_controls()
        if not self.devices:
            self.status_var.set("未检测到可用摄像头")
            self._show_empty_message("未检测到可用摄像头")
            messagebox.showwarning(
                "未检测到摄像头",
                "没有找到可打开的摄像头。\n请检查连接或关闭其他占用摄像头的程序后重试。",
            )
            return

        self.camera_combo.configure(state="readonly")
        self.camera_combo.current(0)
        if self.mode_var.get() == "multi":
            self._show_drawer_button()
            self._show_multi_drawer()
            self.status_var.set("多路显示：请选择摄像头并确认")
            self._show_empty_message("请选择需要同时显示的摄像头")
        else:
            self.open_selected_camera()

    def _rebuild_multi_controls(self) -> None:
        for child in self.multi_controls.winfo_children():
            child.destroy()
        self._multi_vars.clear()

        tk.Label(
            self.multi_controls,
            text="选择同时显示的摄像头：",
            bg="#1f2937",
            fg="#d1d5db",
            font=("Microsoft YaHei UI", 9),
        ).pack(side=tk.LEFT, padx=(0, 8))

        for device in self.devices:
            variable = tk.BooleanVar(value=True)
            self._multi_vars[device.index] = variable
            tk.Checkbutton(
                self.multi_controls,
                text=device.display_name,
                variable=variable,
                bg="#1f2937",
                fg="#f3f4f6",
                selectcolor="#374151",
                activebackground="#1f2937",
                activeforeground="white",
                font=("Microsoft YaHei UI", 9),
            ).pack(side=tk.LEFT, padx=4)

        ttk.Button(
            self.multi_controls,
            text="应用选择",
            command=self.apply_multi_selection,
        ).pack(side=tk.RIGHT)

    def _on_mode_changed(self) -> None:
        if self.mode_var.get() == "multi":
            self.single_controls.pack_forget()
            self._show_drawer_button()
            self._stop_preview()
            self._show_multi_drawer()
            self.status_var.set("多路显示：请选择摄像头并确认")
            self._show_empty_message("请选择需要同时显示的摄像头")
        else:
            self._hide_multi_drawer()
            self._hide_drawer_button()
            self.single_controls.pack(side=tk.RIGHT, padx=(0, 12))
            self.open_selected_camera()

    def _show_drawer_button(self) -> None:
        if self.drawer_button.winfo_manager():
            return
        self.drawer_button.pack(
            side=tk.LEFT,
            padx=(8, 0),
            after=self.mode_group,
        )

    def _hide_drawer_button(self) -> None:
        self.drawer_button.pack_forget()

    def _toggle_multi_drawer(self) -> None:
        if self.mode_var.get() != "multi":
            return
        if self._drawer_visible:
            self._hide_multi_drawer()
        else:
            self._show_multi_drawer()

    def _show_multi_drawer(self) -> None:
        if self._drawer_visible:
            return
        self.multi_controls.pack(fill=tk.X, before=self.video_container)
        self._drawer_visible = True

    def _hide_multi_drawer(self) -> None:
        self.multi_controls.pack_forget()
        self._drawer_visible = False

    def _on_camera_selected(self, _event: tk.Event) -> None:
        self.open_selected_camera()

    def open_selected_camera(self) -> None:
        selection = self.camera_combo.current()
        if selection < 0 or selection >= len(self.devices):
            self._show_empty_message("请选择摄像头")
            return

        device = self.devices[selection]
        self._stop_preview()
        if not self.camera_service.open(device):
            self.status_var.set(f"{device.display_name} 打开失败")
            self._show_empty_message("摄像头打开失败")
            messagebox.showerror(
                "无法打开摄像头",
                f"无法打开{device.display_name}。\n"
                "请检查设备连接，或关闭其他占用摄像头的程序。",
            )
            return

        self._create_tiles([device])
        self.status_var.set(f"单路显示：{device.display_name}")
        self._schedule_next_frame()

    def apply_multi_selection(self) -> None:
        selected = [
            device
            for device in self.devices
            if self._multi_vars.get(device.index) is not None
            and self._multi_vars[device.index].get()
        ]
        self._stop_preview()
        if not selected:
            self.status_var.set("多路显示：尚未选择摄像头")
            self._show_empty_message("请至少选择一路摄像头")
            return

        self._hide_multi_drawer()
        opened: list[CameraDevice] = []
        failed: list[CameraDevice] = []
        for device in selected:
            if self.camera_service.open(device):
                opened.append(device)
            else:
                failed.append(device)

        if opened:
            self._create_tiles(opened)
            self.status_var.set(f"多路显示：正在显示 {len(opened)} 路摄像头")
            self._schedule_next_frame()
        else:
            self._show_empty_message("所选摄像头均无法打开")
            self.status_var.set("多路显示：摄像头打开失败")

        if failed:
            names = "、".join(device.display_name for device in failed)
            messagebox.showerror(
                "部分摄像头无法打开",
                f"以下设备无法打开：{names}\n"
                "其他可用摄像头将继续显示，请检查连接或设备占用情况。",
            )

    def _create_tiles(self, devices: list[CameraDevice]) -> None:
        rows, columns = grid_shape(len(devices))
        for row in range(rows):
            self.video_grid.rowconfigure(row, weight=1, uniform="video-row")
        for column in range(columns):
            self.video_grid.columnconfigure(
                column, weight=1, uniform="video-column"
            )

        for device, (row, column) in zip(devices, grid_positions(len(devices))):
            tile = VideoTile(self.video_grid, device)
            tile.frame.grid(
                row=row, column=column, sticky="nsew", padx=5, pady=5
            )
            self.tiles[device.index] = tile
            self._read_failures[device.index] = 0

    def _show_empty_message(self, text: str) -> None:
        self._clear_video_area()
        placeholder = tk.Label(
            self.video_grid,
            text=text,
            bg="#030712",
            fg="#9ca3af",
            font=("Microsoft YaHei UI", 14),
        )
        placeholder.grid(row=0, column=0, sticky="nsew")
        self.video_grid.rowconfigure(0, weight=1)
        self.video_grid.columnconfigure(0, weight=1)

    def _new_video_grid(self) -> tk.Frame:
        grid = tk.Frame(self.video_container, bg="#111827")
        grid.pack(fill=tk.BOTH, expand=True)
        return grid

    def _clear_video_area(self) -> None:
        for tile in self.tiles.values():
            tile.destroy()
        self.tiles.clear()
        self.video_grid.destroy()
        self.video_grid = self._new_video_grid()
        self._read_failures.clear()

    def _schedule_next_frame(self) -> None:
        self._frame_job = self.root.after(
            self.FRAME_INTERVAL_MS, self._update_frames
        )

    def _update_frames(self) -> None:
        self._frame_job = None
        interrupted: list[int] = []
        for index, tile in list(self.tiles.items()):
            frame = self.camera_service.read(index)
            if frame is None:
                self._read_failures[index] += 1
                if self._read_failures[index] >= self.MAX_READ_FAILURES:
                    self.camera_service.close(index)
                    tile.show_message("视频画面读取失败")
                    interrupted.append(index)
                continue

            self._read_failures[index] = 0
            tile.show_frame(frame)

        if interrupted:
            names = "、".join(f"摄像头 {index}" for index in interrupted)
            messagebox.showerror(
                "视频流中断",
                f"{names} 的画面读取失败。\n其他可用摄像头将继续显示。",
            )

        if self.camera_service.active_indexes:
            self._schedule_next_frame()
        elif self.tiles:
            self.status_var.set("视频流已中断")

    def _stop_preview(self) -> None:
        if self._frame_job is not None:
            self.root.after_cancel(self._frame_job)
            self._frame_job = None
        self.camera_service.close()
        self._clear_video_area()

    def close(self) -> None:
        self._stop_preview()
        self.root.destroy()
