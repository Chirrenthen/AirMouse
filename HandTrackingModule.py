"""
Hand Tracking Module
Compatible: mediapipe >= 0.10.13 (Tasks API, no mp.solutions)
"""

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
import math
import urllib.request
import os

MODEL_PATH = "hand_landmarker.task"
if not os.path.exists(MODEL_PATH):
    print("Downloading hand landmarker model (~5MB)...")
    urllib.request.urlretrieve(
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
        MODEL_PATH
    )
    print("Model downloaded.")

HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (5,9),(9,10),(10,11),(11,12),
    (9,13),(13,14),(14,15),(15,16),
    (13,17),(17,18),(18,19),(19,20),
    (0,17)
]

FINGER_TIP_IDS = [4, 8, 12, 16, 20]


class handDetector():
    def __init__(self, maxHands=1, detectionCon=0.78, trackCon=0.65):
        self.lmList     = []
        self.tipIds     = FINGER_TIP_IDS
        self._result    = None
        self.handedness = []

        base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=maxHands,
            min_hand_detection_confidence=detectionCon,
            min_hand_presence_confidence=detectionCon,
            min_tracking_confidence=trackCon,
            running_mode=vision.RunningMode.IMAGE
        )
        self.detector = vision.HandLandmarker.create_from_options(options)

    def findHands(self, img, draw=True):
        img_rgb  = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
        self._result = self.detector.detect(mp_image)

        self.handedness = []
        if self._result.handedness:
            for h in self._result.handedness:
                self.handedness.append(h[0].category_name)

        if draw and self._result.hand_landmarks:
            h, w, _ = img.shape
            for hand_landmarks in self._result.hand_landmarks:
                pts = [(int(lm.x * w), int(lm.y * h)) for lm in hand_landmarks]
                for a, b in HAND_CONNECTIONS:
                    cv2.line(img, pts[a], pts[b], (0, 210, 90), 2)
                for pt in pts:
                    cv2.circle(img, pt, 4, (255, 60, 220), cv2.FILLED)
        return img

    def findPosition(self, img, handNo=0, draw=False):
        self.lmList = []
        bbox        = []
        if not self._result or not self._result.hand_landmarks:
            return self.lmList, bbox
        if handNo >= len(self._result.hand_landmarks):
            return self.lmList, bbox

        h, w, _ = img.shape
        hand     = self._result.hand_landmarks[handNo]
        xList, yList = [], []

        for id, lm in enumerate(hand):
            cx, cy = int(lm.x * w), int(lm.y * h)
            xList.append(cx)
            yList.append(cy)
            self.lmList.append([id, cx, cy])

        xmin, xmax = min(xList), max(xList)
        ymin, ymax = min(yList), max(yList)
        bbox = xmin, ymin, xmax, ymax

        if draw:
            cv2.rectangle(img, (xmin-20, ymin-20), (xmax+20, ymax+20), (0,255,0), 2)

        return self.lmList, bbox

    def fingersUp(self, mirrored=True):
        if not self.lmList:
            return [0, 0, 0, 0, 0]

        fingers   = []
        is_right  = (len(self.handedness) > 0 and self.handedness[0] == "Right")
        thumb_tip = self.lmList[self.tipIds[0]][1]
        thumb_ip  = self.lmList[self.tipIds[0]-1][1]

        if mirrored:
            fingers.append(1 if (is_right and thumb_tip < thumb_ip) or
                                (not is_right and thumb_tip > thumb_ip) else 0)
        else:
            fingers.append(1 if (is_right and thumb_tip > thumb_ip) or
                                (not is_right and thumb_tip < thumb_ip) else 0)

        for id in range(1, 5):
            tip_y = self.lmList[self.tipIds[id]][2]
            pip_y = self.lmList[self.tipIds[id]-2][2]
            fingers.append(1 if tip_y < pip_y else 0)

        return fingers

    def findDistance(self, p1, p2, img, draw=True, r=12, t=2):
        if not self.lmList or p1 >= len(self.lmList) or p2 >= len(self.lmList):
            return 999, img, [0, 0, 0, 0, 0, 0]

        x1, y1 = self.lmList[p1][1], self.lmList[p1][2]
        x2, y2 = self.lmList[p2][1], self.lmList[p2][2]
        cx, cy = (x1+x2)//2, (y1+y2)//2

        if draw:
            cv2.line(img, (x1,y1), (x2,y2), (255,0,255), t)
            cv2.circle(img, (x1,y1), r, (255,0,255), cv2.FILLED)
            cv2.circle(img, (x2,y2), r, (255,0,255), cv2.FILLED)
            cv2.circle(img, (cx,cy), r, (0,0,255), cv2.FILLED)

        return math.hypot(x2-x1, y2-y1), img, [x1, y1, x2, y2, cx, cy]

    def handPresent(self):
        return bool(self._result and self._result.hand_landmarks)

    def getLandmark(self, id):
        if not self.lmList or id >= len(self.lmList):
            return None
        return self.lmList[id][1], self.lmList[id][2]

    def getWristX(self):
        pt = self.getLandmark(0)
        return pt[0] if pt else None