import cv2, time
import mediapipe as mp
import numpy as np
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import subprocess

root = tk.Tk()
root.withdraw()

LEFT_EYE_INNER = 133
LEFT_EYE_OUTER = 33
LEFT_EYE_UPPER = 159
LEFT_EYE_LOWER = 145
LEFT_IRIS = [474, 475, 476, 477]

def on_scale_change(v):
    value = round(float(v), 2)  # 0.01刻み
    gaze_settings.threshold.set(value)
    lbl1.config(text=f"{value:.2f}")

# ===== 新規追加: グローバル設定クラス =====
class GazeSettings:
    """目線判定の設定を管理"""
    def __init__(self):
        self.threshold = tk.DoubleVar(value=0.35)  # 目線ズレ判定の閾値
        self.distraction_time = tk.DoubleVar(value=5.0)  # 通知までの秒数
        self.notification_cooldown = tk.IntVar(value=10)  # 通知間隔（秒）

gaze_settings = GazeSettings()

class DataPatter:
    def __init__(self):
        base_data = []
    def makeInfoer():
        base_and_recordgap = []


class SystemNotifier:

    @staticmethod
    def notify(message, title="集中力モニター", subtitle="", sound=True):
        """macOS通知センターに表示"""
        print("通知を送信中...")
        try:
            # AppleScriptで通知
            script = f'display notification "{message}" with title "{title}" subtitle "{subtitle}"'
            if sound:
                script += ' sound name "Glass"'
            subprocess.run(['osascript', '-e', script])
            print(f"✅ 通知送信: {message}")
            return True
        except Exception as e:
            print(f"❌ 通知エラー: {e}")
            return False

    @staticmethod
    def speak(text):
        """音声で読み上げ"""
        subprocess.run(['say', text])

    @staticmethod
    def notify_with_dialog(message, title="警告"):
        """ダイアログ表示（確実に気づく）"""
        script = f'display dialog "{message}" with title "{title}" buttons {{"OK"}} default button "OK" with icon caution'
        subprocess.run(['osascript', '-e', script])

def on_threshold_change(v):
    value = round(float(v), 2)
    gaze_settings.threshold.set(value)
    lbl1.config(text=f"{value:.2f}")

