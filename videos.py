import cv2, time, logging, yaml, os
import numpy as np
from movier.step01 import detect_people, visualize_detections
from utils import power, scheduler, network, security
from utils.scheduler import run_scheduled_tasks
import threading
import fast_module as fast_module

network_latency = {"ping_ms": None}

def monitor_network_latency():
    """バックグラウンドで定期的にpingを測定"""
    while True:
        latency = network.ping("8.8.8.8")
        network_latency["ping_ms"] = latency
        time.sleep(5)

def main():
    # ネットワーク監視スレッド開始
    threading.Thread(target=monitor_network_latency, daemon=True).start()

    power.init_monitor()
    security.initialize_keys()

    print(f"Current network latency: {network_latency['ping_ms']} ms")

    cap = cv2.VideoCapture(0)  # 🎥 カメラ入力
    if not cap.isOpened():
        print("Error: カメラが開けません。")
        return

    # 出力動画設定
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out = cv2.VideoWriter("output/camera_output.mp4", fourcc, fps, (width, height))

    frame_buffer = []
    window_size = 16

    while True:
        ret, frame = cap.read()

        if not ret:
            break

        # 人検出
        boxes, scores = detect_people(frame)

        # Python版描画
        frame_py = frame.copy()
        visualize_detections(frame_py, boxes, scores)

        # C++版描画
        frame_cpp = frame.copy()
        # fast_module.visualize_detections は py::array_t<uint8_t> を想定しているので numpy を渡す
        fast_module.visualize_detections(frame_cpp, boxes.tolist(), scores.tolist())

        # ピクセル差分
        diff = cv2.absdiff(frame_py, frame_cpp)
        mae = np.mean(diff)
        print(f"Python vs C++ 描画差分（MAE）: {mae:.2f}")

        # 差分表示
        cv2.imshow("Python", frame_py)
        cv2.imshow("C++", frame_cpp)
        cv2.imshow("差分", diff)


        # # 🔽 C拡張で平均スコア計算
        # if scores is not None and len(scores) > 0:
        #     avg_score = fast_module.average([float(s) for s in scores])
        # else:
        #     avg_score = 0.0

        # logging.info(f"Detection avg_score={avg_score:.3f}")
        # # === Python版平均 ===
        # avg_py = sum(scores) / len(scores) if len(scores) > 0 else 0.0
        # # === C++版平均 ===
        # avg_cpp = fast_module.average(scores.tolist() if hasattr(scores, "tolist") else list(scores))
        # print(f"Python平均: {avg_py:.3f}, C++平均: {avg_cpp:.3f}, 差={abs(avg_py-avg_cpp):.6f}")


        # # 描画
        # display = frame.copy()
        # visualize_detections(display, boxes, scores)

        # # 表示
        # cv2.imshow("Camera Detection", display)

        # # 🔽 ★ 動画に書き込み
        # out.write(display)

        # # 🔽 ★ 必要に応じてバッファ保持（後で動作認識に使うなど）
        # frame_buffer.append(frame)
        # if len(frame_buffer) > window_size:
        #     frame_buffer.pop(0)

        # # 'q' で終了
        # if cv2.waitKey(1) & 0xFF == ord('q'):
        #     break

    # リソース解放
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print("✅ カメラ映像を保存しました。")


if __name__ == "__main__":
    # cap = cv2.VideoCapture(0)

    # if not cap.isOpened():
    #     print("❌ カメラが開けません。")
    # else:
    #     print("✅ カメラが開きました。")

    # cap.release()
    main()

# config_path = yaml.safe_load(open("config.yaml"))

# os.makedirs("logs", exist_ok=True)
# logging.basicConfig(filename="logs/movier.log", level=logging.INFO)

# cap = cv2.VideoCapture(config_path.get("video_source"))
# fps = cap.get(cv2.CAP_PROP_FPS)

# state = { "count":0, "present": False }

# power.init_monitor()
# network.init_client(config_path["network"]["host"], config_path["network"]["port"])
# security.initialize_keys()

# try:
#   while True:
#     ret, frame = cap.read()
#     if not ret:
#         break

#     boxes, scores = detect_people(frame)
#     if len(boxes) > 0:
#       state["count"] += 1
#       state["present"] = True
#     else:
#       state["count"] = max(0, state["count"] - 1)
#       if state["count"] == 0:
#         state["present"] = False

#     power.manage(state["present"])
#     network.publish_state(state)
#     scheduler.adjust(state["present"])
#     power.manage(state["present"])

#     cv2.imshow("Detector", frame)
#     if cv2.waitKey(1) & 0xFF == ord('q'):
#         break

#     time.sleep(1.0 / fps)

# except KeybordInterrupt:
#     pass

# finally:
#     cap.release()
#     cv2.destroyAllWindows()
#     power.shutdown_monitor()
#     logging.info("Program stopped.")
