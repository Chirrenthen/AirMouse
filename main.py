"""
Virtual Mouse — Hand Gesture Controller
OS     : Windows 11
Python : 3.12
Deps   : mediapipe>=0.10.13  opencv-python  pynput  numpy

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GESTURE MAP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
☝  Index only              → Move mouse
✌  Index+Middle open       → Click-ready
✌  Index+Middle pinch      → Left click
👌 Thumb+Index pinch       → Right click
🤘 Index+Pinky (horns)     → Scroll UP   (fixed, tap gesture)
🤙 Thumb+Pinky             → Scroll DOWN (fixed, tap gesture)
✊ Fist                    → PAUSE (failsafe)
🖐  All 5 fingers           → PAUSE (failsafe)
👋 Wave (wrist L→R→L)      → Double click
🤞 Index+Middle crossed     → Drag lock toggle
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import cv2
import numpy as np
import HandTrackingModule as htm
import time
import ctypes
from pynput.mouse import Button, Controller

# ── Config ────────────────────────────────────────────────────────────────────
wCam, hCam    = 640, 480
frameR        = 60            # smaller margin = more reach incl. taskbar
smoothening   = 5
CLICK_DIST    = 38
SCROLL_AMOUNT = 3             # scroll clicks per gesture trigger
WAVE_THRESH   = 50
WAVE_TIMEOUT  = 0.7
DRAG_DIST     = 35            # pinch dist to activate drag

# ── Screen (DPI-aware) ────────────────────────────────────────────────────────
user32 = ctypes.windll.user32
user32.SetProcessDPIAware()
wScr   = user32.GetSystemMetrics(0)
hScr   = user32.GetSystemMetrics(1)

# ── Init ──────────────────────────────────────────────────────────────────────
mouse    = Controller()
cap      = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  wCam)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, hCam)
cap.set(cv2.CAP_PROP_FPS, 30)
detector = htm.handDetector(maxHands=1, detectionCon=0.78, trackCon=0.65)

pTime           = 0
plocX, plocY    = 0, 0
clocX, clocY    = 0, 0
click_cooldown  = 0
scroll_cooldown = 0           # prevents scroll spam

# Wave state
wave_stage      = 0
wave_last_x     = None
wave_timer      = 0.0

# Drag state
drag_active     = False

# Status
status_text     = "Ready"
status_color    = (0, 255, 120)

print(f"[INFO] Screen: {wScr}x{hScr} | Cam: {wCam}x{hCam} | Q to quit")

# ── Gesture helpers ───────────────────────────────────────────────────────────

def is_fist(fingers):
    return fingers == [0, 0, 0, 0, 0]

def is_open_palm(fingers):
    return fingers == [1, 1, 1, 1, 1]

def is_move(fingers):
    # Index only — middle, ring, pinky down
    return fingers[1] == 1 and fingers[2] == 0 and fingers[3] == 0 and fingers[4] == 0

def is_left_click_mode(fingers):
    return fingers[1] == 1 and fingers[2] == 1 and fingers[3] == 0 and fingers[4] == 0

def is_right_click_mode(fingers):
    return fingers[0] == 1 and fingers[1] == 1 and fingers[2] == 0 and fingers[3] == 0 and fingers[4] == 0

def is_scroll_up(fingers):
    # Horns: index + pinky up, middle + ring down — \\m/
    return fingers[1] == 1 and fingers[4] == 1 and fingers[2] == 0 and fingers[3] == 0

def is_scroll_down(fingers):
    # Thumb + pinky up, others down
    return fingers[0] == 1 and fingers[4] == 1 and fingers[1] == 0 and fingers[2] == 0 and fingers[3] == 0

def is_drag_gesture(fingers):
    # Middle + index crossed/together — all three top fingers up
    return fingers[1] == 1 and fingers[2] == 1 and fingers[3] == 1 and fingers[4] == 0

def detect_wave(wrist_x, now):
    global wave_stage, wave_last_x, wave_timer
    if wrist_x is None:
        return False
    if wave_last_x is None:
        wave_last_x = wrist_x
        return False

    delta = wrist_x - wave_last_x

    if now - wave_timer > WAVE_TIMEOUT:
        wave_stage = 0

    if wave_stage == 0 and delta > WAVE_THRESH:
        wave_stage = 1
        wave_timer = now
    elif wave_stage == 1 and delta < -WAVE_THRESH:
        wave_stage = 2
        wave_timer = now
    elif wave_stage == 2 and delta > WAVE_THRESH:
        wave_stage = 0
        wave_last_x = wrist_x
        return True

    wave_last_x = wrist_x
    return False

# ── UI draw ───────────────────────────────────────────────────────────────────

def draw_ui(img, status, color, fps, drag_on):
    # Bottom legend bar
    overlay = img.copy()
    cv2.rectangle(overlay, (0, hCam-88), (wCam, hCam), (15,15,15), -1)
    cv2.addWeighted(overlay, 0.6, img, 0.4, 0, img)

    lines = [
        "☝ Move  ✌ L-Click(pinch)  👌 R-Click(pinch)  ✊/🖐 PAUSE",
        "🤘 Scroll UP  🤙 Scroll DOWN  👋 Wave=DblClick  ✋ Drag",
    ]
    for i, txt in enumerate(lines):
        cv2.putText(img, txt, (6, hCam-66+i*26),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (160,160,160), 1, cv2.LINE_AA)

    # Top bar
    overlay2 = img.copy()
    cv2.rectangle(overlay2, (0,0), (wCam, 48), (15,15,15), -1)
    cv2.addWeighted(overlay2, 0.6, img, 0.4, 0, img)

    cv2.putText(img, f"MODE: {status}", (10, 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.72, color, 2, cv2.LINE_AA)
    cv2.putText(img, f"FPS {int(fps)}", (wCam-85, 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.60, (80,220,80), 2, cv2.LINE_AA)

    if drag_on:
        cv2.putText(img, "DRAG ON", (wCam//2-45, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0,200,255), 2, cv2.LINE_AA)

    # Active zone — mapped to FULL screen including taskbar
    cv2.rectangle(img, (frameR, frameR), (wCam-frameR, hCam-frameR), (60,60,180), 1)

# ── Main loop ─────────────────────────────────────────────────────────────────
while True:
    success, img = cap.read()
    if not success:
        print("[ERROR] Camera read failed. Try VideoCapture(1)")
        break

    img      = cv2.flip(img, 1)
    img      = detector.findHands(img, draw=True)
    lmList, _ = detector.findPosition(img, draw=False)
    now      = time.time()

    if not detector.handPresent() or not lmList:
        status_text  = "No Hand"
        status_color = (90, 90, 90)
        # Release drag if hand lost
        if drag_active:
            mouse.release(Button.left)
            drag_active = False

    else:
        fingers  = detector.fingersUp(mirrored=True)
        wrist_x  = detector.getWristX()

        # ── FAILSAFE ──────────────────────────────────────────────────────
        if is_fist(fingers) or is_open_palm(fingers):
            if drag_active:
                mouse.release(Button.left)
                drag_active  = False
            status_text  = "PAUSED"
            status_color = (0, 80, 220)

        # ── WAVE → double click ───────────────────────────────────────────
        elif detect_wave(wrist_x, now) and click_cooldown == 0:
            mouse.click(Button.left, 2)
            click_cooldown = 25
            status_text    = "DOUBLE CLICK"
            status_color   = (255, 220, 0)

        # ── SCROLL UP: horns \\m/ ─────────────────────────────────────────
        elif is_scroll_up(fingers):
            if scroll_cooldown == 0:
                mouse.scroll(0, SCROLL_AMOUNT)
                scroll_cooldown = 12          # ~12 frames between scroll ticks
            status_text  = "SCROLL UP  🤘"
            status_color = (0, 240, 180)
            cv2.putText(img, "▲▲▲", (wCam//2-30, hCam//2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0,240,180), 3, cv2.LINE_AA)

        # ── SCROLL DOWN: thumb+pinky ──────────────────────────────────────
        elif is_scroll_down(fingers):
            if scroll_cooldown == 0:
                mouse.scroll(0, -SCROLL_AMOUNT)
                scroll_cooldown = 12
            status_text  = "SCROLL DOWN  🤙"
            status_color = (0, 180, 255)
            cv2.putText(img, "▼▼▼", (wCam//2-30, hCam//2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0,180,255), 3, cv2.LINE_AA)

        # ── DRAG: index+middle+ring up ────────────────────────────────────
        elif is_drag_gesture(fingers):
            x1, y1 = lmList[8][1], lmList[8][2]
            x3 = np.interp(x1, (frameR, wCam-frameR), (0, wScr))
            y3 = np.interp(y1, (frameR, hCam-frameR), (0, hScr))
            clocX = plocX + (x3-plocX) / smoothening
            clocY = plocY + (y3-plocY) / smoothening
            mouse.position = (int(clocX), int(clocY))

            length, img, _ = detector.findDistance(8, 12, img, draw=False)
            if length < DRAG_DIST and not drag_active:
                mouse.press(Button.left)
                drag_active = True
            elif length >= DRAG_DIST and drag_active:
                mouse.release(Button.left)
                drag_active = False

            plocX, plocY = clocX, clocY
            status_text  = "DRAG"
            status_color = (255, 140, 0)
            cv2.circle(img, (x1,y1), 14, (255,140,0), cv2.FILLED)

        else:
            # Release drag if leaving drag gesture
            if drag_active:
                mouse.release(Button.left)
                drag_active = False

            # ── MOVE ──────────────────────────────────────────────────────
            if is_move(fingers):
                x1, y1 = lmList[8][1], lmList[8][2]
                # Map full camera zone → full screen (0,0) to (wScr, hScr)
                # including taskbar — no clipping
                x3    = np.interp(x1, (frameR, wCam-frameR), (0, wScr))
                y3    = np.interp(y1, (frameR, hCam-frameR), (0, hScr))
                clocX = plocX + (x3-plocX) / smoothening
                clocY = plocY + (y3-plocY) / smoothening
                # Clamp to allow reaching every pixel including taskbar
                clocX = max(0, min(clocX, wScr-1))
                clocY = max(0, min(clocY, hScr-1))
                mouse.position = (int(clocX), int(clocY))
                cv2.circle(img, (x1,y1), 12, (80,255,180), cv2.FILLED)
                plocX, plocY = clocX, clocY
                status_text  = "MOVE"
                status_color = (80, 255, 180)

            # ── LEFT CLICK ────────────────────────────────────────────────
            if is_left_click_mode(fingers):
                length, img, lineInfo = detector.findDistance(8, 12, img)
                if length < CLICK_DIST and click_cooldown == 0:
                    cv2.circle(img, (lineInfo[4], lineInfo[5]), 14, (0,255,80), cv2.FILLED)
                    mouse.click(Button.left, 1)
                    click_cooldown = 18
                    status_text    = "LEFT CLICK"
                    status_color   = (0, 255, 80)
                else:
                    status_text  = "CLICK READY"
                    status_color = (0, 200, 255)

            # ── RIGHT CLICK ───────────────────────────────────────────────
            elif is_right_click_mode(fingers):
                length, img, lineInfo = detector.findDistance(4, 8, img)
                if length < CLICK_DIST and click_cooldown == 0:
                    cv2.circle(img, (lineInfo[4], lineInfo[5]), 14, (0,120,255), cv2.FILLED)
                    mouse.click(Button.right, 1)
                    click_cooldown = 18
                    status_text    = "RIGHT CLICK"
                    status_color   = (0, 120, 255)

        # Cooldowns
        if click_cooldown  > 0: click_cooldown  -= 1
        if scroll_cooldown > 0: scroll_cooldown -= 1

    # ── FPS + draw UI ─────────────────────────────────────────────────────────
    cTime = time.time()
    fps   = 1 / (cTime - pTime) if pTime else 0
    pTime = cTime

    draw_ui(img, status_text, status_color, fps, drag_active)
    cv2.imshow("Virtual Mouse  |  Q to quit", img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        if drag_active:
            mouse.release(Button.left)
        break

cap.release()
cv2.destroyAllWindows()
print("[INFO] Exited cleanly.")