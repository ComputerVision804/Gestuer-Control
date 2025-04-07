import cv2
import mediapipe as mp
import numpy as np
import math
import tkinter as tk
import threading
import pyttsx3
import screen_brightness_control as sbc
import keyboard
import subprocess
import os
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# === Voice Engine Setup ===
engine = pyttsx3.init()
def speak(text):
    engine.say(text)
    engine.runAndWait()

# === GUI Setup ===
root = tk.Tk()
root.title("Gesture Control System")
root.geometry("400x150")
status_label = tk.Label(root, text="Initializing...", font=("Arial", 14))
status_label.pack(pady=10)
volume_label = tk.Label(root, text="Volume: ", font=("Arial", 12))
volume_label.pack()
brightness_label = tk.Label(root, text="Brightness: ", font=("Arial", 12))
brightness_label.pack()

def update_status(text):
    status_label.config(text=text)

def update_volume_label(vol_percent):
    volume_label.config(text=f"Volume: {vol_percent}%")

def update_brightness_label(bright_percent):
    brightness_label.config(text=f"Brightness: {bright_percent}%")

# === Audio Setup ===
devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = cast(interface, POINTER(IAudioEndpointVolume))
minVol, maxVol = volume.GetVolumeRange()[0], volume.GetVolumeRange()[1]

# === MediaPipe Setup ===
mpHands = mp.solutions.hands
hands = mpHands.Hands()
mpDraw = mp.solutions.drawing_utils

# === Video Capture ===
cap = cv2.VideoCapture(0)

def gesture_control():
    vol_mode = True  # Toggle between volume and brightness control

    while True:
        success, img = cap.read()
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = hands.process(imgRGB)

        if results.multi_hand_landmarks:
            for handLms in results.multi_hand_landmarks:
                lmList = []
                for id, lm in enumerate(handLms.landmark):
                    h, w, c = img.shape
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    lmList.append((id, cx, cy))

                if len(lmList) >= 16:
                    x1, y1 = lmList[4][1], lmList[4][2]    # Thumb tip
                    x2, y2 = lmList[8][1], lmList[8][2]    # Index tip
                    x3, y3 = lmList[12][1], lmList[12][2]  # Middle tip
                    x4, y4 = lmList[16][1], lmList[16][2]  # Ring tip
                    x5, y5 = lmList[20][1], lmList[20][2]  # Pinky tip

                    cx, cy = (x1 + x2)//2, (y1 + y2)//2
                    cv2.line(img, (x1, y1), (x2, y2), (0, 255, 0), 2)

                    length = math.hypot(x2 - x1, y2 - y1)

                    if vol_mode:
                        vol = np.interp(length, [30, 200], [minVol, maxVol])
                        volume.SetMasterVolumeLevel(vol, None)
                        vol_percent = int(np.interp(length, [30, 200], [0, 100]))
                        update_volume_label(vol_percent)
                        update_status("Volume Mode")
                        if vol_percent >= 99:
                            speak("Volume is maxed out")
                    else:
                        bright = int(np.interp(length, [30, 200], [10, 100]))
                        sbc.set_brightness(bright)
                        update_brightness_label(bright)
                        update_status("Brightness Mode")

                    # Gesture: Thumb + Pinky = Mode Toggle
                    if abs(x1 - x5) < 40 and abs(y1 - y5) < 40:
                        vol_mode = not vol_mode
                        mode = "Volume Mode" if vol_mode else "Brightness Mode"
                        update_status(f"Switched to {mode}")
                        speak(f"Switched to {mode}")

                    # Gesture: Thumb + Ring = Play/Pause Media
                    if abs(x1 - x4) < 40 and abs(y1 - y4) < 40:
                        keyboard.press_and_release("play/pause media")
                        update_status("Media Play/Pause")
                        speak("Toggled media")

                    # Gesture: Thumb + Middle = App Launcher (e.g., Calculator)
                    if abs(x1 - x3) < 40 and abs(y1 - y3) < 40:
                        subprocess.Popen("calc.exe")
                        update_status("Launching Calculator")
                        speak("Launching Calculator")

                    # Gesture: Thumb + Index + Pinky = Sleep Mode (system lock)
                    if abs(x1 - x2) < 40 and abs(x1 - x5) < 40:
                        update_status("Sleep Mode Activated")
                        speak("System going to sleep")
                        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

                mpDraw.draw_landmarks(img, handLms, mpHands.HAND_CONNECTIONS)

        cv2.imshow("Gesture Control", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# Run the gesture control in a separate thread
threading.Thread(target=gesture_control, daemon=True).start()

# Start GUI loop
root.mainloop()
