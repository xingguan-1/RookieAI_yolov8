import tkinter as tk
import threading
import queue
from pynput import keyboard, mouse


class KeyCaptureApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Key Capture")
        self.label = tk.Label(
            root, text="Press any key... (Esc to cancel)", font=('Helvetica', 16))
        self.label.pack(pady=20)

        # 设置焦点以便立即接收键盘事件
        self.root.focus_set()
        self.listener = None
        self.mouse_listener = None
        self.event_result = None
        self.done = False   # 是否已捕获到事件（区分“尚未捕获”与“取消”）
        self._closed = False  # on_close 幂等保护

        # 绑定关闭事件以确保正确清理资源
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def start_listening(self):
        self.listener = keyboard.Listener(on_press=self.on_press)
        self.listener.start()
        self.mouse_listener = mouse.Listener(on_click=self.on_mouse_click)
        self.mouse_listener.start()
        # 注意：pynput 的回调运行在钩子消息泵线程上（WH_KEYBOARD_LL / WH_MOUSE_LL）。
        # 若在回调里调用 stop()/root.quit()，一旦其中任何调用阻塞，该线程将停止
        # 泵消息，钩子链上所有后续的物理鼠标/键盘事件都会被挂起——表现为全系统
        # 鼠标冻结。因此回调里只记录结果，收尾工作交给 Tk 主循环线程上的轮询器。
        self.root.after(50, self._poll_result)

    def _poll_result(self):
        """在 Tk 主循环线程中轮询捕获结果，捕获完成后安全地停止监听并退出。"""
        if self.done:
            self.on_close()
            return
        self.root.after(50, self._poll_result)

    def on_press(self, key):
        # 只在回调里记录结果，绝不在此停止监听器或操作 Tk
        if self.done:
            return
        if key == keyboard.Key.esc:
            self.event_result = None  # Esc 取消设置，返回原来的按键
        elif isinstance(key, keyboard.KeyCode):
            self.event_result = hex(
                key.vk) if key.vk is not None else 'UNKNOWN'
        else:
            self.event_result = hex(key.value.vk)
        self.done = True

    def on_mouse_click(self, x, y, button, pressed):
        if self.done:
            return
        mouse_vk_map = {
            mouse.Button.left: 0x01,   # VK_LBUTTON
            mouse.Button.right: 0x02,  # VK_RBUTTON
            mouse.Button.middle: 0x04,  # VK_MBUTTON
            mouse.Button.x1: 0x05,     # VK_XBUTTON1
            mouse.Button.x2: 0x06      # VK_XBUTTON2
        }
        if vk_code := mouse_vk_map.get(button):
            self.event_result = hex(vk_code)
        else:
            self.event_result = 'UNKNOWN'
        self.done = True

    def on_close(self):
        # 可能被多次触发（轮询器 / WM_DELETE_WINDOW），需要幂等
        if self._closed:
            return
        self._closed = True
        # 从 Tk 主循环线程停止监听器：pynput 的 stop() 只是向钩子线程投递
        # WM_STOP 消息，不会阻塞；钩子线程随后自行退出并卸载钩子。
        if self.listener is not None:
            self.listener.stop()
            self.listener = None
        if self.mouse_listener is not None:
            self.mouse_listener.stop()
            self.mouse_listener = None
        self.root.quit()  # 使用 quit 而不是 destroy 以便返回结果

    def capture_event(self):
        self.start_listening()
        self.root.mainloop()
        return self.event_result


def get_keyboard_event(text="UNKNOWN"):
    result_queue = queue.Queue()

    def capture_key():
        key = KeyCaptureApp(tk.Tk()).capture_event()
        result_queue.put(key)

    thread = threading.Thread(target=capture_key)
    thread.start()
    # 等待线程完成（模态捕获）；加超时兜底，避免任何意外情况下卡死调用方 UI
    thread.join(timeout=60)
    if thread.is_alive():
        # 兜底：理论上不会走到这里，但绝不能无限期阻塞 Qt 主线程
        return text

    # 获取结果
    key = 'UNKNOWN' if result_queue.empty() else result_queue.get()

    return text if key is None or key == 'UNKNOWN' else key


