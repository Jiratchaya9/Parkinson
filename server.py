from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
import mediapipe as mp
import pandas as pd
import time
from scipy.signal import butter, filtfilt, stft
from sklearn.decomposition import PCA
import os
app = Flask(__name__)
CORS(app)
SAVE_VIDEO_PATH = "uploaded_video.mp4"
SAVE_CSV_PATH = "hand_data.csv"
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
def bandpass_filter(signal, lowcut=0.3, highcut=9.0, fs=30, order=4): #เปลี่ยน fs = 30
    b, a = butter(order, [lowcut / (fs / 2), highcut / (fs / 2)], btype='band')
    return filtfilt(b, a, signal)
def process_video(video_path):
    print(f"เริ่มประมวลผลวิดีโอ")
    cap = cv2.VideoCapture(video_path)
    input_fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"FPS ที่ได้จาก ImagePicker: {input_fps}")
    output_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    output_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    output_path = "output_with_hand.mp4"
    if os.path.exists("output_with_hand.mp4"):
        os.remove("output_with_hand.mp4")
    out = cv2.VideoWriter(output_path, fourcc, input_fps, (output_width, output_height))
    frame_idx = 0
    data = {'Frame': [], 'Time': []}
    for i in range(21):
        data[f'Landmark_{i}_X'] = []
        data[f'Landmark_{i}_Y'] = []
        data[f'Landmark_{i}_Z'] = []

    with mp_hands.Hands(model_complexity=0, min_detection_confidence=0.5, min_tracking_confidence=0.5) as hands:
        while cap.isOpened():
            success, image = cap.read()
            if not success:
                break
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = hands.process(image)

            if results.multi_hand_landmarks and len(results.multi_hand_landmarks) == 1:
                hand_landmarks = results.multi_hand_landmarks[0]
                data['Frame'].append(frame_idx)
                data['Time'].append(frame_idx / input_fps)
                for i, landmark in enumerate(hand_landmarks.landmark):
                    data[f'Landmark_{i}_X'].append(landmark.x)
                    data[f'Landmark_{i}_Y'].append(landmark.y)
                    data[f'Landmark_{i}_Z'].append(landmark.z)

                mp_drawing.draw_landmarks(
                image,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS,
                mp_drawing_styles.get_default_hand_landmarks_style(),
                mp_drawing_styles.get_default_hand_connections_style())
            out.write(cv2.cvtColor(image,cv2.COLOR_RGB2BGR))
            frame_idx += 1
    cap.release()
    out.release()
    df = pd.DataFrame(data)
    df.to_csv(SAVE_CSV_PATH, index=False)

    landmark_x = df.iloc[:, 2::3].values
    landmark_y = df.iloc[:, 3::3].values
    landmark_z = df.iloc[:, 4::3].values

    offset_samples = int(1 * input_fps)
    offset_x = np.mean(landmark_x[:offset_samples, :], axis=0)
    offset_y = np.mean(landmark_y[:offset_samples, :], axis=0)
    offset_z = np.mean(landmark_z[:offset_samples, :], axis=0)

    landmark_x -= offset_x
    landmark_y -= offset_y
    landmark_z -= offset_z

    noise_threshold = 0.0075
    landmark_x[np.abs(landmark_x) < noise_threshold] = 0
    landmark_y[np.abs(landmark_y) < noise_threshold] = 0
    landmark_z[np.abs(landmark_z) < noise_threshold] = 0

    data_matrix = np.vstack([
        landmark_x.mean(axis=1),
        landmark_y.mean(axis=1),
        landmark_z.mean(axis=1)
    ]).T
    pca = PCA(n_components=3)
    principal_components = pca.fit_transform(data_matrix)
    pc1 = bandpass_filter(principal_components[:, 0], fs=input_fps)
    f_pc1, t_pc1, Zxx_pc1 = stft(pc1, fs=input_fps, nperseg=512, noverlap=384)
    magnitude_spectrum = np.abs(Zxx_pc1)
    valid_freq_idx = (f_pc1 >= 0.1) & (f_pc1 <= 9.0)
    filtered_magnitude = magnitude_spectrum[valid_freq_idx, :]

    if np.all(filtered_magnitude == 0):
        return 0.0
    else:
        global_max_index = np.unravel_index(np.argmax(filtered_magnitude, axis=None), filtered_magnitude.shape)
        freq = f_pc1[valid_freq_idx][global_max_index[0]]
        print(f"เสร็จสิ้นความถี่ = {freq:.2f} Hz")
        return freq
latest_result = None
@app.route('/upload', methods=['POST'])
def upload():
    global latest_result

    print("วิดีโอถูกส่งเข้ามาแล้ว")
    latest_result = None
    if 'video' not in request.files:
        print("ไม่มีวิดีโอที่ถูกอัปโหลด")
        return jsonify({"error": "No video uploaded"}), 400
    video = request.files['video']
    video.save(SAVE_VIDEO_PATH)
    print(f"วิดีโอถูกบันทึก:", SAVE_VIDEO_PATH)
    start = time.time()
    freq = process_video(SAVE_VIDEO_PATH)
    end = time.time()
    #os.remove(SAVE_VIDEO_PATH) #ลบวิดีโอออกเมื่อประมวลผลเเสร็จ
    risk = "ปกติ"
    if 4 <= freq <= 6:
        risk = "เสี่ยงสูง"
    elif 3 <= freq < 4 or 6 < freq <= 7:
        risk = "เสี่ยงปานกลาง"

    latest_result = {
        "max_frequency": round(freq, 2),
        "risk": risk,
        "processing_time": round(end - start, 2)
    }
    return jsonify(latest_result)

@app.route('/status', methods=['GET'])
def check_status():
    if latest_result:
        return jsonify({"processed": True, "result": latest_result})
    return jsonify({"processed": False})

@app.route('/results', methods=['GET'])
def get_results():
    if not latest_result:
        return jsonify({"error": "No results available"}), 404
    return jsonify(latest_result)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
