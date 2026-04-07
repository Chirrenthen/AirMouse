# AirMouse
Control your PC with hand gestures — no mouse needed.
Control your mouse entirely with hand gestures using your webcam. Built with MediaPipe, OpenCV, and pynput.

---

## 🤌 Gesture Map

| Gesture | Hand Shape | Action |
|---|---|---|
| ☝️ **Move** | Index finger only | Move mouse pointer |
| ✌️ **Click Ready** | Index + Middle open | Prepares for click |
| ✌️ **Left Click** | Index + Middle pinch together | Left click |
| 👌 **Right Click** | Thumb + Index pinch | Right click |
| 🤘 **Scroll Up** | Index + Pinky up (horns) | Scroll up |
| 🤙 **Scroll Down** | Thumb + Pinky up (shaka) | Scroll down |
| ✋ **Drag** | Index + Middle + Ring up, pinch to lock | Click and drag |
| 👋 **Double Click** | Wave wrist left → right → left | Double click |
| ✊ **Pause** | Fist (all fingers down) | Freeze mouse control |
| 🖐️ **Pause** | Open palm (all fingers up) | Freeze mouse control |

> **Tip:** Keep your hand inside the purple rectangle shown on the camera feed — that zone maps to your full screen.

---

## 🖥️ Requirements

- Windows 11
- Python 3.10 – 3.12 (**not 3.13**)
- Webcam (built-in or USB)
- Internet connection (first run downloads the MediaPipe model ~5 MB)

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/Chirrenthen/AirMouse.git
cd AirMouse
```

### 2. Create a virtual environment

Open **Command Prompt** (`cmd`, not PowerShell):

```cmd
python -m venv venv
venv\Scripts\activate.bat
```

### 3. Install dependencies

```cmd
pip install mediapipe opencv-python pynput numpy
```

> On first run, `hand_landmarker.task` (~5 MB) is automatically downloaded to your project folder from Google's servers.

---

## ▶️ Usage

```cmd
venv\Scripts\activate.bat
python main.py
```

A window will open showing your webcam feed with the hand skeleton overlay. Use the gestures from the table above to control your mouse.

Press **`Q`** to quit cleanly.

---

## 🛠️ Troubleshooting

**Camera doesn't open**

Change the camera index in `main.py`:
```python
cap = cv2.VideoCapture(1)  # try 1 or 2
```

**`mediapipe` won't install**

Ensure you are using Python 3.10–3.12. Python 3.13 is not supported by MediaPipe yet:
```cmd
python --version
```

**Mouse coordinates are off on a HiDPI screen**

The code calls `SetProcessDPIAware()` automatically. If issues persist, check your Windows display scaling setting (Settings → Display → Scale).

**PowerShell blocks venv activation**

Use `cmd` instead, or run this once in PowerShell as Administrator:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Scroll is too fast or too slow**

Adjust `SCROLL_AMOUNT` and the scroll cooldown (frames between ticks) in `main.py`:
```python
SCROLL_AMOUNT = 3       # reduce for slower scroll
# scroll_cooldown = 12  # increase for longer pause between ticks
```
