from flask import Flask, render_template, request, jsonify, send_from_directory
from threading import Thread, Lock, Event
from pynput import mouse, keyboard
from pynput.keyboard import Key, Controller as KeyboardController, KeyCode
from pynput.mouse import Button, Controller as MouseController
import json
import time
import subprocess
import ctypes
from ctypes import cast, POINTER, wintypes
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import win32api
import win32con
import win32gui
import win32com.client
import pythoncom
import mouse
import webbrowser
import math
import winreg
import os
import sys
from datetime import datetime, timedelta
from PIL import Image, ImageDraw
import pystray
import tempfile
import win32ui
import threading
import psutil
import tkinter as tk
from tkinter import filedialog

# Windows constants
WM_APPCOMMAND = 0x319
APPCOMMAND_VOLUME_UP = 0x0a
APPCOMMAND_VOLUME_DOWN = 0x09
APPCOMMAND_MEDIA_PLAY_PAUSE = 0x0E
APPCOMMAND_MEDIA_NEXTTRACK = 0x0B
APPCOMMAND_MEDIA_PREVIOUSTRACK = 0x0C

app = Flask(__name__)

# Default hotkeys
default_hotkeys = {
    "volume_up": {
        "keyboard": "ctrl",
        "mouse": "scrollup"
    },
    "volume_down": {
        "keyboard": "ctrl",
        "mouse": "scrolldown"
    },
    "toggle_sound_volume": {
        "keyboard": "ctrl+alt+m",
        "mouse": "None"
    },
    "prev_device": {
        "keyboard": "win+pageup",
        "mouse": "None"
    },
    "next_device": {
        "keyboard": "win+pagedown",
        "mouse": "None"
    },
    "prev_input_device": {
        "keyboard": "win+home",
        "mouse": "None"
    },
    "next_input_device": {
        "keyboard": "win+end",
        "mouse": "None"
    },
    "toggle_mic_volume": {
        "keyboard": "ctrl+m",
        "mouse": "None"
    },
    "media_play_pause": {
        "keyboard": "ctrl+space",
        "mouse": "None"
    },
    "media_next": {
        "keyboard": "ctrl+right",
        "mouse": "None"
    },
    "media_previous": {
        "keyboard": "ctrl+left",
        "mouse": "None"
    }
}

# Добавляем константы для позиций уведомлений
NOTIFICATION_POSITIONS = {
    "top_right": "Top Right",
    "top_left": "Top Left", 
    "bottom_left": "Bottom Left",
    "bottom_right": "Bottom Right",
    "center": "Center"
}

class KeyboardMouseTracker:
    def __init__(self):
        self.pressed_buttons = set()
        self.pressed_keyboard_keys = set()
        self.scroll_direction = None
        self.lock = Lock()
        self.stop_event = Event()
        
        self._left_pressed = False
        self._right_pressed = False
        self._middle_pressed = False
        
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        
        mouse.hook(self._on_mouse_event)
        
        self.state_cache = None
        self.last_state_update = 0
        self.state_cache_lifetime = 0.008
    
    def _on_mouse_event(self, event):
        try:
            if hasattr(event, 'delta'):
                with self.lock:
                    if event.delta > 0:
                        self.scroll_direction = 'scrollup'
                        Thread(target=self._reset_scroll, daemon=True).start()
                    elif event.delta < 0:
                        self.scroll_direction = 'scrolldown'
                        Thread(target=self._reset_scroll, daemon=True).start()
                return
            
            if getattr(event, 'event_type', None) == 'move':
                return

        except Exception as e:
            print(f"Error in mouse event handler: {e}")

    def _on_key_press(self, key):
        try:
            key_str = None
            
            # Обработка об��чных клавиш
            if isinstance(key, keyboard.KeyCode):
                # Маппинг виртуальных кодов на английские буквы
                vk_to_eng = {
                    65: 'a', 66: 'b', 67: 'c', 68: 'd', 69: 'e',
                    70: 'f', 71: 'g', 72: 'h', 73: 'i', 74: 'j',
                    75: 'k', 76: 'l', 77: 'm', 78: 'n', 79: 'o',
                    80: 'p', 81: 'q', 82: 'r', 83: 's', 84: 't',
                    85: 'u', 86: 'v', 87: 'w', 88: 'x', 89: 'y', 90: 'z'
                }
                
                if hasattr(key, 'vk') and key.vk in vk_to_eng:
                    key_str = vk_to_eng[key.vk]
                elif hasattr(key, 'vk') and key.vk:
                    # Маппинг для специальных клавиш
                    key_str = {
                        191: '/', 220: '\\', 188: ',', 190: '.',
                        186: ';', 222: "'", 219: '[', 221: ']',
                        189: '-', 187: '=', 192: '`',
                        48: '0', 49: '1', 50: '2', 51: '3', 52: '4',
                        53: '5', 54: '6', 55: '7', 56: '8', 57: '9'
                    }.get(key.vk)
            
            # Обработка специальных клавиш
            if isinstance(key, keyboard.Key):
                key_str = str(key).replace('Key.', '').lower()
                # Нормализация имен клавиш
                key_str = {
                    'ctrl_l': 'ctrl', 'ctrl_r': 'ctrl',
                    'alt_l': 'alt', 'alt_r': 'alt',
                    'shift_l': 'shift', 'shift_r': 'shift',
                    'cmd': 'win', 'cmd_l': 'win', 'cmd_r': 'win',
                    'return': 'enter',
                    'space': 'space'
                }.get(key_str, key_str)
            
            # Если ключ не определен, используем строковое представление
            if not key_str:
                key_str = str(key).lower().replace('key.', '')
            
            key_str = normalize_key_name(key_str)
            
            with self.lock:
                self.pressed_keyboard_keys.add(key_str)
                
        except Exception as e:
            print(f"Error in key press handler: {e}")

    def _on_key_release(self, key):
        try:
            key_str = None
            
            # Обработк������ обычных клавиш
            if isinstance(key, keyboard.KeyCode):
                # Маппинг виртуальных кодов на английские буквы
                vk_to_eng = {
                    65: 'a', 66: 'b', 67: 'c', 68: 'd', 69: 'e',
                    70: 'f', 71: 'g', 72: 'h', 73: 'i', 74: 'j',
                    75: 'k', 76: 'l', 77: 'm', 78: 'n', 79: 'o',
                    80: 'p', 81: 'q', 82: 'r', 83: 's', 84: 't',
                    85: 'u', 86: 'v', 87: 'w', 88: 'x', 89: 'y', 90: 'z'
                }
                
                if hasattr(key, 'vk') and key.vk in vk_to_eng:
                    key_str = vk_to_eng[key.vk]
                elif hasattr(key, 'vk') and key.vk:
                    # Маппинг для специальных клавиш
                    key_str = {
                        191: '/', 220: '\\', 188: ',', 190: '.',
                        186: ';', 222: "'", 219: '[', 221: ']',
                        189: '-', 187: '=', 192: '`',
                        48: '0', 49: '1', 50: '2', 51: '3', 52: '4',
                        53: '5', 54: '6', 55: '7', 56: '8', 57: '9'
                    }.get(key.vk)
            
            # Обработка специальных клавиш
            if isinstance(key, keyboard.Key):
                key_str = str(key).replace('Key.', '').lower()
                # Нормализация имен клавиш
                key_str = {
                    'ctrl_l': 'ctrl', 'ctrl_r': 'ctrl',
                    'alt_l': 'alt', 'alt_r': 'alt',
                    'shift_l': 'shift', 'shift_r': 'shift',
                    'cmd': 'win', 'cmd_l': 'win', 'cmd_r': 'win',
                    'return': 'enter',
                    'space': 'space'
                }.get(key_str, key_str)
            
            # Если ключ не определен, используем строковое представление
            if not key_str:
                key_str = str(key).lower().replace('key.', '')
            
            key_str = normalize_key_name(key_str)
            
            with self.lock:
                self.pressed_keyboard_keys.discard(key_str)
                
        except Exception as e:
            print(f"Error in key release handler: {e}")

    def _track_mouse_buttons(self):
        while not self.stop_event.is_set():
            try:
                time.sleep(0.008)
                
                left = win32api.GetKeyState(win32con.VK_LBUTTON) < 0
                right = win32api.GetKeyState(win32con.VK_RBUTTON) < 0
                middle = win32api.GetKeyState(win32con.VK_MBUTTON) < 0

                with self.lock:
                    changed = False
                    
                    if left != self._left_pressed:
                        if left:
                            self.pressed_buttons.add('mouseleft')
                        else:
                            self.pressed_buttons.discard('mouseleft')
                        self._left_pressed = left
                        changed = True

                    if right != self._right_pressed:
                        if right:
                            self.pressed_buttons.add('mouseright')
                        else:
                            self.pressed_buttons.discard('mouseright')
                        self._right_pressed = right
                        changed = True

                    if middle != self._middle_pressed:
                        if middle:
                            self.pressed_buttons.add('mousemiddle')
                        else:
                            self.pressed_buttons.discard('mousemiddle')
                        self._middle_pressed = middle
                        changed = True
                    
                    if changed:
                        self.state_cache = None

            except Exception as e:
                print(f"Error tracking mouse buttons: {e}")
                time.sleep(0.1)

    def _reset_scroll(self):
        time.sleep(0.2)
        with self.lock:
            self.scroll_direction = None

    def start(self):
        self.keyboard_listener.start()
        self.mouse_thread = Thread(target=self._track_mouse_buttons, daemon=True)
        self.mouse_thread.start()

    def stop(self):
        self.stop_event.set()
        self.keyboard_listener.stop()
        mouse.unhook_all()
        if hasattr(self, 'mouse_thread'):
            self.mouse_thread.join(timeout=1.0)

    def get_state(self):
        current_time = time.time()
        
        if self.state_cache and (current_time - self.last_state_update) < self.state_cache_lifetime:
            return self.state_cache
            
        with self.lock:
            self.state_cache = {
                'keyboard': self.pressed_keyboard_keys.copy(),
                'mouse': {
                    'buttons': self.pressed_buttons.copy(),
                    'scroll': self.scroll_direction
                }
            }
            self.last_state_update = current_time
            return self.state_cache

