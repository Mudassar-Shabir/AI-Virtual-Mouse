import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import time
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

pyautogui.PAUSE = 0

# -----------------------
# Volume Control Setup
# -----------------------

devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(
    IAudioEndpointVolume._iid_,
    CLSCTX_ALL,
    None
)

volume = cast(interface, POINTER(IAudioEndpointVolume))

minVol, maxVol = volume.GetVolumeRange()[:2]

volume_mode = False

# -------------------------------
# Load MediaPipe Hand Model
# -------------------------------
mp_hands = mp.solutions.hands

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

# Drawing Utility
mp_draw = mp.solutions.drawing_utils

# Open Camera
cap = cv2.VideoCapture(0)
screen_w, screen_h = pyautogui.size()

# Finger Tip IDs
tips = [4, 8, 12, 16, 20]
prev_x = 0
prev_y = 0

smoothening = 5
clicked = False
dragging = False
right_clicked = False
double_clicked = False
pinch_start = 0
scroll_mode = False
scroll_y = 0
drag_start = 0

while True:

    success, frame = cap.read()

    if not success:
        break

    # Mirror Effect
    frame = cv2.flip(frame, 1)

    # Convert BGR to RGB
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Detect Hand
    results = hands.process(rgb)

    count = 0

    if results.multi_hand_landmarks:

        for hand in results.multi_hand_landmarks:
            gesture = "MOVE"

            # Draw Hand
            mp_draw.draw_landmarks(
                frame,
                hand,
                mp_hands.HAND_CONNECTIONS
            )
            # Frame Size
            # Frame Size
            h, w, c = frame.shape

            # Index Finger Tip
            index_tip = hand.landmark[8]
            middle_tip = hand.landmark[12]
            ring_tip = hand.landmark[16]
            thumb_tip = hand.landmark[4]
            index_pip = hand.landmark[6]
            middle_pip = hand.landmark[10]
            pinky_tip = hand.landmark[20]


            # Convert to Pixels
            x = int(index_tip.x * w)
            y = int(index_tip.y * h)
            mx = int(middle_tip.x * w)
            my = int(middle_tip.y * h)
            rx = int(ring_tip.x * w)
            ry = int(ring_tip.y * h)
            tx = int(thumb_tip.x * w)
            ty = int(thumb_tip.y * h)

            px = int(pinky_tip.x * w)
            py = int(pinky_tip.y * h)

            volume_distance = np.hypot(px - tx, py - ty)


            distance = np.hypot(mx - x, my - y)
            right_distance = np.hypot(rx - mx, ry - my)
            drag_distance = np.hypot(tx - x, ty - y)
            index_up = index_tip.y < index_pip.y
            middle_up = middle_tip.y < middle_pip.y
            if index_up and middle_up:

                if not scroll_mode:
                    scroll_mode = True
                    scroll_y = y

            else:
                scroll_mode = False


            if scroll_mode:
                gesture = "SCROLL"

                diff = scroll_y - y

                if abs(diff) > 20:

                    pyautogui.scroll(int(diff))

                    scroll_y = y

           # -----------------------
            # Left Click
            # -----------------------

            if distance < 30:

                if pinch_start == 0:
                    gesture = "LEFT CLICK"
                    pinch_start = time.time()

                if not clicked:
                    pyautogui.click()
                    clicked = True

                # Hold for Double Click
                if time.time() - pinch_start > 0.7 and not double_clicked:
                    gesture = "DOUBLE CLICK"
                    pyautogui.doubleClick()
                    double_clicked = True

            else:
             clicked = False
             double_clicked = False
             pinch_start = 0
            # -----------------------
            # Right Click
            # -----------------------

            if right_distance < 25 and not right_clicked:
                gesture = "RIGHT CLICK"
                pyautogui.rightClick()
                right_clicked = True

            elif right_distance > 35:
                right_clicked = False


                # -----------------------
            # Volume Control
            # -----------------------

            if volume_distance > 180:

                gesture = "VOLUME"

                volume_mode = True

                vol = np.interp(
                    volume_distance,
                    [180, 350],
                    [minVol, maxVol]
                )

                volume.SetMasterVolumeLevel(vol, None)

            else:
                volume_mode = False

            cv2.line(
                frame,
                (tx, ty),
                (px, py),
                (0,255,0),
                3
            )

            vol_bar = np.interp(
                volume_distance,
                [180,350],
                [400,150]
            )

            cv2.rectangle(frame,(560,150),(590,400),(255,255,255),2)

            cv2.rectangle(
                frame,
                (560,int(vol_bar)),
                (590,400),
                (0,255,0),
                cv2.FILLED
            )

            vol_percent = int(np.interp(
                volume_distance,
                [180,350],
                [0,100]
            ))

            cv2.putText(
                frame,
                f"{vol_percent}%",
                (545,430),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0,255,0),
                2
            )
           

            # -----------------------
            # Drag & Drop
            # Thumb + Index Pinch
            # -----------------------

            if drag_distance < 25:

                if drag_start == 0:
                    drag_start = time.time()

                if time.time() - drag_start > 0.3 and not dragging:
                    gesture = "DRAG"
                    pyautogui.mouseDown()
                    dragging = True


            elif drag_distance > 60:

                drag_start = 0

                if dragging:
                    gesture = "RELEASE"
                    pyautogui.mouseUp()
                    dragging = False


            screen_x = np.interp(x, (0, w), (0, screen_w))
            screen_y = np.interp(y, (0, h), (0, screen_h))

            current_x = prev_x + (screen_x - prev_x) / smoothening
            current_y = prev_y + (screen_y - prev_y) / smoothening
            if not scroll_mode:
                pyautogui.moveTo(current_x, current_y)
            prev_x = current_x
            prev_y = current_y

            # Draw Circle
            cv2.circle(
                frame,
                (x, y),
                12,
                (0, 0, 255),
                cv2.FILLED
            )

            cv2.circle(
            frame,
            (mx, my),
            12,
            (255, 0, 255),
            cv2.FILLED
            )
            cv2.circle(
                frame,
                (rx, ry),
                12,
                (255, 255, 0),
                cv2.FILLED
            )

            cv2.circle(
            frame,
            (tx, ty),
            12,
            (255, 255, 255),
            cv2.FILLED
            )

            # Show Coordinates
            cv2.putText(
                frame,
                f"X:{x}  Y:{y}",
                (20, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 0),
                2
            )

            cv2.putText(
            frame,
            f"Clicked: {clicked}",
            (400, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            3
            )

            cv2.putText(
            frame,
            f"Drag : {dragging}",
            (20,180),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0,255,255),
            2
            )

            cv2.putText(
                frame,
                f"Double : {double_clicked}",
                (20,300),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255,0,255),
                2
            )

            cv2.putText(
                frame,
                f"Right Dist : {int(right_distance)}",
                (20, 220),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 255),
                2
            )

            cv2.putText(
            frame,
            f"Drag Dist : {int(drag_distance)}",
            (20,260),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255,255,255),
            2
            )
            
            cv2.putText(
            frame,
            f"Scroll : {scroll_mode}",
            (20,340),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0,255,0),
            2
            )

            cv2.putText(
                frame,
                f"Gesture : {gesture}",
                (20,380),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0,255,255),
                2
            )

            


           
            # -------------------------------
            # Count Fingers
            # -------------------------------

            # Thumb
            if hand.landmark[4].x > hand.landmark[3].x:
                count += 1

            # Other 4 Fingers
            for tip in tips[1:]:

                if hand.landmark[tip].y < hand.landmark[tip - 2].y:
                    count += 1

    # -------------------------------
    # Display Finger Count
    # -------------------------------
    cv2.putText(
        frame,
        f"Fingers: {count}",
        (20, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )

    cv2.imshow("Finger Counter", frame)

    # Press Q to Quit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()