import cv2, time
import mediapipe as mp
import numpy as np
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import subprocess

root = tk.Tk()
root.withdraw() 

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

def open_settings_window(path):
    win = tk.Toplevel(root)
    win.title("Settings")
    win.geometry("300x200")

    # 画像読み込み
    img = Image.open(path)
    img = img.resize((200, 150))  # サイズ調整（任意）
    photo = ImageTk.PhotoImage(img)

    # 画像表示（★参照保持が超重要）
    img_label = ttk.Label(win, image=photo)
    img_label.image = photo
    img_label.pack(pady=10)

    ttk.Label(win, text="Sensitivity").pack(pady=5)
    ttk.Scale(win, from_=200, to=8000,
              orient="horizontal").pack(fill="x", padx=20)


    ttk.Button(win, text="Close", command=win.destroy).pack(pady=10)


class GazeMonitorWithNotification:
    def __init__(self, 
                 gaze_threshold=0.2,  # 目線ずれの閾値（調整可能）
                 distraction_time=5.0,  # 何秒同じであれば通知するか
                 cooldown_time=60.0,    # 通知間隔
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
        self.notification_cooldown = 10  # 10秒のクールダウン
        self.notification_count = 0
        # 状態管理
        self.distracted_frames = 0
        self.last_notification_time = 0
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

    def detect_gaze(self, frame):
        """視線検出"""
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            return None, frame

        landmarks = results.multi_face_landmarks[0].landmark

        # 虹彩中心を取得
        left_iris = np.mean([
            [landmarks[i].x * w, landmarks[i].y * h] 
            for i in self.LEFT_IRIS
        ], axis=0).astype(int)

        right_iris = np.mean([
            [landmarks[i].x * w, landmarks[i].y * h] 
            for i in self.RIGHT_IRIS
        ], axis=0).astype(int)

        eyes_center = ((left_iris + right_iris) / 2).astype(int)
        screen_center = np.array([w // 2, h // 2])
        gaze_vector = eyes_center - screen_center

        gaze_x = gaze_vector[0] / (w // 2)
        gaze_y = gaze_vector[1] / (h // 2)

        direction = self._classify_direction(gaze_x, gaze_y)
        is_focused = direction == "CENTER"

        # 描画
        annotated = self._draw_gaze(frame, left_iris, right_iris, 
                                     eyes_center, direction, is_focused)

        return {
            'direction': direction,
            'is_focused': is_focused,
            'gaze_x': gaze_x,
            'gaze_y': gaze_y,
        }, annotated

    def monitor(self, frame):
        """目線監視とアクション実行"""
        gaze_info, annotated = self.detect_gaze(frame)

        if gaze_info:
            self.total_frames += 1
            direction = gaze_info['direction']
            is_focused = gaze_info['is_focused']
            # if gaze_info['is_focused']:
            #     self.focused_frames += 1
            #     self.distracted_frames = 0  # リセット
            # else:
            #     self.distracted_frames += 1

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
            print(f"is_focused: {is_focused} | 経過: {distracted_seconds:.2f}s")
            print(f"direction: {direction} | 経過: {self.last_direction}")
            print(f"distracted_frames: {self.distracted_frames} | distracted_threshold: {int(self.distracted_threshold)}")

            # 集中状態ならフレームを加算
            if is_focused:
                self.focused_frames += 1

            # 同じ方向が一定時間続いたら通知（ただし10分に1回まで）
            if (is_focused == True and 
                int(self.distracted_frames) >= int(self.distracted_threshold)):
                print(f": {self.distracted_frames} | self.distracted_threshold: {self.distracted_threshold}")

                current_time = time.time()
                if current_time - self.last_notification_time > self.notification_cooldown:
                    self._send_notification()
                    open_settings_window("./images/imager.png")
                    self.last_notification_time = current_time

            # # 目線が同じである場合
            # if self.distracted_frames >= self.distracted_threshold:
            #     current_time = time.time()
            #     print(f"2@@distracted_threshold: {self.distracted_threshold}")
            #     print(f"2@@distracted_frames: {self.distracted_frames}")

            #     # クールダウン期間が経過していれば通知
            #     if current_time - self.last_notification_time > self.notification_cooldown:
            #         print(f"2@@目線ずれフレーム数: {self.distracted_frames}")
            #         self._send_notification()
            #         self.last_notification_time = current_time
            #         self.distracted_frames = 0  # リセット

            # 統計情報を表示
            focus_rate = (self.focused_frames / self.total_frames * 100) if self.total_frames > 0 else 0
            cv2.putText(annotated, f"Focus Rate: {focus_rate:.1f}%", 
                       (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            # 警告表示
            # if self.distracted_frames > 30:
            #     remaining = self.distracted_threshold - self.distracted_frames
            #     cv2.putText(annotated, f"Warning in: {remaining // 30}s", 
            #                (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        return annotated

    def _classify_direction(self, x, y):
        """視線方向を分類"""
        threshold = 0.35

        if abs(x) < threshold and abs(y) < threshold:
            return "CENTER"
        elif abs(x) > abs(y):
            return "LEFT" if x < 0 else "RIGHT"
        else:
            return "UP" if y < 0 else "DOWN"

    def _draw_gaze(self, frame, left_iris, right_iris, eyes_center, direction, is_focused):
        """視線の描画"""
        annotated = frame.copy()

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
    print("目線が3秒以上ずれると通知が表示されます")
    print("'q'キーで終了")
    print()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        annotated = monitor.monitor(frame)
        cv2.imshow('Gaze Monitor', annotated)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    # 最終統計
    if monitor.total_frames > 0:
        focus_rate = monitor.focused_frames / monitor.total_frames * 100
        print(f"\n=== 統計情報 ===")
        print(f"総フレーム数: {monitor.total_frames}")
        print(f"集中フレーム数: {monitor.focused_frames}")
        print(f"集中率: {focus_rate:.1f}%")

    # detector = GazeDetector()
    # cap = cv2.VideoCapture(0)
    # print("Press 'q' to quit.")

    # while cap.isOpened():
    #     ret, frame = cap.read()
    #     if not ret:
    #         break
        
    #     gaze_info, annotated_frame = detector.get_gaze_direction(frame)
        
    #     if gaze_info:
    #         print(f"Direction: {gaze_info['direction']}, "
    #               f"Ratio X: {gaze_info['gaze_ratio_x']:.2f}, "
    #               f"Ratio Y: {gaze_info['gaze_ratio_y']:.2f}")
        
    #     cv2.imshow('Gaze Detection', annotated_frame)
        
    #     if cv2.waitKey(1) & 0xFF == ord('q'):
    #         break
    
    # cap.release()
    # cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
    root.mainloop()
                    