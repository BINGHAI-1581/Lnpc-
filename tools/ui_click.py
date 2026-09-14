# -*- coding: utf-8 -*-
"""自动化 UI 测试辅助：把应用窗口置前并模拟真实鼠标点击。

用法:
    python tools/ui_click.py X Y [X2 Y2 ...]      # 依次点击屏幕物理坐标
    python tools/ui_click.py --rect               # 仅打印窗口矩形后退出

坐标使用屏幕物理像素（与 tools/capture.py 的输出同一坐标系）。
"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

# 必须声明 DPI 感知：否则 GetWindowRect/SetCursorPos 用的是被虚拟化的逻辑坐标，
# 与 tools/capture.py 抓到的物理像素对不上，点击就会偏到别处。
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)      # PER_MONITOR_DPI_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

user32 = ctypes.windll.user32
TITLE = "课程推送助手"
HWND_TOPMOST, HWND_NOTOPMOST = -1, -2
SWP_NOMOVE, SWP_NOSIZE, SWP_SHOWWINDOW = 0x0002, 0x0001, 0x0040

handles = []


@ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
def _enum(hwnd, lparam):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, buf, 256)
    if buf.value == TITLE and user32.IsWindowVisible(hwnd):
        handles.append(hwnd)
    return True


def find_window():
    del handles[:]
    user32.EnumWindows(_enum, 0)
    if not handles:
        raise SystemExit("未找到应用窗口，请先启动程序")
    return handles[0]


def window_rect(hwnd):
    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right - r.left, r.bottom - r.top


def focus(hwnd):
    """置顶并置前（先送一次 Alt 解除前台锁定）。"""
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    user32.keybd_event(0x12, 0, 0, 0)
    user32.keybd_event(0x12, 0, 2, 0)
    user32.SetForegroundWindow(hwnd)
    time.sleep(1.0)
    return user32.GetForegroundWindow() == hwnd


def _release_all():
    """清掉可能残留的按下状态。

    合成输入若在异常路径上漏发了抬起，系统会认为左键一直按着；此时鼠标一旦
    移到某个控件上，Qt 就会把它当成 press→release，产生"幽灵点击"。
    """
    for _ in range(3):
        user32.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(0.15)


def click(x, y, settle=0.9):
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.5)
    user32.mouse_event(0x0001, 0, 0, 0, 0)      # 先发移动，确保 Qt 收到 hover
    time.sleep(0.25)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.12)
    user32.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(settle)
    _release_all()


def main(argv):
    hwnd = find_window()
    x, y, w, h = window_rect(hwnd)
    if "--rect" in argv:
        print("window x=%d y=%d w=%d h=%d" % (x, y, w, h))
        return 0
    if not focus(hwnd):
        print("警告：窗口未能置前，点击可能不生效")
    _release_all()
    nums = [int(v) for v in argv if v.lstrip("-").isdigit()]
    if len(nums) < 2 or len(nums) % 2:
        print("用法: python tools/ui_click.py X Y [X2 Y2 ...]")
        return 2
    for i in range(0, len(nums), 2):
        print("click (%d, %d)" % (nums[i], nums[i + 1]))
        click(nums[i], nums[i + 1])
    user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