def normalize_key_name(key_str):
    """Нормализует названия клавиш"""
    key_mapping = {
        # Special keys
        'arrowup': 'up',
        'arrowdown': 'down',
        'arrowleft': 'left',
        'arrowright': 'right',
        'page_up': 'pageup',
        'page_down': 'pagedown',
        'none': '',
        'space': 'space',
        # Arrows
        'up': 'up',
        'down': 'down',
        'left': 'left',
        'right': 'right',
        # Modifiers
        'ctrl_l': 'ctrl',
        'ctrl_r': 'ctrl',
        'alt_l': 'alt',
        'alt_r': 'alt',
        'shift_l': 'shift',
        'shift_r': 'shift',
        'cmd': 'win',
        'cmd_r': 'win',
        # Mouse
        'mouseleft': 'mouseleft',
        'mouseright': 'mouseright',
        'mousemiddle': 'mousemiddle',
        'scrollup': 'scrollup',
        'scrolldown': 'scrolldown',
        'lmb': 'mouseleft',
        'rmb': 'mouseright',
        'mmb': 'mousemiddle',
        # Special characters
        '/': '/',
        '\\': '\\',
        ',': ',',
        '.': '.',
        ';': ';',
        "'": "'",
        '[': '[',
        ']': ']',
        '-': '-',
        '=': '=',
        '`': '`',
        # Fix for control characters
        '\x01': 'a',  # Ctrl+A
        '\x02': 'b',  # Ctrl+B
        '\x03': 'c',  # Ctrl+C
        '\x04': 'd',  # Ctrl+D
        '\x05': 'e',  # Ctrl+E
        '\x06': 'f',  # Ctrl+F
        '\x07': 'g',  # Ctrl+G
        '\x08': 'h',  # Ctrl+H
        '\x09': 'i',  # Ctrl+I (Tab)
        '\x0A': 'j',  # Ctrl+J
        '\x0B': 'k',  # Ctrl+K
        '\x0C': 'l',  # Ctrl+L
        '\x0D': 'm',  # Ctrl+M (Enter)
        '\x0E': 'n',  # Ctrl+N
        '\x0F': 'o',  # Ctrl+O
        '\x10': 'p',  # Ctrl+P
        '\x11': 'q',  # Ctrl+Q
        '\x12': 'r',  # Ctrl+R
        '\x13': 's',  # Ctrl+S
        '\x14': 't',  # Ctrl+T
        '\x15': 'u',  # Ctrl+U
        '\x16': 'v',  # Ctrl+V
        '\x17': 'w',  # Ctrl+W
        '\x18': 'x',  # Ctrl+X
        '\x19': 'y',  # Ctrl+Y
        '\x1A': 'z',  # Ctrl+Z
        '\r': 'm',    # Enter key
        '\n': 'n',    # Newline
        '\t': 'tab',  # Tab key
        # Letters and numbers
        'a': 'a', 'b': 'b', 'c': 'c', 'd': 'd', 'e': 'e',
        'f': 'f', 'g': 'g', 'h': 'h', 'i': 'i', 'j': 'j',
        'k': 'k', 'l': 'l', 'm': 'm', 'n': 'n', 'o': 'o',
        'p': 'p', 'q': 'q', 'r': 'r', 's': 's', 't': 't',
        'u': 'u', 'v': 'v', 'w': 'w', 'x': 'x', 'y': 'y',
        'z': 'z',
        '0': '0', '1': '1', '2': '2', '3': '3', '4': '4',
        '5': '5', '6': '6', '7': '7', '8': '8', '9': '9',
    }
    
    # Remove 'key.' prefix if it exists
    if key_str.lower().startswith('key.'):
        key_str = key_str[4:]
    
    # Convert to lowercase for consistency
    key_str = key_str.lower()
    
    # Check if key is in mapping
    return key_mapping.get(key_str, key_str)

def handle_hotkeys(tracker):
    """Обработчик горячих клавиш"""
    global profile_manager
    last_action_time = {}
    
    while True:
        try:
            time.sleep(0.008)
            state = tracker.get_state()
            current_time = time.time()
            
            # Проверяем горячие клавиши профилей
            for profile in profile_manager.profiles:
                if not profile.get('hotkey') or not profile['hotkey'].get('keyboard'):
                    continue
                    
                profile_combo = {
                    'keyboard': profile['hotkey'].get('keyboard', 'None'),
                    'mouse': profile['hotkey'].get('mouse', 'None')
                }
                
                if current_time - last_action_time.get(f'profile_{profile["name"]}', 0) < 0.1:
                    continue
                    
                if check_hotkey_combination(profile_combo, state):
                    print(f"Activating profile {profile['name']} by hotkey")
                    activate_profile(profile['name'])
                    last_action_time[f'profile_{profile["name"]}'] = current_time
                    continue
            
            # Проверяем остальные горячие клавиши
            for action, combo in hotkeys.items():
                if current_time - last_action_time.get(action, 0) < 0.1:
                    continue
                
                if combo['keyboard'].lower() == 'none' and combo['mouse'].lower() == 'none':
                    continue
                    
                if check_hotkey_combination(combo, state):
                    if action == 'volume_up':
                        send_volume_message(APPCOMMAND_VOLUME_UP)
                    elif action == 'volume_down':
                        send_volume_message(APPCOMMAND_VOLUME_DOWN)
                    elif action == 'toggle_sound_volume':
                        toggle_sound_volume()
                    elif action == 'prev_device':
                        switch_audio_device('prev')
                    elif action == 'next_device':
                        switch_audio_device('next')
                    elif action == 'prev_input_device':
                        switch_input_device('prev')
                    elif action == 'next_input_device':
                        switch_input_device('next')
                    elif action == 'toggle_mic_volume':
                        toggle_microphone_volume()
                    elif action == 'media_play_pause':
                        send_media_message(APPCOMMAND_MEDIA_PLAY_PAUSE)
                    elif action == 'media_next':
                        send_media_message(APPCOMMAND_MEDIA_NEXTTRACK)
                    elif action == 'media_previous':
                        send_media_message(APPCOMMAND_MEDIA_PREVIOUSTRACK)
                    
                    last_action_time[action] = current_time

        except Exception as e:
            print(f"Error in handle_hotkeys: {e}")
            time.sleep(0.1)

def check_hotkey_combination(hotkey, state):
    try:
        if (hotkey['keyboard'].lower() == 'none' and 
            hotkey['mouse'].lower() == 'none'):
            return False

        # Разделяем комбинации клавиш
        keyboard_keys = set()
        for k in hotkey['keyboard'].split('+'):
            k = k.strip().lower()
            if k and k != 'none':
                keyboard_keys.add(k)

        mouse_keys = set(m.strip().lower() for m in hotkey['mouse'].split('+') 
                        if m.strip() and m.strip().lower() != 'none')

        if not keyboard_keys and not mouse_keys:
            return False

        # Получаем текущие нажатые клавиши
        current_keys = state['keyboard']

        # Проверяем, что все необходимые клавиши нажаты
        keyboard_match = True
        if keyboard_keys:
            # Проверяем, что количество нажатых клавиш совпадает
            if len(keyboard_keys) != len(current_keys):
                return False
            
            # Проверяем, что все необходимые клавиши нажаты
            keyboard_match = all(key in current_keys for key in keyboard_keys)
            if not keyboard_match:
                return False

        mouse_match = True
        if mouse_keys:
            for mouse_key in mouse_keys:
                if mouse_key in ['scrollup', 'scrolldown']:
                    mouse_match = mouse_match and state['mouse']['scroll'] == mouse_key
                else:
                    mouse_match = mouse_match and mouse_key in state['mouse']['buttons']
            if not mouse_match:
                return False

        return True

    except Exception as e:
        print(f"Error in check_hotkey_combination: {e}")
        return False

def send_volume_message(app_command):
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    ctypes.windll.user32.SendMessageW(hwnd, WM_APPCOMMAND, 0, app_command * 0x10000)

def send_media_message(app_command):
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    ctypes.windll.user32.SendMessageW(hwnd, WM_APPCOMMAND, 0, app_command * 0x10000)

