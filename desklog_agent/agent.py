import argparse
import os
import sys
import time
import json
import platform
import threading
from datetime import datetime

import requests
import psutil
from mss import mss
from PIL import Image

try:
    import win32gui  # type: ignore
except Exception:  # noqa: S110
    win32gui = None

try:
    import pyautogui  # type: ignore
except Exception:  # noqa: S110
    pyautogui = None


class DesklogClient:
    def __init__(self, server, db, username, password, verify_ssl=True):
        self.server = server.rstrip('/')
        self.db = db
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.token = None
        self.system = 'windows' if platform.system().lower().startswith('win') else 'linux'
        self.hostname = platform.node()

    def _json_rpc(self, path, params):
        url = f"{self.server}{path}"
        headers = {'Content-Type': 'application/json'}
        response = self.session.post(url, headers=headers, data=json.dumps(params), verify=self.verify_ssl, timeout=20)
        response.raise_for_status()
        return response.json()

    def login(self):
        # Authenticate to get session for /json endpoints
        url = f"{self.server}/web/session/authenticate"
        payload = {
            'jsonrpc': '2.0',
            'method': 'call',
            'params': {
                'db': self.db,
                'login': self.username,
                'password': self.password,
            },
        }
        res = self.session.post(url, json=payload, timeout=20, verify=self.verify_ssl)
        res.raise_for_status()
        result = res.json()
        if 'error' in result:
            raise RuntimeError(f"Login failed: {result['error']}")
        return True

    def register(self):
        payload = {
            'jsonrpc': '2.0',
            'method': 'call',
            'params': {
                'system': self.system,
                'hostname': self.hostname,
            },
        }
        result = self._json_rpc('/desklog/register', payload)['result']
        self.token = result['token']

    def ping(self):
        payload = {'jsonrpc': '2.0', 'method': 'call', 'params': {'token': self.token}}
        self._json_rpc('/desklog/ping', payload)

    def get_config(self):
        payload = {'jsonrpc': '2.0', 'method': 'call', 'params': {'token': self.token}}
        result = self._json_rpc('/desklog/config', payload)['result']
        return result

    def post_activity(self, entries):
        payload = {'jsonrpc': '2.0', 'method': 'call', 'params': {'token': self.token, 'entries': entries}}
        self._json_rpc('/desklog/activity', payload)

    def upload_screenshot(self, image_bytes, mime, width, height):
        url = f"{self.server}/desklog/screenshot"
        files = {
            'image': ('screenshot', image_bytes, mime),
        }
        data = {
            'token': self.token,
            'width': str(width),
            'height': str(height),
            'mime': mime,
        }
        res = self.session.post(url, files=files, data=data, timeout=30, verify=self.verify_ssl)
        res.raise_for_status()


def get_active_window_title():
    try:
        if win32gui:
            hwnd = win32gui.GetForegroundWindow()
            return win32gui.GetWindowText(hwnd)
        if pyautogui:
            # On Linux, PyAutoGUI can get active window title via getActiveWindow
            win = pyautogui.getActiveWindow()
            return win.title if win else ''
    except Exception:
        return ''
    return ''


def capture_screenshot(quality=80, fmt='JPEG'):
    with mss() as sct:
        img = sct.grab(sct.monitors[0])
        img_pil = Image.frombytes('RGB', img.size, img.rgb)
        width, height = img_pil.size
        buf = None
        from io import BytesIO
        bio = BytesIO()
        if fmt.upper() == 'PNG':
            img_pil.save(bio, format='PNG')
            mime = 'image/png'
        else:
            img_pil.save(bio, format='JPEG', quality=quality, optimize=True)
            mime = 'image/jpeg'
        data = bio.getvalue()
        return data, mime, width, height


def compute_activity(idle_threshold):
    # Simple heuristic: idle if no user input for threshold seconds
    try:
        if sys.platform.startswith('win'):
            # Windows-specific idle time detection could use GetLastInputInfo via pywin32
            # TODO: implement robust idle detection; fallback below
            pass
        # Fallback using CPU activity of user processes
        user_active = any(p.info['cpu_percent'] > 0.5 for p in psutil.process_iter(['cpu_percent']))
        if user_active:
            return 'active', 0
        else:
            return 'idle', idle_threshold
    except Exception:
        return 'active', 0


class Runner:
    def __init__(self, client: DesklogClient, screenshot_every: int, quality: int, idle_threshold: int):
        self.client = client
        self.screenshot_every = max(60, screenshot_every)
        self.quality = quality
        self.idle_threshold = idle_threshold
        self.stop_event = threading.Event()

    def loop(self):
        last_screenshot = 0
        self.client.login()
        self.client.register()
        config = self.client.get_config()
        self.screenshot_every = int(config.get('screenshot_interval', self.screenshot_every))
        self.quality = int(config.get('screenshot_quality', self.quality))
        self.idle_threshold = int(config.get('idle_threshold', self.idle_threshold))

        while not self.stop_event.is_set():
            now = time.time()
            # Build and send a single activity entry
            activity_type, idle_seconds = compute_activity(self.idle_threshold)
            entry = {
                'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                'app_name': platform.system(),
                'window_title': get_active_window_title(),
                'idle_seconds': idle_seconds,
                'activity_type': activity_type,
            }
            try:
                self.client.post_activity([entry])
                self.client.ping()
            except Exception as e:
                print('Activity upload error:', e)

            if now - last_screenshot >= self.screenshot_every:
                try:
                    data, mime, w, h = capture_screenshot(quality=self.quality, fmt='JPEG')
                    self.client.upload_screenshot(data, mime, w, h)
                except Exception as e:
                    print('Screenshot upload error:', e)
                last_screenshot = now

            time.sleep(10)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', required=True)
    parser.add_argument('--db', required=True)
    parser.add_argument('-u', '--username', default=os.getenv('DESKLOG_USER'))
    parser.add_argument('-p', '--password', default=os.getenv('DESKLOG_PASS'))
    parser.add_argument('--no-verify-ssl', action='store_true')
    args = parser.parse_args()

    if not args.username or not args.password:
        print('Username and password required (flags or DESKLOG_USER/DESKLOG_PASS)')
        sys.exit(2)

    client = DesklogClient(args.server, args.db, args.username, args.password, verify_ssl=not args.no_verify_ssl)
    runner = Runner(client, screenshot_every=300, quality=80, idle_threshold=300)
    runner.loop()


if __name__ == '__main__':
    main()
