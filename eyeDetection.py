import cv2, time
import mediapipe as mp
import numpy as np
import subprocess

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


# class GazeDetector:
#     def __init__(self):
#         self.mp_face_mesh = mp.solutions.face_mesh
#         self.face_mesh = self.mp_face_mesh.FaceMesh(
#             max_num_faces=1,
#             refine_landmarks=True,  # 瞳孔検出のため必要
#             min_detection_confidence=0.5,
#             min_tracking_confidence=0.5
#         )

#         # 虹彩のランドマークインデックス
#         self.LEFT_IRIS = [474, 475, 476, 477]
#         self.RIGHT_IRIS = [469, 470, 471, 472]

#         # 目の周囲のランドマーク
#         self.LEFT_EYE = [33, 133, 160, 159, 158, 144, 145, 153]
#         self.RIGHT_EYE = [362, 263, 387, 386, 385, 380, 374, 373]


#     def get_gaze_direction(self, frame):
#         """視線方向を判定"""
#         h, w = frame.shape[:2]
#         rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#         results = self.face_mesh.process(rgb_frame)
        
#         if not results.multi_face_landmarks:
#             return None, frame

#         face_landmarks = results.multi_face_landmarks[0]
        
#         # 左目の虹彩中心を計算
#         left_iris_center = self._get_iris_center(
#             face_landmarks, self.LEFT_IRIS, w, h
#         )

#         # 右目の虹彩中心を計算
#         right_iris_center = self._get_iris_center(
#             face_landmarks, self.RIGHT_IRIS, w, h
#         )

#         # 目の中心（眼窩の中心）を計算
#         left_eye_center = self._get_eye_center(
#             face_landmarks, self.LEFT_EYE, w, h
#         )
#         right_eye_center = self._get_eye_center(
#             face_landmarks, self.RIGHT_EYE, w, h
#         )
        
#         # 虹彩の相対位置から視線方向を判定
#         left_gaze = self._calculate_gaze_ratio(left_iris_center, left_eye_center)
#         right_gaze = self._calculate_gaze_ratio(right_iris_center, right_eye_center)
        
#         # 平均を取る
#         gaze_ratio_x = (left_gaze[0] + right_gaze[0]) / 2
#         gaze_ratio_y = (left_gaze[1] + right_gaze[1]) / 2

#         # 視線方向を判定
#         direction = self._classify_gaze_direction(gaze_ratio_x, gaze_ratio_y)

#         # 可視化
#         annotated_frame = self._draw_gaze(
#             frame, left_iris_center, right_iris_center,
#             left_eye_center, right_eye_center, direction
#         )

#         return {
#             'direction': direction,
#             'gaze_ratio_x': gaze_ratio_x,
#             'gaze_ratio_y': gaze_ratio_y,
#             'left_iris': left_iris_center,
#             'right_iris': right_iris_center,
#         }, annotated_frame

#     def _get_iris_center(self, landmarks, indices, w, h):
#         """虹彩の中心座標を計算"""
#         points = []
#         for idx in indices:
#             point = landmarks.landmark[idx]
#             points.append([point.x * w, point.y * h])

#         points = np.array(points)
#         center = np.mean(points, axis=0).astype(int)
#         return center

#     def _get_eye_center(self, landmarks, indices, w, h):
#         """目の中心座標を計算"""
#         points = []
#         for idx in indices:
#             point = landmarks.landmark[idx]
#             points.append([point.x * w, point.y * h])

#         points = np.array(points)
#         center = np.mean(points, axis=0).astype(int)
#         return center

#     def _calculate_gaze_ratio(self, iris_center, eye_center):
#         """虹彩の相対位置を計算（-1.0 ~ 1.0）"""
#         # 水平方向のズレ
#         dx = (iris_center[0] - eye_center[0]) / 30.0  # 正規化
#         # 垂直方向のズレ
#         dy = (iris_center[1] - eye_center[1]) / 20.0

#         # クリップ
#         dx = np.clip(dx, -1.0, 1.0)
#         dy = np.clip(dy, -1.0, 1.0)

#         return (dx, dy)

#     def _classify_gaze_direction(self, ratio_x, ratio_y):
#         """視線方向を分類"""
#         threshold_x = 0.15
#         threshold_y = 0.15

#         # 水平方向
#         if ratio_x < -threshold_x:
#             horizontal = "LEFT"
#         elif ratio_x > threshold_x:
#             horizontal = "RIGHT"
#         else:
#             horizontal = "CENTER"

#         # 垂直方向
#         if ratio_y < -threshold_y:
#             vertical = "UP"
#         elif ratio_y > threshold_y:
#             vertical = "DOWN"
#         else:
#             vertical = "CENTER"

#         # 組み合わせ
#         if horizontal == "CENTER" and vertical == "CENTER":
#             return "FORWARD"
#         elif horizontal == "CENTER":
#             return vertical
#         elif vertical == "CENTER":
#             return horizontal
#         else:
#             return f"{vertical}_{horizontal}"

#     def _draw_gaze(self, frame, left_iris, right_iris, 
#                     left_eye, right_eye, direction):
#         """視線の可視化"""
#         # 虹彩を描画
#         cv2.circle(frame, tuple(left_iris), 3, (0, 255, 0), -1)
#         cv2.circle(frame, tuple(right_iris), 3, (0, 255, 0), -1)

#         # 目の中心を描画
#         cv2.circle(frame, tuple(left_eye), 2, (255, 0, 0), -1)
#         cv2.circle(frame, tuple(right_eye), 2, (255, 0, 0), -1)

#         # 視線ベクトルを描画
#         scale = 50
#         left_end = (
#             left_iris[0] + int((left_iris[0] - left_eye[0]) * scale / 30),
#             left_iris[1] + int((left_iris[1] - left_eye[1]) * scale / 20)
#         )
#         right_end = (
#             right_iris[0] + int((right_iris[0] - right_eye[0]) * scale / 30),
#             right_iris[1] + int((right_iris[1] - right_eye[1]) * scale / 20)
#         )

#         cv2.arrowedLine(frame, tuple(left_iris), left_end, (0, 255, 255), 2)
#         cv2.arrowedLine(frame, tuple(right_iris), right_end, (0, 255, 255), 2)

#         # 方向テキスト
#         cv2.putText(frame, f"Gaze: {direction}", (10, 30),
#                     cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
#         return frame


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
            print(f"2@@distracted_frames: {self.distracted_frames} | distracted_threshold: {int(self.distracted_threshold)}")

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
                    print("¥¥¥¥¥¥¥¥¥¥¥¥¥¥¥¥¥¥¥¥¥¥¥¥¥¥¥¥¥¥¥¥¥¥¥¥")
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