def get_audio_devices():
    """Получает список устройств вывода звука"""
    devices = []
    
    # 1. Основной метод через PowerShell
    try:
        powershell_path = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
        
        ps_script = """
        if (-not (Get-Module -ListAvailable -Name AudioDeviceCmdlets)) {
            Write-Host "ERROR: AudioDeviceCmdlets not installed"
            exit 1
        }
        
        try {
            $OutputEncoding = [Console]::OutputEncoding = [Text.Encoding]::UTF8
            $devices = Get-AudioDevice -List | Where-Object { $_.Type -eq 'Playback' }
            $devices | ForEach-Object {
                Write-Output ("DEVICE:{0}|{1}" -f $_.Index, $_.Name)
            }
        } catch {
            Write-Host "Error getting output device list: $_"
        }
        """
        
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        result = subprocess.run(
            [powershell_path, "-Command", ps_script],
            capture_output=True,
            text=True,
            encoding='utf-8',
            creationflags=subprocess.CREATE_NO_WINDOW,
            startupinfo=startupinfo
        )
        
        for line in result.stdout.split('\n'):
            if line.strip().startswith('DEVICE:'):
                try:
                    _, device_info = line.strip().split('DEVICE:', 1)
                    index, name = device_info.split('|', 1)
                    devices.append([index.strip(), name.strip()])
                except ValueError:
                    continue
                    
        if devices:
            return devices
    except Exception as e:
        print(f"PowerShell method failed: {e}")

    # 2. Резервный метод через pycaw
    if not devices:
        try:
            pythoncom.CoInitialize()
            try:
                deviceEnumerator = AudioUtilities.GetAllDevices()
                index = 0
                for device in deviceEnumerator:
                    if device.state == 1 and device.flow == 0:  # DEVICE_STATE_ACTIVE = 1, eRender = 0
                        devices.append([str(index), device.FriendlyName])
                        index += 1
            finally:
                pythoncom.CoUninitialize()
                
            if devices:
                print("Using pycaw method for device enumeration")
                return devices
        except Exception as e:
            print(f"Pycaw method failed: {e}")

    # 3. Резервный метод через MMDevice API в PowerShell
    if not devices:
        try:
            ps_script = """
            Add-Type -TypeDefinition @"
            using System.Runtime.InteropServices;
            [Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
            interface IMMDevice {
                int Activate([MarshalAs(UnmanagedType.LPStruct)] Guid iid, int dwClsCtx, IntPtr pActivationParams, [MarshalAs(UnmanagedType.IUnknown)] out object ppInterface);
            }
            [Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
            interface IMMDeviceEnumerator {
                int EnumAudioEndpoints(int dataFlow, int dwStateMask, out IMMDeviceCollection ppDevices);
            }
            [Guid("0BD7A1BE-7A1A-44DB-8397-CC5392387B5E"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
            interface IMMDeviceCollection {
                int GetCount(out int pcDevices);
                int Item(int nDevice, out IMMDevice ppDevice);
            }
"@
            
            $deviceEnumerator = New-Object -ComObject "MMDeviceEnumerator.MMDeviceEnumerator"
            $devices = @()
            $deviceCollection = $deviceEnumerator.EnumAudioEndpoints(0, 1)  # eRender = 0, DEVICE_STATE_ACTIVE = 1
            
            for ($i = 0; $i -lt $deviceCollection.Count; $i++) {
                $device = $deviceCollection.Item($i)
                $properties = $device.Properties
                $name = $properties.GetValue("{a45c254e-df1c-4efd-8020-67d146a850e0},2").ToString()
                Write-Output ("DEVICE:{0}|{1}" -f $i, $name)
            }
            """
            
            result = subprocess.run(
                [powershell_path, "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                text=True,
                encoding='utf-8',
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
            
            for line in result.stdout.split('\n'):
                if line.strip().startswith('DEVICE:'):
                    try:
                        _, device_info = line.strip().split('DEVICE:', 1)
                        index, name = device_info.split('|', 1)
                        devices.append([index.strip(), name.strip()])
                    except ValueError:
                        continue
                        
            if devices:
                print("Using MMDevice API method for device enumeration")
                return devices
        except Exception as e:
            print(f"MMDevice API method failed: {e}")

    print("All methods failed to get audio devices")
    return []

def set_default_audio_device(device_index):
    """Устанавливает устройство вывода по умолчанию"""
    ps_script = f"""
    try {{
        $device = Get-AudioDevice -List | Where-Object {{ $_.Index -eq {device_index} }}
        if ($device) {{
            Write-Host "Setting default device: $($device.Name)"
            Set-AudioDevice -ID $device.ID
        }} else {{
            Write-Host "Device with index {device_index} not found"
        }}
    }} catch {{
        Write-Host "Error setting default device: $_"
    }}
    """
    
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        result = subprocess.run(
            [r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe", "-Command", ps_script],
            capture_output=True,
            text=True,
            encoding='cp866',
            creationflags=subprocess.CREATE_NO_WINDOW,
            startupinfo=startupinfo
        )
        print(f"PowerShell output: {result.stdout}")
        if result.stderr:
            print(f"PowerShell error: {result.stderr}")
    except Exception as e:
        print(f"Error executing PowerShell: {e}")

def set_default_communication_device(device_index):
    """Устанавливает устройство вывода для связи по умолчанию"""
    ps_script = f"""
    try {{
        $device = Get-AudioDevice -List | Where-Object {{ $_.Index -eq {device_index} }}
        if ($device) {{
            Write-Host "Setting communication device: $($device.Name)"
            Set-AudioDevice -ID $device.ID -Communication
        }} else {{
            Write-Host "Device with index {device_index} not found"
        }}
    }} catch {{
        Write-Host "Error setting communication device: $_"
    }}
    """
    
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        result = subprocess.run(
            [r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe", "-Command", ps_script],
            capture_output=True,
            text=True,
            encoding='cp866',
            creationflags=subprocess.CREATE_NO_WINDOW,
            startupinfo=startupinfo
        )
        print(f"PowerShell output: {result.stdout}")
        if result.stderr:
            print(f"PowerShell error: {result.stderr}")
    except Exception as e:
        print(f"Error executing PowerShell: {e}")

def set_default_input_device(device_index):
    """Устаналивает устройство ввода по умолчанию"""
    ps_script = f"""
    try {{
        $device = Get-AudioDevice -List | Where-Object {{ $_.Index -eq {device_index} }}
        if ($device) {{
            Write-Host "Setting default input device: $($device.Name)"
            Set-AudioDevice -ID $device.ID
        }} else {{
            Write-Host "Device with index {device_index} not found"
        }}
    }} catch {{
        Write-Host "Error setting default input device: $_"
    }}
    """
    
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        result = subprocess.run(
            [r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe", "-Command", ps_script],
            capture_output=True,
            text=True,
            encoding='cp866',
            creationflags=subprocess.CREATE_NO_WINDOW,
            startupinfo=startupinfo
        )
        print(f"PowerShell output: {result.stdout}")
        if result.stderr:
            print(f"PowerShell error: {result.stderr}")
    except Exception as e:
        print(f"Error executing PowerShell: {e}")

def set_default_input_communication_device(device_index):
    """Утанавливает устройство ввода для связи по умолчанию"""
    ps_script = f"""
    try {{
        $device = Get-AudioDevice -List | Where-Object {{ $_.Index -eq {device_index} }}
        if ($device) {{
            Write-Host "Setting communication input device: $($device.Name)"
            Set-AudioDevice -ID $device.ID -Communication
        }} else {{
            Write-Host "Device with index {device_index} not found"
        }}
    }} catch {{
        Write-Host "Error setting communication input device: $_"
    }}
    """
    
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        result = subprocess.run(
            [r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe", "-Command", ps_script],
            capture_output=True,
            text=True,
            encoding='cp866',
            creationflags=subprocess.CREATE_NO_WINDOW,
            startupinfo=startupinfo
        )
        print(f"PowerShell output: {result.stdout}")
        if result.stderr:
            print(f"PowerShell error: {result.stderr}")
    except Exception as e:
        print(f"Error executing PowerShell: {e}")

def create_notification_icon(icon_type='speaker', size=64):
    """Создает красивую иконку для уведомлений"""
    # Создаем изображение большего размера для лучшего сглаживания
    large_size = size * 4
    image = Image.new('RGBA', (large_size, large_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    scale = large_size / 128

    # Рисуем градиентный круг с правильным расчетом координат
    gradient_steps = 20
    step_size = large_size / (2 * gradient_steps)
    for i in range(gradient_steps):
        alpha = int(255 * (1 - i/gradient_steps))
        color = (0, 123, 255, alpha)
        x0 = i * step_size
        y0 = i * step_size
        x1 = large_size - (i * step_size)
        y1 = large_size - (i * step_size)
        draw.ellipse([x0, y0, x1, y1], fill=color)

    if icon_type == 'speaker':
        # Рисуем динамик (белый)
        speaker_color = (255, 255, 255, 255)
        
        # Прямоугольник динамика
        draw.rectangle([
            int(35 * scale), int(44 * scale), 
            int(55 * scale), int(84 * scale)
        ], fill=speaker_color)
        
        # Треугольник динамика
        points = [
            (int(55 * scale), int(44 * scale)),
            (int(85 * scale), int(24 * scale)),
            (int(85 * scale), int(104 * scale)),
            (int(55 * scale), int(84 * scale))
        ]
        draw.polygon(points, fill=speaker_color)
        
        # Звуковые волны с улучшенным сглаживанием
        wave_color = (255, 255, 255, 200)
        for i in range(3):
            offset = i * 15
            # Увеличиваем толщину линии для лучшего сглаживания
            draw.arc(
                [int((70 + offset) * scale), int((34 + offset) * scale),
                int((100 + offset) * scale), int((94 + offset) * scale)],
                300, 60, fill=wave_color, width=int(6 * scale)
            )

    elif icon_type == 'microphone':
        mic_color = (255, 255, 255, 255)
        
        # Основной корпус микрофона (более округлый)
        draw.rounded_rectangle([
            int(52 * scale), int(24 * scale),
            int(76 * scale), int(64 * scale)
        ], radius=int(12 * scale), fill=mic_color)
        
        # Нижняя чась микрофона (подставка)
        base_width = int(40 * scale)
        base_height = int(4 * scale)
        base_x = int(64 * scale - base_width/2)
        base_y = int(84 * scale)
        
        # Ножка микрофона
        stand_width = int(4 * scale)
        stand_x = int(64 * scale - stand_width/2)
        stand_y1 = int(64 * scale)
        stand_y2 = base_y
        
        # Рисуем ножку с градиентом
        steps = 20  # Увеличиваем количество шагов для плавности
        for i in range(steps):
            alpha = int(255 * (1 - i/steps * 0.3))
            current_color = (255, 255, 255, alpha)
            current_y = stand_y1 + (stand_y2 - stand_y1) * i/steps
            draw.rectangle([
                stand_x, current_y,
                stand_x + stand_width, current_y + (stand_y2 - stand_y1)/steps
            ], fill=current_color)
        
        # Рисуем подставку с градиентом
        for i in range(steps):
            alpha = int(255 * (1 - i/steps * 0.3))
            current_color = (255, 255, 255, alpha)
            current_width = base_width * (1 - i/steps * 0.2)
            current_x = int(64 * scale - current_width/2)
            current_y = base_y + i * base_height/steps
            draw.rounded_rectangle([
                current_x, current_y,
                current_x + current_width, current_y + base_height/steps
            ], radius=int(2 * scale), fill=current_color)
        
        # Добавляем блики на корпусе
        highlight_color = (255, 255, 255, 30)
        draw.ellipse([
            int(54 * scale), int(26 * scale),
            int(62 * scale), int(34 * scale)
        ], fill=highlight_color)
        
        # Добавляем звуковые волны с улучшенным сглаживание
        wave_color = (255, 255, 255, 100)
        for i in range(3):
            offset = i * 8
            # Увелчиваем толщин линии для лучшего сглаживания
            draw.arc([
                int((44 - offset) * scale), int((34 - offset) * scale),
                int((84 + offset) * scale), int((54 + offset) * scale)
            ], 220, 320, fill=wave_color, width=int(4 * scale))

    # Уменьшаем изображение до нужного азеа с использованием всококачественного ресемплинга
    image = image.resize((size, size), Image.Resampling.LANCZOS)
    return image

class NotificationWindow:
    def __init__(self):
        self.notifications = []
        self.WINDOW_CLASS = "SoundDeviceControlNotification"
        
        # Цвета для темно темы
        self.DARK_THEME = {
            'bg': win32api.RGB(44, 44, 44),      # Темно-серый фон
            'text': win32api.RGB(255, 255, 255),  # Белый текст
            'accent': win32api.RGB(74, 158, 255)  # Голубой акцент
        }
        
        # Цвета для светлой темы
        self.LIGHT_THEME = {
            'bg': win32api.RGB(240, 240, 240),    # Светло-серый фон
            'text': win32api.RGB(0, 0, 0),        # Черный текст
            'accent': win32api.RGB(0, 120, 215)   # Синий кцент
        }
        
        # По умолчанию темная тема
        self.current_theme = self.DARK_THEME

        # Регистрируем класс окна
        wc = win32gui.WNDCLASS()
        wc.lpszClassName = self.WINDOW_CLASS
        wc.lpfnWndProc = self._window_proc
        wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        wc.hbrBackground = win32gui.GetStockObject(win32con.BLACK_BRUSH)
        wc.hInstance = win32api.GetModuleHandle(None)
        
        try:
            win32gui.RegisterClass(wc)
        except Exception as e:
            print(f"Failed to register window class: {e}")

        self.notification_position = self.load_notification_position()

    def _window_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _create_rounded_region(self, hwnd, width, height, radius):
        """Сздает регио окна со скругленными углами"""
        try:
            region = win32gui.CreateRoundRectRgn(0, 0, width, height, radius, radius)
            win32gui.SetWindowRgn(hwnd, region, True)
        except Exception as e:
            print(f"Error creating rounded region: {e}")

    def set_theme(self, is_light):
        """Устанавливает тему уведомлений"""
        print(f"Setting theme to {'light' if is_light else 'dark'}")  # Отладочный вывод
        self.current_theme = self.LIGHT_THEME if is_light else self.DARK_THEME

    def show_notification(self, text, icon_type='speaker'):
        def _show():
            try:
                # Создаем окно уведомления
                width = 300
                height = 80
                screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
                screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
                
                # Получем координаты в зависимости от выбранной позиции
                x, y = self.get_notification_position(width, height, screen_width, screen_height)

                # Добавляем WS_EX_TOPMOST к стилям окна
                hwnd = win32gui.CreateWindowEx(
                    win32con.WS_EX_TOOLWINDOW | win32con.WS_EX_TOPMOST,  # Добавляем WS_EX_TOPMOST
                    self.WINDOW_CLASS,
                    "Notification",
                    win32con.WS_POPUP | win32con.WS_VISIBLE,
                    x, y, width, height,
                    0, 0, win32api.GetModuleHandle(None), None
                )

                # Создаем скруленный регион для окна
                region = win32gui.CreateRoundRectRgn(0, 0, width, height, 15, 15)
                win32gui.SetWindowRgn(hwnd, region, True)

                # Устанавливаем окно поверх всех окон
                win32gui.SetWindowPos(
                    hwnd, 
                    win32con.HWND_TOPMOST,
                    x, y, width, height,
                    win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW
                )

                # Создаем DC для рисования
                hdc = win32gui.GetDC(hwnd)
                memdc = win32gui.CreateCompatibleDC(hdc)
                bitmap = win32gui.CreateCompatibleBitmap(hdc, width, height)
                win32gui.SelectObject(memdc, bitmap)

                # Заливаем фон
                brush = win32gui.CreateSolidBrush(self.current_theme['bg'])
                win32gui.FillRect(memdc, (0, 0, width, height), brush)
                win32gui.DeleteObject(brush)

                # Создаем иконку
                icon_image = create_notification_icon(icon_type, size=32)
                
                # Сохраняем как ICO
                icon_path = os.path.join(tempfile.gettempdir(), f'notification_icon_{icon_type}.ico')
                # Конвертируем в ICO формат
                icon_image.save(icon_path, format='ICO', sizes=[(32, 32)])
                
                # Загружаем иконку
                icon = win32gui.LoadImage(
                    0, icon_path, win32con.IMAGE_ICON,
                    32, 32, win32con.LR_LOADFROMFILE
                )
                
                # Рисуем иконку
                win32gui.DrawIconEx(
                    memdc, 15, 24,
                    icon, 32, 32,
                    0, None, win32con.DI_NORMAL
                )
                
                # Удаляем иконку
                win32gui.DestroyIcon(icon)
                
                try:
                    os.remove(icon_path)
                except:
                    pass

                # Рисуем текст
                lf = win32gui.LOGFONT()
                lf.lfFaceName = 'Segoe UI'
                lf.lfHeight = 15
                lf.lfWeight = win32con.FW_NORMAL
                lf.lfQuality = win32con.DEFAULT_QUALITY
                font = win32gui.CreateFontIndirect(lf)

                win32gui.SelectObject(memdc, font)
                win32gui.SetTextColor(memdc, self.current_theme['text'])
                win32gui.SetBkMode(memdc, win32con.TRANSPARENT)
                rect = (60, 0, width - 10, height)
                win32gui.DrawText(memdc, text, -1, rect, 
                                win32con.DT_LEFT | win32con.DT_VCENTER | win32con.DT_SINGLELINE)

                # Копируем из памяти на экран напрямую
                win32gui.BitBlt(hdc, 0, 0, width, height, memdc, 0, 0, win32con.SRCCOPY)

                # Очищаем ресурсы
                win32gui.DeleteObject(bitmap)
                win32gui.DeleteDC(memdc)
                win32gui.ReleaseDC(hwnd, hdc)

                # Ждем перед закрытием
                time.sleep(2)
                
                win32gui.DestroyWindow(hwnd)

            except Exception as e:
                print(f"Error showing notification: {e}")
                import traceback
                print(traceback.format_exc())

        Thread(target=_show, daemon=True).start()

    def load_notification_position(self):
        try:
            with open('notification_settings.json', 'r') as f:
                settings = json.load(f)
                return settings.get('position', 'bottom_right')
        except FileNotFoundError:
            return 'bottom_right'

    def save_notification_position(self, position):
        try:
            with open('notification_settings.json', 'w') as f:
                json.dump({'position': position}, f)
        except Exception as e:
            print(f"Error saving notification position: {e}")

    def get_notification_position(self, width, height, screen_width, screen_height):
        padding = 20
        bottom_padding = 70  # Увеличенный отступ снизу для нижних позиций (было 50, стало 70)
        
        positions = {
            'top_right': (screen_width - width - padding, padding),
            'top_left': (padding, padding),
            'bottom_left': (padding, screen_height - height - bottom_padding),
            'bottom_right': (screen_width - width - padding, screen_height - height - bottom_padding),
            'center': (screen_width//2 - width//2, screen_height//2 - height//2)
        }
        
        return positions.get(self.notification_position, positions['bottom_right'])

# Создаем глобальный объект для уведомлений
notification_window = NotificationWindow()

# Заменяем все вызовы show_notification на:
def show_notification(message, icon_type='speaker'):
    notification_window.show_notification(message, icon_type)

# Удаляем старый код создания окна уведомлений
# def create_notification_window():
#     ...

# В функции main() заменяем запуск старого notification_thread на:
# notification_thread = Thread(target=create_notification_window, daemon=True)
# notification_thread.start()

# Добавляем глобальную переменную для хранения активных устройств
enabled_devices = set()

def load_enabled_devices():
    """Загружает список активнх устройств из файла"""
    global enabled_devices
    try:
        with open('enabled_devices.json', 'r') as f:
            enabled_devices = set(json.load(f))
    except FileNotFoundError:
        # Если файл не существует, все устройства активны по умолчанию
        enabled_devices = set(device[0] for device in devices)
        save_enabled_devices()

def save_enabled_devices():
    """Сохраняет список актвых устройств в файл"""
    try:
        with open('enabled_devices.json', 'w') as f:
            json.dump(list(enabled_devices), f)
    except Exception as e:
        print(f"Error saving enabled devices: {e}")

@app.route("/set_device_enabled", methods=["POST"])
def set_device_enabled():
    """Включает/выключает утройство в списке активных"""
    try:
        data = request.json
        device_index = data.get("device_index")
        enabled = data.get("enabled", True)
        
        if enabled:
            enabled_devices.add(device_index)
        else:
            enabled_devices.discard(device_index)
        
        save_enabled_devices()
        
        return jsonify({
            "status": "success"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })

def switch_audio_device(direction):
    """Переключает устройство вывода звука"""
    global current_device_index, devices, enabled_devices
    try:
        if not devices:
            devices = get_audio_devices()
            if not devices:
                return
        
        if not enabled_devices:
            enabled_devices.update(device[0] for device in devices)
            save_enabled_devices()
            
        active_devices = [device for device in devices if device[0] in enabled_devices]
        
        if not active_devices:
            return
            
        if current_device_index >= len(devices) or current_device_index < 0:
            current_device_index = 0
            
        try:
            current_device = next((device for device in active_devices 
                                if device[0] == devices[current_device_index][0]), 
                                active_devices[0])
            
            current_active_index = active_devices.index(current_device)
            
            if direction == 'prev':
                next_active_index = (current_active_index - 1) % len(active_devices)
            else:
                next_active_index = (current_active_index + 1) % len(active_devices)
            
            next_device = active_devices[next_active_index]
            
            current_device_index = next(i for i, device in enumerate(devices) 
                                    if device[0] == next_device[0])
            
            set_default_audio_device(next_device[0])
            
            Thread(target=show_notification, args=(f"Switched to: {next_device[1]}",)).start()
            
        except Exception as e:
            if active_devices:
                current_device_index = next(i for i, device in enumerate(devices) 
                                        if device[0] == active_devices[0][0])
                set_default_audio_device(active_devices[0][0])
        
    except Exception as e:
        print(f"Error switching device: {e}")

def create_icon():
    width = 128
    height = 128
    image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    for i in range(40):
        alpha = int(255 * (1 - i/40))
        color = (0, 123, 255, alpha)
        draw.ellipse([i, i, width-i, height-i], fill=color)

    speaker_color = (255, 255, 255, 255)
    draw.rectangle([35, 44, 55, 84], fill=speaker_color)
    
    points_left = [(55, 44), (85, 24), (85, 104), (55, 84)]
    draw.polygon(points_left, fill=speaker_color)

    wave_color = (255, 255, 255, 200)
    draw.arc([70, 34, 100, 94], 300, 60, fill=wave_color, width=4)
    draw.arc([85, 24, 115, 104], 300, 60, fill=wave_color, width=4)

    bar_colors = [(0, 255, 255, 200), (0, 255, 200, 200), (0, 200, 255, 200)]
    bar_width = 4
    for i, color in enumerate(bar_colors):
        height = 20 + i * 10
        x = 95 + i * 8
        y = 64 - height//2
        draw.rectangle([x, y, x+bar_width, y+height], fill=color)

    return image

def open_settings(icon, item):
    webbrowser.open('http://127.0.0.1:5000')

def exit_app(icon, item):
    icon.stop()
    global running
    running = False

# Добавляем константу для отслеживания изменений устройств
WM_DEVICECHANGE = 0x0219

class SystemTray:
    def __init__(self):
        self.log("Initializing SystemTray...")
        
        # Создаем иконку
        try:
            icon_size = 64
            image = Image.new('RGBA', (icon_size, icon_size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)

            # Рисуем граиентный круг
            for i in range(20):
                alpha = int(255 * (1 - i/20))
                color = (0, 123, 255, alpha)
                draw.ellipse([i, i, icon_size-i, icon_size-i], fill=color)

            # Рисем динамик (елый)
            speaker_color = (255, 255, 255, 255)
            scale = icon_size / 128  # Масштабируем координаты
            
            # Прямоугольник динамика
            draw.rectangle([
                int(35 * scale), int(44 * scale), 
                int(55 * scale), int(84 * scale)
            ], fill=speaker_color)
            
            # Треугльник динамика
            points = [
                (int(55 * scale), int(44 * scale)),
                (int(85 * scale), int(24 * scale)),
                (int(85 * scale), int(104 * scale)),
                (int(55 * scale), int(84 * scale))
            ]
            draw.polygon(points, fill=speaker_color)

            # Звуковые волны
            wave_color = (255, 255, 255, 200)
            draw.arc([
                int(70 * scale), int(34 * scale),
                int(100 * scale), int(94 * scale)
            ], 300, 60, fill=wave_color, width=int(4 * scale))
            draw.arc([
                int(85 * scale), int(24 * scale),
                int(115 * scale), int(104 * scale)
            ], 300, 60, fill=wave_color, width=int(4 * scale))

            # Цветные полоски
            bar_colors = [(0, 255, 255, 200), (0, 255, 200, 200), (0, 200, 255, 200)]
            bar_width = int(4 * scale)
            for i, color in enumerate(bar_colors):
                height = int((20 + i * 10) * scale)
                x = int((95 + i * 8) * scale)
                y = int(64 * scale - height//2)
                draw.rectangle([x, y, x+bar_width, y+height], fill=color)

            # Создаем меню
            menu = (
                pystray.MenuItem("Settings", self._open_settings),
                pystray.MenuItem("Exit", self._exit_app)
            )

            # Создаем иконку в трее
            self.icon = pystray.Icon(
                "Sound Device Control App",
                image,
                "Sound Device Control App",
                menu
            )

            self.log("Tray icon created successfully")
            
        except Exception as e:
            self.log(f"Failed to create tray icon: {e}")
            raise

        self.running = True
        self.log("Initialization complete")

    def _open_settings(self, icon, item):
        try:
            self.log("Opening settings")
            webbrowser.open('http://127.0.0.1:5000')
        except Exception as e:
            self.log(f"Error opening settings: {e}")

    def _exit_app(self, icon, item):
        try:
            self.log("Exiting application")
            global running
            self.stop()
            running = False
        except Exception as e:
            self.log(f"Error exiting: {e}")

    def stop(self):
        try:
            if hasattr(self, 'icon'):
                self.icon.stop()
            self.log("Stopped")
        except Exception as e:
            self.log(f"Error stopping: {e}")

    def run(self):
        self.log("Starting tray icon")
        self.icon.run()

    def log(self, message):
        """Логирование событий трея"""
        print(f"{message}")

def setup_tray():
    """Sets up the system tray icon"""
    return SystemTray()

def exit_app(icon):
    global running
    running = False
    icon.stop()

@app.route("/")
def index():
    return render_template("index.html", hotkeys=hotkeys)

def save_settings(settings):
    """Сохраяет настройки в файл"""
    try:
        # Проверяем валидность JSON перед сохранением
        json.dumps(settings)
        
        with open('settings.json', 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False

def update_settings_structure(settings):
    """Обновляет структуру настроек, добавляя недостающие действия"""
    updated = False
    for action, combo in default_hotkeys.items():
        if action not in settings:
            settings[action] = combo.copy()
            updated = True
    return settings, updated

# Загрузк настроек при запуске
try:
    with open('settings.json', 'r', encoding='utf-8') as f:
        hotkeys = json.load(f)
    # Обновляем структуру если нужно
    hotkeys, was_updated = update_settings_structure(hotkeys)
    if was_updated:
        save_settings(hotkeys)
    print(f"Loaded hotkeys: {hotkeys}")
except FileNotFoundError:
    hotkeys = default_hotkeys.copy()
    save_settings(hotkeys)
    print(f"Using default hotkeys: {hotkeys}")
except json.JSONDecodeError:
    print("Error reading settings.json, using default hotkeys")
    hotkeys = default_hotkeys.copy()
    save_settings(hotkeys)

@app.route("/update_hotkey", methods=["POST"])
def update_hotkey():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data received"})
            
        action = data.get("action")
        if not action:
            return jsonify({"status": "error", "message": "No action specified"})
            
        keyboard_keys = data.get("keyboard", "None")
        mouse_keys = data.get("mouse", "None")
        
        print(f"Updating hotkey - Action: {action}, Keyboard: {keyboard_keys}, Mouse: {mouse_keys}")

        try:
            with open('settings.json', 'r', encoding='utf-8') as f:
                current_hotkeys = json.load(f)
        except FileNotFoundError:
            current_hotkeys = default_hotkeys.copy()
        except json.JSONDecodeError:
            current_hotkeys = default_hotkeys.copy()

        # Обновляем структуру если нужно
        current_hotkeys, _ = update_settings_structure(current_hotkeys)
        
        current_hotkeys[action] = {
            "keyboard": keyboard_keys,
            "mouse": mouse_keys
        }

        if save_settings(current_hotkeys):
            global hotkeys
            hotkeys = current_hotkeys
            return jsonify({"status": "success", "hotkeys": current_hotkeys})
        else:
            return jsonify({"status": "error", "message": "Error saving settings"})

    except Exception as e:
        print(f"Error in update_hotkey: {e}")
        import traceback
        print(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)})

def run_flask():
    app.run(host='127.0.0.1', port=5000, debug=False)

# Добавлем глобальные переменные для устройств ввода
enabled_input_devices = set()

def load_enabled_input_devices():
    """Загружает список активных устройств ввода из файла"""
    global enabled_input_devices
    try:
        with open('enabled_input_devices.json', 'r') as f:
            enabled_input_devices = set(json.load(f))
    except FileNotFoundError:
        # Еси файл не существует, все усройства активны по умолчанию
        enabled_input_devices = set(device[0] for device in input_devices)
        save_enabled_input_devices()

def save_enabled_input_devices():
    """Сохраняет список активных устройств ввода в файл"""
    try:
        with open('enabled_input_devices.json', 'w') as f:
            json.dump(list(enabled_input_devices), f)
    except Exception as e:
        print(f"Error saving enabled input devices: {e}")

@app.route("/get_input_devices")
def get_input_devices_route():
    """Вовращает спиок устройств ввода"""
    try:
        devices = get_input_devices()
        return jsonify({
            "status": "success",
            "devices": devices
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })

@app.route("/set_input_device_enabled", methods=["POST"])
def set_input_device_enabled():
    """Включает/выключает устройство ввода в списке активных"""
    try:
        data = request.json
        device_index = data.get("device_index")
        enabled = data.get("enabled", True)
        
        if enabled:
            enabled_input_devices.add(device_index)
        else:
            enabled_input_devices.discard(device_index)
        
        save_enabled_input_devices()
        
        return jsonify({
            "status": "success"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })

def get_input_devices():
    """Получает список устройств ввода звука"""
    devices = []
    
    # 1. Основной метод через PowerShell
    try:
        powershell_path = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
        
        ps_script = """
        if (-not (Get-Module -ListAvailable -Name AudioDeviceCmdlets)) {
            Write-Host "ERROR: AudioDeviceCmdlets not installed"
            exit 1
        }
        
        try {
            $OutputEncoding = [Console]::OutputEncoding = [Text.Encoding]::UTF8
            $devices = Get-AudioDevice -List | Where-Object { $_.Type -eq 'Recording' }
            $devices | ForEach-Object {
                Write-Output ("DEVICE:{0}|{1}" -f $_.Index, $_.Name)
            }
        } catch {
            Write-Host "Error getting input device list: $_"
        }
        """
        
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        result = subprocess.run(
            [powershell_path, "-Command", ps_script],
            capture_output=True,
            text=True,
            encoding='utf-8',
            creationflags=subprocess.CREATE_NO_WINDOW,
            startupinfo=startupinfo
        )
        
        for line in result.stdout.split('\n'):
            if line.strip().startswith('DEVICE:'):
                try:
                    _, device_info = line.strip().split('DEVICE:', 1)
                    index, name = device_info.split('|', 1)
                    devices.append([index.strip(), name.strip()])
                except ValueError:
                    continue
                    
        if devices:
            return devices
    except Exception as e:
        print(f"PowerShell method failed: {e}")

    # 2. Резервный метод через pycaw
    if not devices:
        try:
            pythoncom.CoInitialize()
            try:
                deviceEnumerator = AudioUtilities.GetAllDevices()
                index = 0
                for device in deviceEnumerator:
                    if device.state == 1 and device.flow == 1:  # DEVICE_STATE_ACTIVE = 1, eCapture = 1
                        devices.append([str(index), device.FriendlyName])
                        index += 1
            finally:
                pythoncom.CoUninitialize()
                
            if devices:
                print("Using pycaw method for input device enumeration")
                return devices
        except Exception as e:
            print(f"Pycaw method failed: {e}")

    # 3. Резервный метод через MMDevice API в PowerShell
    if not devices:
        try:
            ps_script = """
            Add-Type -TypeDefinition @"
            using System.Runtime.InteropServices;
            [Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
            interface IMMDevice {
                int Activate([MarshalAs(UnmanagedType.LPStruct)] Guid iid, int dwClsCtx, IntPtr pActivationParams, [MarshalAs(UnmanagedType.IUnknown)] out object ppInterface);
            }
            [Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
            interface IMMDeviceEnumerator {
                int EnumAudioEndpoints(int dataFlow, int dwStateMask, out IMMDeviceCollection ppDevices);
            }
            [Guid("0BD7A1BE-7A1A-44DB-8397-CC5392387B5E"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
            interface IMMDeviceCollection {
                int GetCount(out int pcDevices);
                int Item(int nDevice, out IMMDevice ppDevice);
            }
"@
            
            $deviceEnumerator = New-Object -ComObject "MMDeviceEnumerator.MMDeviceEnumerator"
            $devices = @()
            $deviceCollection = $deviceEnumerator.EnumAudioEndpoints(1, 1)  # eCapture = 1, DEVICE_STATE_ACTIVE = 1
            
            for ($i = 0; $i -lt $deviceCollection.Count; $i++) {
                $device = $deviceCollection.Item($i)
                $properties = $device.Properties
                $name = $properties.GetValue("{a45c254e-df1c-4efd-8020-67d146a850e0},2").ToString()
                Write-Output ("DEVICE:{0}|{1}" -f $i, $name)
            }
            """
            
            result = subprocess.run(
                [powershell_path, "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                text=True,
                encoding='utf-8',
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
            
            for line in result.stdout.split('\n'):
                if line.strip().startswith('DEVICE:'):
                    try:
                        _, device_info = line.strip().split('DEVICE:', 1)
                        index, name = device_info.split('|', 1)
                        devices.append([index.strip(), name.strip()])
                    except ValueError:
                        continue
                        
            if devices:
                print("Using MMDevice API method for input device enumeration")
                return devices
        except Exception as e:
            print(f"MMDevice API method failed: {e}")

    print("All methods failed to get input devices")
    return []

def switch_input_device(direction):
    """Переключает устройство ввода звука"""
    global current_input_device_index, input_devices, enabled_input_devices
    try:
        if not input_devices:
            input_devices = get_input_devices()
            if not input_devices:
                return
            
        active_devices = [device for device in input_devices if device[0] in enabled_input_devices]
        
        if not active_devices:
            return
            
        try:
            current_device = next((device for device in active_devices 
                                if device[0] == input_devices[current_input_device_index][0]), 
                                active_devices[0])
            
            current_active_index = active_devices.index(current_device)
            
            if direction == 'prev':
                next_active_index = (current_active_index - 1) % len(active_devices)
            else:
                next_active_index = (current_active_index + 1) % len(active_devices)
            
            next_device = active_devices[next_active_index]
            
            current_input_device_index = next(i for i, device in enumerate(input_devices) 
                                          if device[0] == next_device[0])
            
            set_default_input_device(next_device[0])
            
            show_notification(f"Input switched to: {next_device[1]}", 'microphone')
            
        except Exception as e:
            print(f"Error during input device switching: {e}")
        
    except Exception as e:
        print(f"Error switching input device: {e}")

def toggle_microphone_volume():
    """Переключает громкость микрофона между 0% и 100%"""
    try:
        pythoncom.CoInitialize()
        devices = AudioUtilities.GetMicrophone()
        
        if not devices:
            return

        interface = devices.Activate(
            IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        
        if volume.GetMute():
            volume.SetMute(0, None)
            volume.SetMasterVolumeLevelScalar(1.0, None)
            Thread(target=show_notification, args=("Microphone: ON", 'microphone')).start()
        else:
            volume.SetMute(1, None)
            volume.SetMasterVolumeLevelScalar(0.0, None)
            Thread(target=show_notification, args=("Microphone: OFF", 'microphone')).start()
    except:
        pass
    finally:
        pythoncom.CoUninitialize()

@app.route("/get_output_devices")
def get_output_devices():
    """Возвращает список устройсв вывоа звука"""
    try:
        devices = get_audio_devices()
        return jsonify({
            "status": "success",
            "devices": devices
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })

@app.route("/save_settings", methods=["POST"])
def save_settings_endpoint():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data received"})

        # Проверяем формат данных
        for action, combo in data.items():
            if not isinstance(combo, dict) or "keyboard" not in combo or "mouse" not in combo:
                return jsonify({
                    "status": "error",
                    "message": f"Invalid data format for action {action}"
                })

        # Обновляем структуру если нужно
        data, _ = update_settings_structure(data)

        # Сохраяем настройки
        if save_settings(data):
            global hotkeys
            hotkeys = data
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": "Error saving settings"})
    except Exception as e:
        print(f"Error in save_settings_endpoint: {e}")
        return jsonify({"status": "error", "message": str(e)})

# Добавляем глобальные переменные, если они были удалены
devices = []
current_device_index = 0
running = False

# Добавляем глобальные переменны для устройств ввода
input_devices = []
current_input_device_index = 0

@app.route("/get_enabled_devices")
def get_enabled_devices():
    """Возвращает список активных устройств вывода"""
    try:
        return jsonify({
            "status": "success",
            "enabled_devices": list(enabled_devices)
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })

@app.route("/get_enabled_input_devices")
def get_enabled_input_devices():
    """Возвращает список активных устройств ввода"""
    try:
        return jsonify({
            "status": "success",
            "enabled_devices": list(enabled_input_devices)
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })

def get_autostart_status():
    """Проверяет, добавлено ли приложение в автозагрузку"""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ
        )
        try:
            value, _ = winreg.QueryValueEx(key, "SoundDeviceControl")
            return True
        except WindowsError:
            return False
        finally:
            winreg.CloseKey(key)
    except WindowsError:
        return False

def set_autostart(enable):
    """Включает или выключает автозагрузку приложения"""
    key = None
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_ALL_ACCESS
        )

        if not enable:
            try:
                winreg.DeleteValue(key, "SoundDeviceControl")
                return True
            except WindowsError:
                return False
        else:
            app_path = sys.argv[0]
            if app_path.endswith('.py'):
                # Для Python скрипта
                python_path = sys.executable
                winreg.SetValueEx(
                    key,
                    "SoundDeviceControl",
                    0,
                    winreg.REG_SZ,
                    f'"{python_path}" "{os.path.abspath(app_path)}"'
                )
            else:
                # Для exe файла
                winreg.SetValueEx(
                    key,
                    "SoundDeviceControl",
                    0,
                    winreg.REG_SZ,
                    os.path.abspath(app_path)
                )
            return True
    except Exception as e:
        print(f"Error setting autostart: {e}")
        return False
    finally:
        if key:
            winreg.CloseKey(key)

@app.route("/get_autostart")
def get_autostart():
    """Возращает статус автозагрузки"""
    try:
        return jsonify({
            "status": "success",
            "autostart": get_autostart_status()
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })

@app.route("/set_autostart", methods=["POST"])
def set_autostart_route():
    """Устанавливает статус автозагрузки"""
    try:
        data = request.json
        enable = data.get("enable", False)
        
        success = set_autostart(enable)
        return jsonify({
            "status": "success" if success else "error"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })

@app.route("/set_theme", methods=["POST"])
def set_theme():
    try:
        data = request.json
        is_light = data.get("is_light", False)
        notification_window.set_theme(is_light)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })

@app.route("/get_notification_position")
def get_notification_position():
    """Возвращает текущую позицию уведомлений и список доступных позицй"""
    try:
        return jsonify({
            "status": "success",
            "current_position": notification_window.notification_position,
            "available_positions": NOTIFICATION_POSITIONS
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })

@app.route("/set_notification_position", methods=["POST"])
def set_notification_position():
    """Устанавливает новую позицию уедомлений"""
    try:
        data = request.json
        position = data.get("position")
        
        if position not in NOTIFICATION_POSITIONS:
            return jsonify({
                "status": "error",
                "message": "Invalid position"
            })
            
        notification_window.notification_position = position
        notification_window.save_notification_position(position)
        
        return jsonify({
            "status": "success"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })

# Добавляем глобальные переменные, если они были удалены
device_update_callbacks = []

def register_device_callback(callback):
    """Регистрирует функцию обратного вызова для обновления устройств"""
    device_update_callbacks.append(callback)

def notify_device_changes():
    """Уведомляет все зарегистрированные функции об изменении устройств"""
    global devices, input_devices
    devices = get_audio_devices()
    input_devices = get_input_devices()
    for callback in device_update_callbacks:
        try:
            callback()
        except Exception as e:
            print(f"Error in device update callback: {e}")

class DeviceChangeListener:
    def __init__(self):
        self.running = True
        self.last_check = 0
        self.check_interval = 1  # Интервал проверки в секундах
        
        # Создаем скрытое окно для получения сообщений Windows
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self._wnd_proc
        wc.lpszClassName = "DeviceChangeListener"
        wc.hInstance = win32api.GetModuleHandle(None)
        
        class_atom = win32gui.RegisterClass(wc)
        self.hwnd = win32gui.CreateWindow(
            class_atom,
            "DeviceChangeListener",
            0,
            0, 0, 0, 0,
            0,
            0,
            wc.hInstance,
            None
        )
        
        # Запускаем поток для периодической проверки
        self.check_thread = threading.Thread(target=self._check_devices, daemon=True)
        self.check_thread.start()

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_DEVICECHANGE:  # Используем константу WM_DEVICECHANGE
            notify_device_changes()
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _check_devices(self):
        """Периодически проверяет устройсва"""
        while self.running:
            current_time = time.time()
            if current_time - self.last_check >= self.check_interval:
                notify_device_changes()
                self.last_check = current_time
            time.sleep(0.5)

    def stop(self):
        self.running = False
        if self.hwnd:
            win32gui.DestroyWindow(self.hwnd)

# Добавляем класс для рботы с профилями
class DeviceProfile:
    def __init__(self, name):
        self.name = name
        self.input_default = None
        self.input_communication = None
        self.output_default = None
        self.output_communication = None
        self.hotkey = {
            'keyboard': 'None',
            'mouse': 'None'
        }
        self.trigger_app = None  # Путь к приложению-триггеру

class ProfileManager:
    def __init__(self):
        self.profiles = []
        self.current_profile = None
        self.load_profiles()
        
    def load_profiles(self):
        """Загружает профили из файла"""
        try:
            if os.path.exists('profiles.json'):
                with open('profiles.json', 'r', encoding='utf-8') as f:
                    self.profiles = json.load(f)
        except Exception as e:
            print(f"Error loading profiles: {e}")
            self.profiles = []
            
    def save_profiles_to_file(self):
        """Сохраняет профили в файл"""
        try:
            with open('profiles.json', 'w', encoding='utf-8') as f:
                json.dump(self.profiles, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving profiles to file: {e}")
            return False
            
    def get_profile(self, name):
        """Получает профиль по имени"""
        for profile in self.profiles:
            if profile.get('name') == name:
                return profile
        return None

    def save_profiles(self):
        try:
            with open(self.profiles_file, 'w') as f:
                json.dump(self.profiles, f, indent=4)
        except Exception as e:
            print(f"Error saving profiles: {e}")

    def get_profiles(self):
        return self.profiles

    def add_profile(self, profile):
        if any(p['name'] == profile['name'] for p in self.profiles):
            return False
        self.profiles.append(profile)
        self.save_profiles()
        return True

    def update_profile(self, profile):
        for i, p in enumerate(self.profiles):
            if p['name'] == profile['name']:
                self.profiles[i] = profile
                self.save_profiles()
                return True
        return False

    def delete_profile(self, name):
        self.profiles = [p for p in self.profiles if p['name'] != name]
        self.save_profiles()

# Создаем глобальный экземпляр ProfileManager в начале файла, после определения класса
profile_manager = None

def toggle_sound_volume():
    """Включает/выключает звук"""
    try:
        # Инициализируем COM
        pythoncom.CoInitialize()
        
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        
        if volume.GetMute() == 0:
            volume.SetMute(1, None)
            show_notification("Sound: OFF", "speaker")
        else:
            volume.SetMute(0, None)
            show_notification("Sound: ON", "speaker")
            
    except Exception as e:
        print(f"Error toggling sound volume: {e}")
    finally:
        # Освобождаем COM
        pythoncom.CoUninitialize()

def monitor_processes():
    """Отслеживает запущенные процессы и активирует соответствующие профили"""
    global profile_manager, running
    last_error_time = 0
    error_cooldown = 60  # Минимальный интервал между повторными ошибками в секундах
    activated_apps = set()  # Множество для хранения уже активированных приложений
    
    while running:
        try:
            # Получаем список всех запущенных процессов
            running_processes = set()
            for proc in psutil.process_iter(['name', 'exe']):
                try:
                    proc_info = proc.info
                    if proc_info['exe']:
                        running_processes.add(proc_info['exe'].lower())
                        running_processes.add(os.path.basename(proc_info['exe']).lower())
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                except Exception as e:
                    print(f"Error processing process: {e}")
                    continue

            # Проверяем профили и активируем при необходимости
            for profile in profile_manager.profiles:
                try:
                    if profile.get('trigger_app'):
                        trigger_app = profile['trigger_app'].lower()
                        trigger_app_name = os.path.basename(trigger_app).lower()
                        
                        # Проверяем, запущено ли приложение
                        app_running = trigger_app in running_processes or trigger_app_name in running_processes
                        app_key = f"{trigger_app}|{trigger_app_name}"
                        
                        if app_running:
                            # Если приложение не было активировано ранее
                            if app_key not in activated_apps:
                                print(f"Activating profile {profile['name']} by trigger app")
                                if activate_profile(profile['name']):
                                    show_notification(f"Profile activated: {profile['name']}")
                                    activated_apps.add(app_key)
                                else:
                                    print(f"Failed to activate profile: {profile['name']}")
                        else:
                            # Если приложение больше не запущено, удаляем его из активированных
                            activated_apps.discard(app_key)
                            
                except Exception as e:
                    current_time = time.time()
                    if current_time - last_error_time > error_cooldown:
                        print(f"Error processing profile {profile.get('name', 'unknown')}: {e}")
                        last_error_time = current_time
                        
            time.sleep(2)  # Проверяем каждые 2 секунды
            
        except Exception as e:
            current_time = time.time()
            if current_time - last_error_time > error_cooldown:
                print(f"Error in process monitoring: {e}")
                last_error_time = current_time
            time.sleep(5)  # В случае ошибки ждем подольше

def activate_profile(name):
    """Активирует профиль по имени"""
    try:
        profile = None
        for p in profile_manager.profiles:
            if p.get('name') == name:
                profile = p
                break

        if not profile:
            print(f"Profile not found: {name}")
            return False
            
        print(f"Activating profile with settings: {profile}")  # Отладочный вывод
            
        # Применяем настройки профиля
        if profile.get('input_default'):
            print(f"Setting default input device: {profile['input_default']}")
            set_default_input_device(profile['input_default'])
            
        if profile.get('input_communication'):
            print(f"Setting communication input device: {profile['input_communication']}")
            set_default_input_communication_device(profile['input_communication'])
            
        if profile.get('output_default'):
            print(f"Setting default output device: {profile['output_default']}")
            set_default_audio_device(profile['output_default'])
            
        if profile.get('output_communication'):
            print(f"Setting communication output device: {profile['output_communication']}")
            set_default_communication_device(profile['output_communication'])
            
        profile_manager.current_profile = profile
        print(f"Profile activated: {name}")
        return True
    except Exception as e:
        print(f"Error activating profile: {e}")
        return False

# Добавляем маршрут для выбора приложения
@app.route('/select_trigger_app', methods=['POST'])
def select_trigger_app():
    """Открывает диалог выбора приложения"""
    try:
        print("Opening file dialog...")  # Отладочный вывод
        
        def open_file_dialog():
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            file_path = filedialog.askopenfilename(
                title="Select Application",
                filetypes=[
                    ("Executable files", "*.exe"),
                    ("All files", "*.*")
                ]
            )
            root.destroy()
            return file_path

        # Запускаем диалог в отдельном потоке
        file_path = ""
        thread = Thread(target=lambda: setattr(thread, 'result', open_file_dialog()))
        thread.start()
        thread.join()
        file_path = getattr(thread, 'result', '')

        print(f"Selected file: {file_path}")  # Отладочный вывод

        if file_path:
            response_data = {
                'success': True,
                'path': file_path,
                'name': os.path.basename(file_path)
            }
            print(f"Sending response: {response_data}")  # Отладочный вывод
            return jsonify(response_data)
            
        print("No file selected")  # Отладочный вывод
        return jsonify({
            'success': False,
            'error': 'No file selected'
        })

    except Exception as e:
        print(f"Error in select_trigger_app: {e}")  # Отладочный вывод
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route("/clear_trigger_app", methods=["POST"])
def clear_trigger_app():
    """Очищает привязку приложения-триггера для профиля"""
    try:
        data = request.json
        profile_name = data.get('profile_name')
        
        if not profile_name:
            return jsonify({
                'status': 'error',
                'message': 'Profile name is required'
            })
            
        profile = profile_manager.get_profile(profile_name)
        if not profile:
            return jsonify({
                'status': 'error',
                'message': 'Profile not found'
            })
            
        profile_manager.update_profile(profile_name, {'trigger_app': None})
        return jsonify({'status': 'success'})
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

def get_filename_from_path(path):
    if not path:
        return None
    return path.split('/')[-1]

@app.route('/profiles', methods=['GET', 'POST', 'PUT'])
def handle_profiles():
    profiles_file = 'profiles.json'
    
    if request.method == 'GET':
        try:
            if os.path.exists(profiles_file):
                with open(profiles_file, 'r') as f:
                    profiles = json.load(f)
                    for profile in profiles:
                        if profile.get('trigger_app'):
                            profile['trigger_app'] = get_filename_from_path(profile['trigger_app'])
            else:
                profiles = []
            return jsonify({'status': 'success', 'profiles': profiles})
        except Exception as e:
            print(f"Error loading profiles: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
            
    elif request.method in ['POST', 'PUT']:
        try:
            profile_data = request.get_json()
            print(f"Received profile data: {profile_data}")
            
            if not profile_data:
                print("Error: No profile data received")
                return jsonify({'status': 'error', 'message': 'No profile data received'}), 400
            
            if not profile_data.get('name'):
                print("Error: Profile name is required")
                return jsonify({'status': 'error', 'message': 'Profile name is required'}), 400
            
            # Загружаем существующие профили
            profiles = []
            if os.path.exists(profiles_file):
                try:
                    with open(profiles_file, 'r') as f:
                        profiles = json.load(f)
                except json.JSONDecodeError as e:
                    print(f"Error reading profiles file: {e}")
                    profiles = []
            
            # Проверяем существование профиля
            profile_exists = any(p['name'] == profile_data['name'] for p in profiles)
            
            if request.method == 'PUT' and not profile_exists:
                return jsonify({'status': 'error', 'message': 'Profile not found'}), 404
            
            if request.method == 'POST' and profile_exists:
                return jsonify({'status': 'error', 'message': 'Profile with this name already exists'}), 409
            
            # Создаем новый профиль с правильными значениями по умолчанию
            new_profile = {
                'name': profile_data['name'],
                'output_default': profile_data.get('output_default', ''),
                'output_communication': profile_data.get('output_communication', ''),
                'input_default': profile_data.get('input_default', ''),
                'input_communication': profile_data.get('input_communication', ''),
                'hotkey': profile_data.get('hotkey', {'keyboard': 'None', 'mouse': 'None'}),
                'trigger_app': profile_data.get('trigger_app')
            }
            
            print(f"Processed profile data: {new_profile}")
            
            # Обновляем или добавляем профиль
            if profile_exists:
                profiles = [new_profile if p['name'] == profile_data['name'] else p for p in profiles]
            else:
                profiles.append(new_profile)
            
            try:
                # Сохраняем обновленный список профилей
                with open(profiles_file, 'w') as f:
                    json.dump(profiles, f, indent=4)
                
                # Обновляем профили в мониторинге процессов
                profile_manager.load_profiles()
                
                print("Profile saved successfully")
                return jsonify({'status': 'success'})
            except Exception as e:
                print(f"Error saving profile to file: {e}")
                return jsonify({'status': 'error', 'message': f'Error saving profile: {str(e)}'}), 500
            
        except Exception as e:
            print(f"Error in handle_profiles: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/delete_profile', methods=['POST'])
def delete_profile():
    """Устаревший метод удаления профиля - перенаправляем на новый"""
    try:
        data = request.get_json()
        profile_name = data.get('name')
        
        if not profile_name:
            return jsonify({'status': 'error', 'message': 'Profile name is required'}), 400
            
        # Перенаправляем на новый метод
        return delete_profile_by_name(profile_name)
        
    except Exception as e:
        print(f"Error deleting profile: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/profiles/<profile_name>', methods=['DELETE'])
def delete_profile_by_name(profile_name):
    """Удаляет профиль по имени"""
    try:
        profiles_file = 'profiles.json'
        
        # Загружаем текущие профили
        if not os.path.exists(profiles_file):
            return jsonify({'status': 'error', 'message': 'Profiles file not found'}), 404
            
        with open(profiles_file, 'r') as f:
            profiles = json.load(f)
        
        # Находим и удаляем профиль
        profiles = [p for p in profiles if p['name'] != profile_name]
        
        # Сохраняем обновленный список
        with open(profiles_file, 'w') as f:
            json.dump(profiles, f, indent=4)
        
        # Обновляем профили в мониторинге процессов
        profile_manager.load_profiles()
        
        return jsonify({'status': 'success'})
        
    except Exception as e:
        print(f"Error deleting profile: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def init_globals():
    """Инициализация глобальных переменных"""
    global profile_manager
    profile_manager = ProfileManager()

def main():
    # Устанавливаем модуль при первом запуске
    install_audio_cmdlets()
    
    init_globals()  # Инициализируем глобальные переменные
    
    global running, devices, input_devices, current_device_index, current_input_device_index
    running = True
    
    # Выводим текущие настройки
    print("\nCurrent hotkey settings:")
    for action, combo in hotkeys.items():
        print(f"{action}: keyboard='{combo['keyboard']}', mouse='{combo['mouse']}'")
    print()
    
    # Создаем слушатель изменений устройств
    device_listener = DeviceChangeListener()
    
    # Получаем списки устройств
    devices = get_audio_devices()
    input_devices = get_input_devices()
    
    # Загружаем списки активных устройств
    load_enabled_devices()
    load_enabled_input_devices()
    
    if not devices:
        print("No audio output devices found!")
    else:
        print(f"Found {len(devices)} audio output devices")
        
    if not input_devices:
        print("No audio input devices found!")
    else:
        print(f"Found {len(input_devices)} audio input devices")
    
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("Flask server started")
    
    tracker = KeyboardMouseTracker()
    tracker.start()
    print("Mouse and keyboard tracking started")

    hotkey_thread = Thread(target=lambda: handle_hotkeys(tracker), daemon=True)
    hotkey_thread.start()
    print("Hotkey handler started")

    # Запускаем мониторинг процессов
    process_monitor_thread = Thread(target=monitor_processes, daemon=True)
    process_monitor_thread.start()
    print("Process monitoring started")

    tray = setup_tray()
    tray_thread = Thread(target=lambda: tray.run(), daemon=True)
    tray_thread.start()
    print("Tray icon started")
    
    try:
        while running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        device_listener.stop()
        tray.stop()
        tracker.stop()

def install_audio_cmdlets():
    """Устанавливает модуль AudioDeviceCmdlets при первом запуске"""
    try:
        powershell_path = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
        
        # Проверяем наличие модуля
        check_script = """
        if (Get-Module -ListAvailable -Name AudioDeviceCmdlets) {
            Write-Output "INSTALLED"
        } else {
            Write-Output "NOT_INSTALLED"
        }
        """
        
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        result = subprocess.run(
            [powershell_path, "-Command", check_script],
            capture_output=True,
            text=True,
            encoding='utf-8',
            creationflags=subprocess.CREATE_NO_WINDOW,
            startupinfo=startupinfo
        )
        
        if "NOT_INSTALLED" in result.stdout:
            print("Installing AudioDeviceCmdlets module...")
            show_notification("Installing required module...", "speaker")
            
            # Устанавливаем модуль
            install_script = """
            Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force
            Set-PSRepository -Name PSGallery -InstallationPolicy Trusted
            Install-Module -Name AudioDeviceCmdlets -Force -Scope CurrentUser
            """
            
            result = subprocess.run(
                [powershell_path, "-Command", install_script],
                capture_output=True,
                text=True,
                encoding='utf-8',
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
            
            if result.returncode == 0:
                show_notification("Module installed successfully!", "speaker")
                print("AudioDeviceCmdlets module installed successfully")
            else:
                show_notification("Failed to install module", "speaker")
                print(f"Error installing module: {result.stderr}")
                
    except Exception as e:
        print(f"Error checking/installing AudioDeviceCmdlets: {e}")

if __name__ == "__main__":
    main()