keys_maps_vk = {
    "VK_LBUTTON": 0x01,
    "VK_RBUTTON": 0x02,
    "VK_CANCEL": 0x03,
    "VK_MBUTTON": 0x04,
    "VK_XBUTTON1": 0x05,
    "VK_XBUTTON2": 0x06,
    "VK_BACK": 0x08,
    "VK_TAB": 0x09,
    "VK_CLEAR": 0x0C,
    "VK_RETURN": 0x0D,
    "VK_SHIFT": 0x10,
    "VK_CONTROL": 0x11,
    "VK_MENU": 0x12,
    "VK_PAUSE": 0x13,
    "VK_CAPITAL": 0x14,
    "VK_KANA": 0x15,
    "VK_HANGUL": 0x15,
    "VK_IME_ON": 0x16,
    "VK_JUNJA": 0x17,
    "VK_FINAL": 0x18,
    "VK_HANJA": 0x19,
    "VK_KANJI": 0x19,
    "VK_IME_OFF": 0x1A,
    "VK_ESCAPE": 0x1B,
    "VK_CONVERT": 0x1C,
    "VK_NONCONVERT": 0x1D,
    "VK_ACCEPT": 0x1E,
    "VK_MODECHANGE": 0x1F,
    "VK_SPACE": 0x20,
    "VK_PRIOR": 0x21,
    "VK_NEXT": 0x22,
    "VK_END": 0x23,
    "VK_HOME": 0x24,
    "VK_LEFT": 0x25,
    "VK_UP": 0x26,
    "VK_RIGHT": 0x27,
    "VK_DOWN": 0x28,
    "VK_SELECT": 0x29,
    "VK_PRINT": 0x2A,
    "VK_EXECUTE": 0x2B,
    "VK_SNAPSHOT": 0x2C,
    "VK_INSERT": 0x2D,
    "VK_DELETE": 0x2E,
    "VK_HELP": 0x2F,
    "VK_0": 0x30,
    "VK_1": 0x31,
    "VK_2": 0x32,
    "VK_3": 0x33,
    "VK_4": 0x34,
    "VK_5": 0x35,
    "VK_6": 0x36,
    "VK_7": 0x37,
    "VK_8": 0x38,
    "VK_9": 0x39,
    "VK_A": 0x41,
    "VK_B": 0x42,
    "VK_C": 0x43,
    "VK_D": 0x44,
    "VK_E": 0x45,
    "VK_F": 0x46,
    "VK_G": 0x47,
    "VK_H": 0x48,
    "VK_I": 0x49,
    "VK_J": 0x4A,
    "VK_K": 0x4B,
    "VK_L": 0x4C,
    "VK_M": 0x4D,
    "VK_N": 0x4E,
    "VK_O": 0x4F,
    "VK_P": 0x50,
    "VK_Q": 0x51,
    "VK_R": 0x52,
    "VK_S": 0x53,
    "VK_T": 0x54,
    "VK_U": 0x55,
    "VK_V": 0x56,
    "VK_W": 0x57,
    "VK_X": 0x58,
    "VK_Y": 0x59,
    "VK_Z": 0x5A,
    "VK_LWIN": 0x5B,
    "VK_RWIN": 0x5C,
    "VK_APPS": 0x5D,
    "VK_SLEEP": 0x5F,
    "VK_NUMPAD0": 0x60,
    "VK_NUMPAD1": 0x61,
    "VK_NUMPAD2": 0x62,
    "VK_NUMPAD3": 0x63,
    "VK_NUMPAD4": 0x64,
    "VK_NUMPAD5": 0x65,
    "VK_NUMPAD6": 0x66,
    "VK_NUMPAD7": 0x67,
    "VK_NUMPAD8": 0x68,
    "VK_NUMPAD9": 0x69,
    "VK_MULTIPLY": 0x6A,
    "VK_ADD": 0x6B,
    "VK_SEPARATOR": 0x6C,
    "VK_SUBTRACT": 0x6D,
    "VK_DECIMAL": 0x6E,
    "VK_DIVIDE": 0x6F,
    "VK_F1": 0x70,
    "VK_F2": 0x71,
    "VK_F3": 0x72,
    "VK_F4": 0x73,
    "VK_F5": 0x74,
    "VK_F6": 0x75,
    "VK_F7": 0x76,
    "VK_F8": 0x77,
    "VK_F9": 0x78,
    "VK_F10": 0x79,
    "VK_F11": 0x7A,
    "VK_F12": 0x7B,
    "VK_F13": 0x7C,
    "VK_F14": 0x7D,
    "VK_F15": 0x7E,
    "VK_F16": 0x7F,
    "VK_F17": 0x80,
    "VK_F18": 0x81,
    "VK_F19": 0x82,
    "VK_F20": 0x83,
    "VK_F21": 0x84,
    "VK_F22": 0x85,
    "VK_F23": 0x86,
    "VK_F24": 0x87,
    "VK_NUMLOCK": 0x90,
    "VK_SCROLL": 0x91,
    "VK_LSHIFT": 0xA0,
    "VK_RSHIFT": 0xA1,
    "VK_LCONTROL": 0xA2,
    "VK_RCONTROL": 0xA3,
    "VK_LMENU": 0xA4,
    "VK_RMENU": 0xA5,
    "VK_BROWSER_BACK": 0xA6,
    "VK_BROWSER_FORWARD": 0xA7,
    "VK_BROWSER_REFRESH": 0xA8,
    "VK_BROWSER_STOP": 0xA9,
    "VK_BROWSER_SEARCH": 0xAA,
    "VK_BROWSER_FAVORITES": 0xAB,
    "VK_BROWSER_HOME": 0xAC,
    "VK_VOLUME_MUTE": 0xAD,
    "VK_VOLUME_DOWN": 0xAE,
    "VK_VOLUME_UP": 0xAF,
    "VK_MEDIA_NEXT_TRACK": 0xB0,
    "VK_MEDIA_PREV_TRACK": 0xB1,
    "VK_MEDIA_STOP": 0xB2,
    "VK_MEDIA_PLAY_PAUSE": 0xB3,
    "VK_LAUNCH_MAIL": 0xB4,
    "VK_LAUNCH_MEDIA_SELECT": 0xB5,
    "VK_LAUNCH_APP1": 0xB6,
    "VK_LAUNCH_APP2": 0xB7,
    "VK_OEM_1": 0xBA,
    "VK_OEM_PLUS": 0xBB,
    "VK_OEM_COMMA": 0xBC,
    "VK_OEM_MINUS": 0xBD,
    "VK_OEM_PERIOD": 0xBE,
    "VK_OEM_2": 0xBF,
    "VK_OEM_3": 0xC0,
    "VK_OEM_4": 0xDB,
    "VK_OEM_5": 0xDC,
    "VK_OEM_6": 0xDD,
    "VK_OEM_7": 0xDE,
    "VK_OEM_8": 0xDF,
    "VK_OEM_102": 0xE2,
    "VK_PROCESSKEY": 0xE5,
    "VK_PACKET": 0xE7,
    "VK_ATTN": 0xF6,
    "VK_CRSEL": 0xF7,
    "VK_EXSEL": 0xF8,
    "VK_EREOF": 0xF9,
    "VK_PLAY": 0xFA,
    "VK_ZOOM": 0xFB,
    "VK_PA1": 0xFD,
    "VK_OEM_CLEAR": 0xFE
}


def get_key_name_vk(hex):
    return dict(
        zip(keys_maps_vk.values(),
            keys_maps_vk.keys())
    ).get(int(hex, 16), "UNKNOWN")


def get_key_code_vk(key_name):
    return keys_maps_vk.get(key_name, "UNKNOWN")
