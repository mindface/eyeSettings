import threading
import time
import cv2
import numpy as np
import mediapipe as mp
import tkinter as tk
from tkinter import ttk
import Quartz
import pyautogui

from Quartz.CoreGraphics import (
    CGEventCreateMouseEvent,
    CGEventPost,
    kCGHIDEventTap,
    kCGEventMouseMoved,
)

# ----------------------------
# Tkinter 用設定クラス
# ----------------------------
class Settings:
    def __init__(self):
        self.sensitivity = tk.DoubleVar(value=600.0)  # 画面移動倍率
        self.dead_zone = tk.DoubleVar(value=0.1)     # 中心停止範囲
        self.fps = tk.IntVar(value=30)                # 処理FPS

# ----------------------------
# カーソル移動関数
# ----------------------------
def move_cursor_from_gaze(eyes_center, frame, landmarks, settings):
    """
    eyes_center: (x, y) カメラ座標
    frame: カメラフレーム
    landmarks: 顔ランドマーク
    settings: Settings クラス（sensitivity, dead_zone）
    """
    h, w = frame.shape[:2]

    # 正規化座標 0~1
    x_norm = eyes_center[0] / w
    y_norm = eyes_center[1] / h

    # 画面サイズ
    screen = Quartz.CGDisplayBounds(Quartz.CGMainDisplayID())
    screen_width = int(screen.size.width)
    screen_height = int(screen.size.height)

    # 正規化 → 画面座標
    x_screen = int(x_norm * screen_width)
    y_screen = int(y_norm * screen_height)

    # dead_zone 設定（画面中央で止める範囲）
    dead_zone_px_x = int(settings.dead_zone.get() * screen_width)
    dead_zone_px_y = int(settings.dead_zone.get() * screen_height)

    center_x = screen_width // 2
    center_y = screen_height // 2

    dx = x_screen - center_x
    dy = y_screen - center_y

    gaze_x = x_norm - 0.5
    gaze_y = y_norm - 0.5

    dead_zone = float(settings.dead_zone.get())  # 例: 0.1
    sensitivity = float(settings.sensitivity.get())  # 例: 700
    
    # Dead zone（無視する範囲）
    if abs(gaze_x) < dead_zone and abs(gaze_y) < dead_zone:
        return
    # if abs(dx) < dead_zone_px_x and abs(dy) < dead_zone_px_y:
    #     return  # dead_zone内は移動しない
    print("¥¥¥¥¥¥¥2")

    # sensitivity に応じて倍率をかける
    dx = int(dx * settings.sensitivity.get() / 600.0)
    dy = int(dy * settings.sensitivity.get() / 600.0)

    final_x = center_x + dx
    final_y = center_y + dy

    # 画面端制限
    final_x = max(0, min(screen_width, final_x))
    final_y = max(0, min(screen_height, final_y))
    print(final_x)

    # カーソル移動
    event = CGEventCreateMouseEvent(
        None,
        kCGEventMouseMoved,
        (final_x, final_y),
        0
    )
    CGEventPost(kCGHIDEventTap, event)


def convert_eye_to_screen(eye_x, eye_y):
    screen = Quartz.CGDisplayBounds(Quartz.CGMainDisplayID())
    screen_width = int(screen.size.width)
    screen_height = int(screen.size.height)
    eye_min_x = 180
    eye_max_x = 430
    eye_min_y = 130
    eye_max_y = 300

    # カメラ空間 → スクリーン空間
    screen_x = map_value(eye_x, eye_min_x, eye_max_x, 0, screen_width)
    screen_y = map_value(eye_y, eye_min_y, eye_max_y, 0, screen_height)

    # 画面外に出さない
    screen_x = max(0, min(screen_width, screen_x))
    screen_y = max(0, min(screen_height, screen_y))

    return int(screen_x), int(screen_y)


# ----------------------------
# OpenCV 目線処理ループ
# ----------------------------
def gaze_loop(settings, stop_event):
    cap = cv2.VideoCapture(0)
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    LEFT_IRIS = [474, 475, 476, 477]
    RIGHT_IRIS = [469, 470, 471, 472]

    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            continue

        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)

        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark

            # 左右虹彩中心
            left_iris = np.mean([[landmarks[i].x * w, landmarks[i].y * h] for i in LEFT_IRIS], axis=0)
            right_iris = np.mean([[landmarks[i].x * w, landmarks[i].y * h] for i in RIGHT_IRIS], axis=0)

            eyes_center = ((left_iris + right_iris) / 2).astype(int)

            # move_cursor に渡す
            move_cursor_from_gaze(eyes_center, frame, landmarks, settings)

        time.sleep(1.0 / settings.fps.get())

    cap.release()


def center_window(win, width, height):
    win.update_idletasks()  # サイズ更新

    screen_w = win.winfo_screenwidth()
    screen_h = win.winfo_screenheight()

    x = int((screen_w - width) / 2)
    y = int((screen_h - height) / 2)

    win.geometry(f"{width}x{height}+{x}+{y}")

# ----------------------------
# 設定ウィンドウ
# ----------------------------
def open_settings_window(settings, root):
    win = tk.Toplevel(root)
    win.title("Settings")
    win.geometry("300x200")

    ttk.Label(win, text="Sensitivity").pack(pady=5)
    ttk.Scale(win, from_=200, to=8000, variable=settings.sensitivity,
              orient="horizontal").pack(fill="x", padx=20)

    ttk.Label(win, text="Dead Zone").pack(pady=5)
    ttk.Scale(win, from_=0.0, to=0.2, variable=settings.dead_zone, orient="horizontal").pack(fill="x", padx=20)

    ttk.Label(win, text="FPS").pack(pady=5)
    ttk.Scale(win, from_=15, to=60, variable=settings.fps,
              orient="horizontal").pack(fill="x", padx=20)

    ttk.Button(win, text="Close", command=win.destroy).pack(pady=10)

# ----------------------------
# メイン
# ----------------------------
def main():
    root = tk.Tk()
    root.title("Gaze Control GUI")
    root.geometry("300x200")

    settings = Settings()
    center_window(root, 300, 200)

    ttk.Button(
        root,
        text="Open Settings",
        command=lambda: open_settings_window(settings, root)
    ).pack(pady=40)

    # OpenCV カメラループを別スレッドで実行
    stop_event = threading.Event()
    threading.Thread(target=gaze_loop, args=(settings, stop_event), daemon=True).start()

    root.mainloop()
    stop_event.set()  # Tkinter終了時にカメラ停止

if __name__ == "__main__":
    main()