def open_settings_window(path=None):
    """目線判定パラメータを調整する簡易UI。

    呼び出しは引数なしでも動作します(`path` はオプションで画像表示用)。
    値はグローバル `gaze_settings` から取得・更新されます。
    """
    settings_win = tk.Toplevel(root)
    settings_win.title("Gaze Monitor Settings")
    settings_win.geometry("400x320")
    settings_win.resizable(False, False)

    threshold_text = tk.StringVar(value=f"{gaze_settings.threshold.get():.2f}")
    distraction_text = tk.StringVar(value=f"{gaze_settings.distraction_time.get():.1f}s")
    cooldown_text = tk.StringVar(value=f"{gaze_settings.notification_cooldown.get()}s")

    ttk.Label(settings_win, text="🎯 目線判定設定", font=("Arial", 14, "bold")).pack(pady=8)

    # ===== 閾値スライダー =====
    frame1 = ttk.Frame(settings_win)
    frame1.pack(fill="x", padx=12, pady=6)
    threshold_text = tk.StringVar(
        value=f"{gaze_settings.threshold.get():.2f}"
    )
    ttk.Label(frame1, text="閾値 (0.0〜1.0):").pack(side="left")

    def update_threshold(value):
        snapped = int(round(float(value)))
        real_value = snapped / 100  # ← 実際の閾値
        gaze_settings.threshold.set(real_value)
        threshold_text.set(f"{real_value:.2f}")
    
    scale1 = ttk.Scale(
        frame1,
        from_=0,
        to=100,
        orient="horizontal",
        length=220,
        command=update_threshold
    )
    scale1.set(gaze_settings.threshold.get())
    scale1.pack(side="left", padx=8)

    ttk.Label(frame1, textvariable=threshold_text, width=6).pack(side="left")

    # 通知までの時間スライダー
    frame2 = ttk.Frame(settings_win)
    frame2.pack(fill="x", padx=12, pady=6)
    ttk.Label(frame2, text="通知まで (秒):").pack(side="left")
    
    def update_distraction_time(value):
        snapped = round(float(value) * 10) / 10  # 0.1刻み
        gaze_settings.distraction_time.set(snapped)
        distraction_text.set(f"{snapped:.1f}s")
    
    scale2 = ttk.Scale(
        frame2,
        from_=1.0,
        to=30.0,
        orient="horizontal",
        length=220,
        command=update_distraction_time
    )
    scale2.set(gaze_settings.distraction_time.get())
    scale2.pack(side="left", padx=8)
    
    ttk.Label(frame2, textvariable=distraction_text, width=6).pack(side="left")

    # 通知間隔スライダー
    frame3 = ttk.Frame(settings_win)
    frame3.pack(fill="x", padx=12, pady=6)
    ttk.Label(frame3, text="通知間隔 (秒):").pack(side="left")
    
    def update_cooldown(value):
        snapped = int(round(float(value)))  # 整数に丸める
        gaze_settings.notification_cooldown.set(snapped)
        cooldown_text.set(f"{snapped}s")
    
    scale3 = ttk.Scale(
        frame3,
        from_=5,
        to=120,
        orient="horizontal",
        length=220,
        command=update_cooldown
    )
    scale3.set(gaze_settings.notification_cooldown.get())
    scale3.pack(side="left", padx=8)
    
    ttk.Label(frame3, textvariable=cooldown_text, width=6).pack(side="left")

    # 画像プレビュー(オプション)
    if path:
        try:
            img = Image.open(path)
            img = img.resize((200, 120))
            photo = ImageTk.PhotoImage(img)
            img_label = ttk.Label(settings_win, image=photo)
            img_label.image = photo
            img_label.pack(pady=6)
        except Exception:
            pass

    btn_frame = ttk.Frame(settings_win)
    btn_frame.pack(fill="x", padx=12, pady=10)

    def on_save():
        print("設定保存:",
              f"threshold={gaze_settings.threshold.get():.2f}",
              f"distraction_time={gaze_settings.distraction_time.get():.1f}",
              f"cooldown={gaze_settings.notification_cooldown.get()}")
        settings_win.destroy()

    ttk.Button(btn_frame, text="保存して閉じる", command=on_save).pack(side="right", padx=6)
    ttk.Button(btn_frame, text="キャンセル", command=settings_win.destroy).pack(side="right")

