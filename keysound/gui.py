from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

from .config import KeysoundConfig, Mode
from .runner import KeysoundRunner


class KeysoundApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Keysound")
        self.root.resizable(False, False)

        self.mode_var = tk.StringVar(value=Mode.SINGLE_FILE.value)
        self.path_var = tk.StringVar(value="")
        self.block_var = tk.IntVar(value=1024)
        self.volume_var = tk.DoubleVar(value=1.0)
        self.status_var = tk.StringVar(value="Idle")

        self.runner: KeysoundRunner | None = None

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        padding = {"padx": 8, "pady": 4}

        mode_frame = tk.LabelFrame(self.root, text="Mode")
        mode_frame.grid(row=0, column=0, columnspan=3, sticky="ew", **padding)
        tk.Radiobutton(mode_frame, text="Single WAV", variable=self.mode_var,
                       value=Mode.SINGLE_FILE.value, command=self._update_placeholder).grid(row=0, column=0, sticky="w", padx=6, pady=4)
        tk.Radiobutton(mode_frame, text="Directory", variable=self.mode_var,
                       value=Mode.DIRECTORY.value, command=self._update_placeholder).grid(row=0, column=1, sticky="w", padx=6, pady=4)
        tk.Radiobutton(mode_frame, text="JSON Config", variable=self.mode_var,
                       value=Mode.JSON.value, command=self._update_placeholder).grid(row=0, column=2, sticky="w", padx=6, pady=4)

        tk.Label(self.root, text="Path").grid(row=1, column=0, sticky="w", **padding)
        entry = tk.Entry(self.root, textvariable=self.path_var, width=48)
        entry.grid(row=1, column=1, sticky="ew", **padding)
        tk.Button(self.root, text="Browse", command=self._browse).grid(row=1, column=2, sticky="ew", **padding)

        tk.Label(self.root, text="Block size").grid(row=2, column=0, sticky="w", **padding)
        tk.Spinbox(self.root, from_=256, to=8192, increment=128, textvariable=self.block_var, width=10).grid(row=2, column=1, sticky="w", **padding)

        tk.Label(self.root, text="Volume").grid(row=3, column=0, sticky="w", **padding)
        tk.Scale(self.root, from_=0.1, to=2.0, resolution=0.1, orient=tk.HORIZONTAL,
                 variable=self.volume_var, length=240).grid(row=3, column=1, columnspan=2, sticky="ew", **padding)

        tk.Button(self.root, text="Start", command=self._toggle).grid(row=4, column=0, sticky="ew", **padding)
        tk.Button(self.root, text="Stop", command=self.stop).grid(row=4, column=1, sticky="ew", **padding)

        status_frame = tk.Frame(self.root)
        status_frame.grid(row=5, column=0, columnspan=3, sticky="ew", padx=8, pady=(4, 12))
        tk.Label(status_frame, text="Status:").grid(row=0, column=0, sticky="w")
        tk.Label(status_frame, textvariable=self.status_var).grid(row=0, column=1, sticky="w")

        self.root.grid_columnconfigure(1, weight=1)

    def _browse(self) -> None:
        mode = Mode(self.mode_var.get())
        if mode is Mode.SINGLE_FILE or mode is Mode.JSON:
            initial = Path(self.path_var.get()) if self.path_var.get() else Path.cwd()
            if mode is Mode.JSON:
                selection = filedialog.askopenfilename(title="Select configuration",
                                                       filetypes=[("JSON", "*.json"), ("All files", "*")],
                                                       initialdir=initial.parent if initial.exists() else Path.cwd())
            else:
                selection = filedialog.askopenfilename(title="Select WAV file",
                                                       filetypes=[("WAV", "*.wav"), ("All files", "*")],
                                                       initialdir=initial.parent if initial.exists() else Path.cwd())
        else:
            selection = filedialog.askdirectory(title="Select audio directory",
                                                initialdir=self.path_var.get() or str(Path.cwd()))
        if selection:
            self.path_var.set(selection)

    def _toggle(self) -> None:
        if self.runner and self.runner.is_running():
            self.stop()
        else:
            self.start()

    def start(self) -> None:
        try:
            mode = Mode(self.mode_var.get())
            source = Path(self.path_var.get()).expanduser()
            config = KeysoundConfig(mode=mode, source=source,
                                    block_size=int(self.block_var.get()),
                                    volume=float(self.volume_var.get()))
            if self.runner:
                self.runner.stop()
            self.runner = KeysoundRunner(config)
            self.runner.start()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Keysound", f"Failed to start: {exc}")
            self.status_var.set("Error")
            return
        self.status_var.set("Running")

    def stop(self) -> None:
        if not self.runner:
            self.status_var.set("Idle")
            return
        self.runner.stop()
        self.runner = None
        self.status_var.set("Idle")

    def _update_placeholder(self) -> None:
        mode = Mode(self.mode_var.get())
        if mode is Mode.SINGLE_FILE:
            self.status_var.set("Select a WAV file for all keys")
        elif mode is Mode.DIRECTORY:
            self.status_var.set("Select a directory of per-key WAV files")
        else:
            self.status_var.set("Select a JSON mapping file")

    def _on_close(self) -> None:
        self.stop()
        self.root.destroy()

    def run(self) -> None:
        self._update_placeholder()
        self.root.mainloop()


def run() -> None:
    KeysoundApp().run()


__all__ = ["KeysoundApp", "run"]
