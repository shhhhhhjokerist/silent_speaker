#!/usr/bin/env python3
"""
TTS 虚拟麦克风 — GUI 版
========================
轻量级 tkinter 界面，适合全屏游戏时 Alt+Tab 切出来快速打字。

用法:
    python tts_mic_gui.py
"""

import asyncio
import json
import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk

# ---- Windows 终端 UTF-8 修复 ----
if sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

# 导入核心功能
from tts_mic import (
    DEFAULT_CONFIG,
    find_virtual_audio_device,
    get_config,
    get_virtual_audio_help,
    list_output_devices,
    play_audio,
    resolve_output_device,
    save_config,
    speak,
    tts_edge,
    tts_google,
    tts_offline,
)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent

# Edge TTS 可用语音列表（中文 — 实测验证）
EDGE_VOICES = [
    ("zh-CN-XiaoxiaoNeural", "晓晓 (活泼女声)"),
    ("zh-CN-XiaoyiNeural", "晓伊 (温柔女声)"),
    ("zh-CN-YunxiNeural", "云希 (男声)"),
    ("zh-CN-YunyangNeural", "云扬 (新闻男声)"),
    ("zh-CN-XiaoxuanNeural", "晓萱 (女声)"),
    ("zh-CN-liaoning-XiaobeiNeural", "晓蓓 (东北话)"),
    ("zh-CN-shaanxi-XiaoniNeural", "晓妮 (陕西话)"),
    ("zh-TW-HsiaoChenNeural", "曉臻 (台湾女声)"),
    ("zh-TW-YunJheNeural", "雲哲 (台湾男声)"),
    ("zh-HK-HiuMaanNeural", "曉曼 (粤语女声)"),
    ("zh-HK-WanLungNeural", "雲龍 (粤语男声)"),
]

GOOGLE_LANGS = [
    ("zh-CN", "中文(简体)"),
    ("zh-TW", "中文(繁体)"),
    ("en", "English"),
    ("ja", "日本語"),
    ("ko", "한국어"),
]