class GazeMonitorWithNotification:
    def __init__(self, 
                 gaze_threshold=0.35,
                 distraction_time=5.0,
                 cooldown_time=10.0,
                 fps=30):

        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        self.fps = fps
        self.distracted_threshold = int(distraction_time * fps)
        self.LEFT_IRIS = [474, 475, 476, 477]
        self.RIGHT_IRIS = [469, 470, 471, 472]
        
        # 目線ずれの監視設定
        self.distracted_frames = 0
        self.last_notification_time = 0
        self.notification_cooldown = cooldown_time
        self.notification_count = 0
        # 状態管理
        self.last_direction = "CENTER"
        # 統計情報
        self.total_frames = 0
        self.focused_frames = 0
        self.notifier = SystemNotifier()

        print(f"=== 初期設定 ===")
        print(f"目線ずれ閾値: {gaze_threshold}")
        print(f"通知までの時間: {distraction_time}秒")
        print(f"通知間隔: {cooldown_time}秒")
        print("================")

    def compute_eye_relative_gaze(self, landmarks, iris_ids,
                                eye_inner_id, eye_outer_id,
                                eye_upper_id, eye_lower_id,
                                w, h):
        """
        単眼の眼球内相対視線を計算
        戻り値: (offset_x, offset_y)
        """

        # ランドマーク座標取得
        eye_inner = np.array([landmarks[eye_inner_id].x * w,
                            landmarks[eye_inner_id].y * h])
        eye_outer = np.array([landmarks[eye_outer_id].x * w,
                            landmarks[eye_outer_id].y * h])
        eye_upper = np.array([landmarks[eye_upper_id].x * w,
                            landmarks[eye_upper_id].y * h])
        eye_lower = np.array([landmarks[eye_lower_id].x * w,
                            landmarks[eye_lower_id].y * h])

        # 虹彩中心
        iris_center = np.mean([
            [landmarks[i].x * w, landmarks[i].y * h]
            for i in iris_ids
        ], axis=0)

        # 眼球中心（原点）
        eye_center = (eye_inner + eye_outer) / 2

        # 眼球内軸
        eye_x_axis = eye_outer - eye_inner
        eye_x_axis /= np.linalg.norm(eye_x_axis)

        eye_y_axis = eye_lower - eye_upper
        eye_y_axis /= np.linalg.norm(eye_y_axis)

        # 差分（ピクセル）
        diff = iris_center - eye_center

        # 👇 正規化は「目の幅」で1回だけ
        eye_width = np.linalg.norm(eye_outer - eye_inner)
        eye_height = np.linalg.norm(eye_lower - eye_upper)

        offset_x = np.dot(diff, eye_x_axis) / eye_width
        offset_y = np.dot(diff, eye_y_axis) / eye_height

        return offset_x, offset_y, iris_center, eye_center

    def _classify_direction(self, x, y):
        """視線方向を分類（相対位置ベース）"""
        threshold = gaze_settings.threshold.get()

        if abs(x) < threshold and abs(y) < threshold:
            return "CENTER"
        elif abs(x) > abs(y):
            return "RIGHT" if x > 0 else "LEFT"  # 正が右、負が左
        else:
            return "DOWN" if y > 0 else "UP"     # 正が下、負が上

    def update_settings_from_ui(self):
        """UI から動的に設定を更新"""
        self.gaze_threshold = gaze_settings.threshold.get()
        self.distraction_time = gaze_settings.distraction_time.get()
        self.notification_cooldown = gaze_settings.notification_cooldown.get()
        self.distracted_threshold = int(self.distraction_time * self.fps)

    def detect_gaze(self, frame):
        """視線検出（目の枠内での瞳孔の相対位置ベース）"""
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            return None, frame

        landmarks = results.multi_face_landmarks[0].landmark

        # 左目の枠と瞳孔
        LEFT_EYE_OUTER = 263  # 左目外側
        LEFT_EYE_INNER = 362  # 左目内側
        LEFT_EYE_TOP = 386    # 左目上
        LEFT_EYE_BOTTOM = 374 # 左目下
        
        # 右目の枠と瞳孔
        RIGHT_EYE_OUTER = 33  # 右目外側
        RIGHT_EYE_INNER = 133 # 右目内側
        RIGHT_EYE_TOP = 159   # 右目上
        RIGHT_EYE_BOTTOM = 145 # 右目下

        # 虹彩中心を取得
        left_iris = np.mean([
            [landmarks[i].x * w, landmarks[i].y * h] 
            for i in self.LEFT_IRIS
        ], axis=0)

        right_iris = np.mean([
            [landmarks[i].x * w, landmarks[i].y * h] 
            for i in self.RIGHT_IRIS
        ], axis=0)

        # 左目の枠を取得
        left_eye_outer = np.array([landmarks[LEFT_EYE_OUTER].x * w, landmarks[LEFT_EYE_OUTER].y * h])
        left_eye_inner = np.array([landmarks[LEFT_EYE_INNER].x * w, landmarks[LEFT_EYE_INNER].y * h])
        left_eye_top = np.array([landmarks[LEFT_EYE_TOP].x * w, landmarks[LEFT_EYE_TOP].y * h])
        left_eye_bottom = np.array([landmarks[LEFT_EYE_BOTTOM].x * w, landmarks[LEFT_EYE_BOTTOM].y * h])

        # 右目の枠を取得
        right_eye_outer = np.array([landmarks[RIGHT_EYE_OUTER].x * w, landmarks[RIGHT_EYE_OUTER].y * h])
        right_eye_inner = np.array([landmarks[RIGHT_EYE_INNER].x * w, landmarks[RIGHT_EYE_INNER].y * h])
        right_eye_top = np.array([landmarks[RIGHT_EYE_TOP].x * w, landmarks[RIGHT_EYE_TOP].y * h])
        right_eye_bottom = np.array([landmarks[RIGHT_EYE_BOTTOM].x * w, landmarks[RIGHT_EYE_BOTTOM].y * h])

        # 左目の幅と高さを計算
        left_eye_width = np.linalg.norm(left_eye_outer - left_eye_inner)
        left_eye_height = np.linalg.norm(left_eye_top - left_eye_bottom)
        
        # 右目の幅と高さを計算
        right_eye_width = np.linalg.norm(right_eye_outer - right_eye_inner)
        right_eye_height = np.linalg.norm(right_eye_top - right_eye_bottom)

        # 左目の中心を計算
        left_eye_center = (left_eye_outer + left_eye_inner) / 2
        
        # 右目の中心を計算
        right_eye_center = (right_eye_outer + right_eye_inner) / 2

        # 瞳孔の相対位置を計算（-1.0 ~ 1.0の範囲に正規化）
        # 左目: 左側が負、右側が正
        left_gaze_x = (left_iris[0] - left_eye_center[0]) / (left_eye_width / 2) if left_eye_width > 0 else 0
        left_gaze_y = (left_iris[1] - left_eye_center[1]) / (left_eye_height / 2) if left_eye_height > 0 else 0
        
        # 右目: 左側が負、右側が正
        right_gaze_x = (right_iris[0] - right_eye_center[0]) / (right_eye_width / 2) if right_eye_width > 0 else 0
        right_gaze_y = (right_iris[1] - right_eye_center[1]) / (right_eye_height / 2) if right_eye_height > 0 else 0

        # 両目の平均を取る
        gaze_x = (left_gaze_x + right_gaze_x) / 2
        gaze_y = (left_gaze_y + right_gaze_y) / 2

        direction = self._classify_direction(gaze_x, gaze_y)
        is_focused = direction == "CENTER"

        # 描画（デバッグ用に目の枠も表示）
        annotated = self._draw_gaze(frame, left_iris.astype(int), right_iris.astype(int), 
                                    ((left_iris + right_iris) / 2).astype(int), 
                                    direction, is_focused,
                                    left_eye_outer.astype(int), left_eye_inner.astype(int),
                                    right_eye_outer.astype(int), right_eye_inner.astype(int))

        return {
            'direction': direction,
            'is_focused': is_focused,
            'gaze_x': gaze_x,
            'gaze_y': gaze_y,
            'left_gaze_x': left_gaze_x,
            'left_gaze_y': left_gaze_y,
            'right_gaze_x': right_gaze_x,
            'right_gaze_y': right_gaze_y,
        }, annotated

    def monitor(self, frame):
        """目線監視とアクション実行"""
        # UI から設定を更新
        self.update_settings_from_ui()

        gaze_info, annotated = self.detect_gaze(frame)

        if gaze_info:
            self.total_frames += 1
            direction = gaze_info['direction']
            is_focused = gaze_info['is_focused']

            distracted_seconds = self.distracted_frames / self.fps

            # 方向変化があった場合 → カウントリセット
            if direction != self.last_direction:
                self.distracted_frames = 0
                self.last_direction = direction
                print(f"リセット: {direction} | リセット")
            else:
                # 同じ方向が続いている
                self.distracted_frames += 1

            distracted_seconds = self.distracted_frames / self.fps
            print(f"is_focused: {is_focused} | 経過: {distracted_seconds:.2f}s | 閾値: {self.gaze_threshold:.2f}")
            print(f"direction: {direction} | 経過: {self.last_direction}")
            print(f"distracted_frames: {self.distracted_frames} | distracted_threshold: {int(self.distracted_threshold)}")

            # 集中状態ならフレームを加算
            if is_focused:
                self.focused_frames += 1

            # 同じ方向が一定時間続いたら通知（ただし設定値に基づいて）
            if (is_focused == True and 
                int(self.distracted_frames) >= int(self.distracted_threshold)):
                print(f": {self.distracted_frames} | self.distracted_threshold: {self.distracted_threshold}")

                current_time = time.time()
                if current_time - self.last_notification_time > self.notification_cooldown:
                    self._send_notification()
                    self.last_notification_time = current_time

            # 統計情報を表示
            focus_rate = (self.focused_frames / self.total_frames * 100) if self.total_frames > 0 else 0
            cv2.putText(annotated, f"Focus Rate: {focus_rate:.1f}%", 
                       (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            # 現在の設定を表示
            cv2.putText(annotated, f"Threshold: {self.gaze_threshold:.2f}", 
                       (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        return annotated

    def _classify_direction(self, x, y):
        """視線方向を分類"""
        threshold = gaze_settings.threshold.get()

        if abs(x) < threshold and abs(y) < threshold:
            return "CENTER"
        elif abs(x) > abs(y):
            return "LEFT" if x < 0 else "RIGHT"
        else:
            return "UP" if y < 0 else "DOWN"

    def _draw_gaze(self, frame, left_iris, right_iris, eyes_center, direction, is_focused,
                left_outer=None, left_inner=None, right_outer=None, right_inner=None):
        """視線の描画"""
        annotated = frame.copy()

        # 目の枠を描画（デバッグ用）
        if left_outer is not None and left_inner is not None:
            cv2.line(annotated, tuple(left_outer), tuple(left_inner), (255, 255, 0), 1)
        if right_outer is not None and right_inner is not None:
            cv2.line(annotated, tuple(right_outer), tuple(right_inner), (255, 255, 0), 1)

        # 虹彩
        cv2.circle(annotated, tuple(left_iris), 3, (0, 255, 0), -1)
        cv2.circle(annotated, tuple(right_iris), 3, (0, 255, 0), -1)

        # 目の中心
        color = (0, 255, 0) if is_focused else (0, 0, 255)
        cv2.circle(annotated, tuple(eyes_center), 5, color, -1)

        # ステータス表示
        status = "FOCUSED" if is_focused else f"DISTRACTED ({direction})"
        cv2.putText(annotated, f"Status: {status}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        return annotated

    def _send_notification(self):
        """通知を送信（複数の方法を試す）"""
        self.notification_count += 1
        
        # ★方法1: osascript通知（最優先）
        success = self.notifier.notify(
            message="目線がずらしてください！ 画面に視点をタスクスケジュールを再評価してください",
            title="集中力モニター",
            subtitle=f"{self.notification_count}回目の警告",
            sound=True
        )

        # ★方法2: 音声通知（確実）
        # self.notifier.speak("目線がずらしてください！画面に視点をタスクスケジュールを再評価してください")

        # ★方法3: ターミナルに大きく表示
        print("\n" + "="*50)
        print("🚨 警告: 目線がずれています！ 🚨")
        print(f"通知回数: {self.notification_count}")
        print("="*50 + "\n")

# 使用例
def main():
    monitor = GazeMonitorWithNotification()
    cap = cv2.VideoCapture(0)

    print("=== 目線モニター開始 ===")
    print("'s'キーで設定ウィンドウを開く")
    print("'q'キーで終了")
    print()
    open_settings_window()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        annotated = monitor.monitor(frame)
        cv2.imshow('Gaze Monitor', annotated)

        # Tkinter のウィンドウイベントを処理して、
        # `open_settings_window()` で作成した Toplevel が応答するようにする
        try:
            root.update()
        except tk.TclError:
            # Tk が既に破棄されている等のエラーは無視
            pass

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            open_settings_window()

    cap.release()
    cv2.destroyAllWindows()

    # 最終統計
    if monitor.total_frames > 0:
        focus_rate = monitor.focused_frames / monitor.total_frames * 100
        print(f"\n=== 統計情報 ===")
        print(f"総フレーム数: {monitor.total_frames}")
        print(f"集中フレーム数: {monitor.focused_frames}")
        print(f"集中率: {focus_rate:.1f}%")


if __name__ == "__main__":
    main()
    root.mainloop()
                    