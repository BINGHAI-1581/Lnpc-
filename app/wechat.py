# -*- coding: utf-8 -*-
"""微信桌面版自动发送：激活窗口 → Ctrl+F 搜索 → 打开会话 → 剪贴板粘贴 → 回车发送。

仅使用 Windows 原生 API（SendInput / 剪贴板 / FindWindow），不注入、不改协议。
要求：微信 PC 版已登录（3.x 或 4.x 均可）。
"""
import ctypes
import ctypes.wintypes as wt
import os
import subprocess
import time

ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

VK_CONTROL = 0x11
VK_MENU = 0x12       # Alt
VK_RETURN = 0x0D
VK_V = 0x56
VK_F = 0x46
VK_ESCAPE = 0x1B

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
INPUT_KEYBOARD = 1
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
SW_RESTORE = 9

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD),
                ("dwFlags", wt.DWORD), ("time", wt.DWORD),
                ("dwExtraInfo", ULONG_PTR)]


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wt.LONG), ("dy", wt.LONG), ("mouseData", wt.DWORD),
                ("dwFlags", wt.DWORD), ("time", wt.DWORD),
                ("dwExtraInfo", ULONG_PTR)]


class _HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wt.DWORD), ("wParamL", wt.WORD), ("wParamH", wt.WORD)]


class _InputUnion(ctypes.Union):
    _fields_ = [("ki", _KEYBDINPUT), ("mi", _MOUSEINPUT), ("hi", _HARDWAREINPUT)]


class _INPUT(ctypes.Structure):
    _anonymous_ = ("ii",)
    _fields_ = [("type", wt.DWORD), ("ii", _InputUnion)]


def _key(vk=None, scan=None, flags=0):
    inp = _INPUT(type=INPUT_KEYBOARD)
    inp.ii.ki = _KEYBDINPUT(wVk=vk or 0, wScan=scan or 0, dwFlags=flags)
    _user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))


def _press(vk, with_ctrl=False):
    if with_ctrl:
        _key(vk=VK_CONTROL)
    _key(vk=vk)
    time.sleep(0.05)
    _key(vk=vk, flags=KEYEVENTF_KEYUP)
    if with_ctrl:
        time.sleep(0.05)
        _key(vk=VK_CONTROL, flags=KEYEVENTF_KEYUP)


def _type_text(text: str):
    for ch in text:
        if ch in "\r\n\t":
            continue
        _key(scan=ord(ch), flags=KEYEVENTF_UNICODE)
        _key(scan=ord(ch), flags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)
        time.sleep(0.02)


def set_clipboard(text: str):
    data = text.encode("utf-16-le") + b"\x00\x00"
    for _ in range(5):
        if _user32.OpenClipboard(0):
            break
        time.sleep(0.1)
    else:
        raise RuntimeError("无法打开剪贴板")
    try:
        _user32.EmptyClipboard()
        h = _kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        p = _kernel32.GlobalLock(h)
        ctypes.memmove(p, data, len(data))
        _kernel32.GlobalUnlock(h)
        _user32.SetClipboardData(CF_UNICODETEXT, h)
    finally:
        _user32.CloseClipboard()


# ---------------- 窗口 ----------------

_WND_CLASSES = ("WeChatMainWndForPC",   # 微信 3.x 主窗口
                "mmui::MainWindow")     # 微信 4.x 主窗口


@ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
def _enum_proc(hwnd, lparam):
    buf = ctypes.create_unicode_buffer(256)
    _user32.GetWindowTextW(hwnd, buf, 256)
    cls = ctypes.create_unicode_buffer(256)
    _user32.GetClassNameW(hwnd, cls, 256)
    if buf.value in ("微信", "WeChat") and _user32.IsWindowVisible(hwnd):
        found.append(hwnd)
        return False
    return True


found = []


def find_wechat() -> int:
    for cls in _WND_CLASSES:
        hwnd = _user32.FindWindowW(cls, None)
        if hwnd:
            return hwnd
    del found[:]
    _user32.EnumWindows(_enum_proc, 0)
    return found[0] if found else 0


def _candidate_paths():
    env = os.environ.get
    roots = [
        env("ProgramFiles"), env("ProgramFiles(x86)"),
        os.path.join(env("LOCALAPPDATA") or "", "Programs"),
    ]
    names = [os.path.join("Tencent", "WeChat", "WeChat.exe"),
             os.path.join("Tencent", "Weixin", "Weixin.exe"),
             os.path.join("Tencent", "WeChat", "Weixin.exe")]
    for r in roots:
        if not r:
            continue
        for n in names:
            yield os.path.join(r, n)


def ensure_wechat_running(custom_path: str = "") -> int:
    hwnd = find_wechat()
    if hwnd:
        return hwnd
    exe = custom_path if custom_path and os.path.exists(custom_path) else ""
    if not exe:
        exe = next((p for p in _candidate_paths() if os.path.exists(p)), "")
    if not exe:
        raise RuntimeError("未找到微信程序，请在设置的运行方式中填写 WeChat.exe 路径")
    subprocess.Popen([exe])
    deadline = time.time() + 20
    while time.time() < deadline:
        time.sleep(1.0)
        hwnd = find_wechat()
        if hwnd:
            time.sleep(2.0)  # 等待窗口就绪
            return hwnd
    raise RuntimeError("微信启动超时，请确认微信已登录")


def activate(hwnd: int):
    if _user32.IsIconic(hwnd):
        _user32.ShowWindow(hwnd, SW_RESTORE)
        time.sleep(0.3)
    # Alt 单击解除前台锁定，再置前
    _user32.keybd_event(VK_MENU, 0, 0, 0)
    _user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
    for _ in range(3):
        if _user32.SetForegroundWindow(hwnd):
            return
        time.sleep(0.3)
    raise RuntimeError("无法将微信切换到前台，请稍后重试")


def send_text(target: str, text: str, wechat_path: str = "") -> None:
    """把 text 发送到微信联系人/群 target。"""
    if not target:
        raise RuntimeError("未设置发送目标（微信群名或文件传输助手）")
    hwnd = ensure_wechat_running(wechat_path)
    activate(hwnd)
    time.sleep(0.8)

    _press(vk=VK_ESCAPE)             # 关闭可能残留的搜索面板
    time.sleep(0.3)
    _press(vk=VK_F, with_ctrl=True)  # 打开搜索
    time.sleep(0.7)
    _type_text(target)
    time.sleep(1.6)                  # 等待搜索结果
    _press(vk=VK_RETURN)             # 选中第一个结果
    time.sleep(0.9)

    set_clipboard(text)
    _press(vk=VK_V, with_ctrl=True)  # 粘贴到输入框
    time.sleep(0.5)
    _press(vk=VK_RETURN)             # 发送
    time.sleep(0.4)