# ---------------------------------------------------------------------------
# GUI Application
# ---------------------------------------------------------------------------
class TTSMicApp:
    def __init__(self, root):
        self.root = root
        self.config = get_config()
        self._speaking = False
        self._setup_ui()
        self._load_config_to_ui()

        # 窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------
    def _setup_ui(self):
        root = self.root
        root.title("TTS 虚拟麦克风")
        root.resizable(True, True)
        root.minsize(420, 280)

        # 尝试设置窗口图标（静默失败）
        try:
            root.iconbitmap(default="")
        except Exception:
            pass

        # 样式
        style = ttk.Style()
        style.theme_use("clam")

        # ---- 主容器 ----
        main_frame = ttk.Frame(root, padding=8)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ---- Row 0: 引擎 + 语音 ----
        row0 = ttk.Frame(main_frame)
        row0.pack(fill=tk.X, pady=(0, 4))

        ttk.Label(row0, text="引擎:").pack(side=tk.LEFT)
        self.engine_var = tk.StringVar(value="edge")
        self.engine_cb = ttk.Combobox(
            row0, textvariable=self.engine_var,
            values=["edge", "google", "offline"],
            state="readonly", width=8,
        )
        self.engine_cb.pack(side=tk.LEFT, padx=(2, 12))
        self.engine_cb.bind("<<ComboboxSelected>>", self._on_engine_changed)

        ttk.Label(row0, text="语音:").pack(side=tk.LEFT)
        self.voice_var = tk.StringVar(value="zh-CN-XiaoxiaoNeural")
        self.voice_cb = ttk.Combobox(
            row0, textvariable=self.voice_var,
            values=[v[0] for v in EDGE_VOICES],
            state="readonly", width=22,
        )
        self.voice_cb.pack(side=tk.LEFT, padx=(2, 0))

        # 语音名称提示
        self.voice_hint = ttk.Label(row0, text="", foreground="gray")
        self.voice_hint.pack(side=tk.LEFT, padx=4)
        self._update_voice_hint()

        # ---- Row 1: 设备 + 音量 ----
        row1 = ttk.Frame(main_frame)
        row1.pack(fill=tk.X, pady=(0, 4))

        ttk.Label(row1, text="设备:").pack(side=tk.LEFT)
        self.device_var = tk.StringVar()
        self.device_cb = ttk.Combobox(
            row1, textvariable=self.device_var,
            state="readonly", width=28,
        )
        self.device_cb.pack(side=tk.LEFT, padx=(2, 12))
        self._refresh_devices()

        ttk.Label(row1, text="音量:").pack(side=tk.LEFT)
        self.volume_var = tk.IntVar(value=100)
        self.volume_scale = ttk.Scale(
            row1, from_=0, to=200, variable=self.volume_var,
            orient=tk.HORIZONTAL, length=120,
            command=self._on_volume_changed,
        )
        self.volume_scale.pack(side=tk.LEFT, padx=2)
        self.volume_label = ttk.Label(row1, text="100%", width=5)
        self.volume_label.pack(side=tk.LEFT)

        # ---- Row 2: 快捷短语 ----
        hot_frame = ttk.LabelFrame(main_frame, text="快捷短语", padding=4)
        hot_frame.pack(fill=tk.X, pady=(2, 6))

        self.hot_buttons_frame = ttk.Frame(hot_frame)
        self.hot_buttons_frame.pack(fill=tk.X)
        self._build_hot_buttons()

        # ---- Row 3: 输入区 ----
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=(0, 4))

        self.text_input = ttk.Entry(input_frame, font=("Microsoft YaHei", 11))
        self.text_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.text_input.bind("<Return>", self._on_send)
        self.text_input.focus_set()

        self.send_btn = ttk.Button(
            input_frame, text="发送 ▶", command=self._on_send, width=9,
        )
        self.send_btn.pack(side=tk.RIGHT)

        # ---- Row 4: 状态栏 ----
        self.status_var = tk.StringVar(value="就绪 — 输入文字后按回车发送")
        status_bar = ttk.Label(
            main_frame, textvariable=self.status_var,
            relief=tk.SUNKEN, anchor=tk.W, padding=(4, 2),
            foreground="#555",
        )
        status_bar.pack(fill=tk.X, pady=(2, 0))

        # ---- 快捷键绑定 ----
        root.bind("<Control-l>", lambda e: self.text_input.focus_set())
        root.bind("<Escape>", lambda e: self._clear_input())

    # ------------------------------------------------------------------
    # 设备列表
    # ------------------------------------------------------------------
    def _refresh_devices(self):
        """重建设备下拉列表。"""
        import sys as _sys

        devices = list_output_devices()
        device_names = []
        self._device_map = {}  # name -> id

        # 平台适配的虚拟设备关键词
        if _sys.platform == "darwin":
            virt_kw = ["BLACKHOLE", "SOUNDFLOWER", "LOOPBACK"]
        else:
            virt_kw = ["CABLE", "VB-AUDIO", "VOICEMEETER"]

        for idx, dev in devices:
            name = dev["name"]
            short_name = name[:50] + ("..." if len(name) > 50 else "")
            tag = ""
            for kw in virt_kw:
                if kw in name.upper():
                    tag = " [虚拟音频]"
                    break
            display = f"[{idx}] {short_name}{tag}"
            device_names.append(display)
            self._device_map[display] = idx

        self.device_cb["values"] = device_names

        # 自动选虚拟设备或默认
        virt = find_virtual_audio_device()
        if virt is not None:
            for display, did in self._device_map.items():
                if did == virt:
                    self.device_var.set(display)
                    return
        # 选系统默认设备
        import sounddevice as sd
        default_id = sd.default.device[1]
        for display, did in self._device_map.items():
            if did == default_id:
                self.device_var.set(display)
                return
        if device_names:
            self.device_var.set(device_names[0])

    def _get_selected_device(self):
        """获取当前选中的设备 ID。"""
        sel = self.device_var.get()
        return self._device_map.get(sel)

    # ------------------------------------------------------------------
    # 快捷短语按钮
    # ------------------------------------------------------------------
    def _build_hot_buttons(self):
        """根据配置生成快捷短语按钮。"""
        for w in self.hot_buttons_frame.winfo_children():
            w.destroy()

        hot = self.config.get("hot_phrases", {})
        if not hot:
            ttk.Label(self.hot_buttons_frame, text="(无)").pack(side=tk.LEFT)
            return

        for key, phrase in hot.items():
            label = key if len(key) <= 6 else key[:5] + ".."
            btn = ttk.Button(
                self.hot_buttons_frame, text=label,
                command=lambda p=phrase: self._send_phrase(p),
                width=6,
            )
            btn.pack(side=tk.LEFT, padx=1, pady=1)
            # 鼠标悬停提示完整短语
            self._set_tooltip(btn, f"{key} -> {phrase}")

    def _set_tooltip(self, widget, text):
        """简单 tooltip 实现。"""
        try:
            widget.bind("<Enter>", lambda e: self.status_var.set(text))
            widget.bind("<Leave>", lambda e: self.status_var.set("就绪"))
        except Exception:
            pass

    def _send_phrase(self, phrase):
        """发送快捷短语。"""
        self.text_input.delete(0, tk.END)
        self.text_input.insert(0, phrase)
        self._do_speak(phrase)

    # ------------------------------------------------------------------
    # 语音合成线程
    # ------------------------------------------------------------------
    def _on_send(self, event=None):
        """发送按钮 / 回车键。"""
        text = self.text_input.get().strip()
        if not text:
            return
        # 检查快捷短语
        hot = self.config.get("hot_phrases", {})
        if text in hot:
            text = hot[text]
        self._do_speak(text)
        self.text_input.delete(0, tk.END)

    def _do_speak(self, text):
        """在后台线程中运行语音合成+播放。"""
        if self._speaking:
            self.status_var.set("请等待上一条播放完毕...")
            return

        self._speaking = True
        self.send_btn.configure(state="disabled")
        self.status_var.set(f"正在合成: {text[:30]}...")

        # 同步 UI config
        self._sync_ui_to_config()

        device_id = self._get_selected_device()
        cfg = dict(self.config)  # 拷贝一份避免并发问题

        def run():
            try:
                asyncio.run(speak(text, cfg, device_id, on_status=self._update_status))
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"错误: {e}"))
            finally:
                self.root.after(0, self._on_speak_done)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def _update_status(self, msg):
        """从后台线程安全更新状态文字。"""
        self.root.after(0, lambda m=msg: self.status_var.set(m.strip()))

    def _on_speak_done(self):
        """播放完成后恢复 UI。"""
        self._speaking = False
        self.send_btn.configure(state="normal")
        self.text_input.focus_set()

    # ------------------------------------------------------------------
    # UI 事件处理
    # ------------------------------------------------------------------
    def _on_engine_changed(self, event=None):
        """引擎切换时同步恢复对应的语音列表和选中项。"""
        engine = self.engine_var.get()
        if engine == "edge":
            # 恢复 Edge 语音列表
            self.voice_cb["values"] = [v[0] for v in EDGE_VOICES]
            edge_voice = self.config.get("voice", "zh-CN-XiaoxiaoNeural")
            edge_ids = [v[0] for v in EDGE_VOICES]
            if edge_voice in edge_ids:
                self.voice_var.set(edge_voice)
            else:
                self.voice_var.set("zh-CN-XiaoxiaoNeural")
            self.voice_cb.configure(state="readonly")
            self._update_voice_hint()
        elif engine == "google":
            # 恢复 Google 语言列表
            self.voice_cb["values"] = [v[0] for v in GOOGLE_LANGS]
            google_lang = self.config.get("google_lang", "zh-CN")
            lang_ids = [v[0] for v in GOOGLE_LANGS]
            if google_lang in lang_ids:
                self.voice_var.set(google_lang)
            else:
                self.voice_var.set("zh-CN")
            self.voice_cb.configure(state="readonly")
            self.voice_hint.configure(text="")
        else:
            self.voice_cb.configure(state="disabled")
            self.voice_hint.configure(text="")

    def _on_volume_changed(self, value):
        """音量滑块变化。"""
        pct = int(float(value))
        self.volume_label.configure(text=f"{pct}%")

    def _update_voice_hint(self):
        """显示当前语音的描述。"""
        voice_id = self.voice_var.get()
        for vid, vname in EDGE_VOICES:
            if vid == voice_id:
                self.voice_hint.configure(text=f"({vname})")
                return
        self.voice_hint.configure(text="")

    def _clear_input(self):
        self.text_input.delete(0, tk.END)
        self.text_input.focus_set()

    # ------------------------------------------------------------------
    # 配置同步
    # ------------------------------------------------------------------
    def _sync_ui_to_config(self):
        """把 UI 状态写入 config —— 按引擎分别保存语音/语言。"""
        engine = self.engine_var.get()
        self.config["tts_engine"] = engine
        self.config["volume"] = self.volume_var.get() / 100.0
        self.config["output_device"] = self._get_selected_device()
        # Edge 语音 vs Google 语言分开保存，避免互相覆盖
        voice_val = self.voice_var.get()
        if engine == "edge":
            self.config["voice"] = voice_val
        elif engine == "google":
            self.config["google_lang"] = voice_val

    def _load_config_to_ui(self):
        """把 config 恢复到 UI —— 按引擎恢复对应的语音/语言选择。"""
        cfg = self.config
        engine = cfg.get("tts_engine", "edge")
        self.engine_var.set(engine)

        if engine == "edge":
            self.voice_cb["values"] = [v[0] for v in EDGE_VOICES]
            voice = cfg.get("voice", "zh-CN-XiaoxiaoNeural")
            edge_ids = [v[0] for v in EDGE_VOICES]
            if voice not in edge_ids:
                voice = "zh-CN-XiaoxiaoNeural"
            self.voice_var.set(voice)
            self.voice_cb.configure(state="readonly")
            self._update_voice_hint()
        elif engine == "google":
            self.voice_cb["values"] = [v[0] for v in GOOGLE_LANGS]
            lang = cfg.get("google_lang", "zh-CN")
            lang_ids = [v[0] for v in GOOGLE_LANGS]
            if lang not in lang_ids:
                lang = "zh-CN"
            self.voice_var.set(lang)
            self.voice_cb.configure(state="readonly")
            self.voice_hint.configure(text="")
        else:
            self.voice_cb.configure(state="disabled")
            self.voice_hint.configure(text="")

        vol = cfg.get("volume", 1.0)
        self.volume_var.set(int(vol * 100))
        self.volume_label.configure(text=f"{int(vol * 100)}%")

    def _on_close(self):
        """窗口关闭时保存配置。"""
        self._sync_ui_to_config()
        save_config(self.config)
        self.root.destroy()


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
def main():
    root = tk.Tk()

    # 窗口大小和位置
    root.geometry("480x280")

    # 可选：窗口置顶（可在设置中开启）
    # root.attributes("-topmost", True)

    # 深色主题配色（可选）
    try:
        root.tk_setPalette(
            background="#f0f0f0",
            foreground="#333333",
            activeBackground="#e0e0e0",
            activeForeground="#000000",
        )
    except Exception:
        pass

    app = TTSMicApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
