# -*- coding: utf-8 -*-
"""自动化测试无边框窗口的边缘拖拽缩放：模拟真实鼠标按下-移动-抬起。"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

user32 = ctypes.windll.user32
TITLE = "课程推送助手"
SW_RESTORE = 9
HWND_TOPMOST, HWND_NOTOPMOST = -1, -2
SWP_NOMOVE, SWP_NOSIZE, SWP_SHOWWINDOW = 0x0002, 0x0001, 0x0040

MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP = 0x0002, 0x0004

hwnds = []


@ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
def enum_proc(hwnd, lparam):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, buf, 256)
    if buf.value == TITLE and user32.IsWindowVisible(hwnd):
        hwnds.append(hwnd)
    return True


def rect_of(hwnd):
    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right - r.left, r.bottom - r.top


def drag(x0, y0, x1, y1, steps=25):
    user32.SetCursorPos(int(x0), int(y0))
    time.sleep(0.4)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.3)
    for i in range(1, steps + 1):
        user32.SetCursorPos(int(x0 + (x1 - x0) * i / steps),
                            int(y0 + (y1 - y0) * i / steps))
        time.sleep(0.03)
    time.sleep(0.3)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.5)


def focus(hwnd):
    """Windows 限制后台进程抢占前台，先送一次 Alt 键再置前台，并校验是否成功。"""
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    user32.keybd_event(0x12, 0, 0, 0)   # Alt down
    user32.keybd_event(0x12, 0, 2, 0)   # Alt up
    user32.SetForegroundWindow(hwnd)
    time.sleep(1.2)
    return user32.GetForegroundWindow() == hwnd


def main():
    user32.EnumWindows(enum_proc, 0)
    if not hwnds:
        print("未找到窗口")
        return 1
    hwnd = hwnds[0]
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    if not focus(hwnd):
        print("无法将窗口置为前台，测试中止（结果不可信）")
        user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0,
                            SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
        return 2

    x, y, w, h = rect_of(hwnd)
    print("初始: x=%d y=%d w=%d h=%d" % (x, y, w, h))
    ok = True

    # 1. 右边缘向右拖 120px -> 宽度 +120
    drag(x + w - 3, y + h // 2, x + w - 3 + 120, y + h // 2)
    x2, y2, w2, h2 = rect_of(hwnd)
    print("右边缘拖 +120 后: w=%d (预期 %d) %s" % (w2, w + 120, "OK" if abs(w2 - (w + 120)) <= 8 else "不符"))
    ok &= abs(w2 - (w + 120)) <= 8

    # 2. 下边缘向下拖 80px -> 高度 +80
    x, y, w, h = rect_of(hwnd)
    drag(x + w // 2, y + h - 3, x + w // 2, y + h - 3 + 80)
    x3, y3, w3, h3 = rect_of(hwnd)
    print("下边缘拖 +80 后:  h=%d (预期 %d) %s" % (h3, h + 80, "OK" if abs(h3 - (h + 80)) <= 8 else "不符"))
    ok &= abs(h3 - (h + 80)) <= 8

    # 3. 左边缘向左拖 60px -> 宽度 +60 且 x 左移 60
    x, y, w, h = rect_of(hwnd)
    drag(x + 3, y + h // 2, x + 3 - 60, y + h // 2)
    x4, y4, w4, h4 = rect_of(hwnd)
    print("左边缘拖 -60 后:  w=%d (预期 %d) x=%d (预期 %d) %s" % (
        w4, w + 60, x4, x - 60,
        "OK" if abs(w4 - (w + 60)) <= 8 and abs(x4 - (x - 60)) <= 8 else "不符"))
    ok &= abs(w4 - (w + 60)) <= 8 and abs(x4 - (x - 60)) <= 8

    # 4. 左上角斜拖 -> 宽高同时变化
    x, y, w, h = rect_of(hwnd)
    drag(x + 4, y + 4, x + 4 - 70, y + 4 - 50)
    x5, y5, w5, h5 = rect_of(hwnd)
    print("左上角斜拖后:    w=%d (预期 %d) h=%d (预期 %d) %s" % (
        w5, w + 70, h5, h + 50,
        "OK" if abs(w5 - (w + 70)) <= 10 and abs(h5 - (h + 50)) <= 10 else "不符"))
    ok &= abs(w5 - (w + 70)) <= 10 and abs(h5 - (h + 50)) <= 10

    user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    print("\n结果:", "全部通过" if ok else "有不符合项")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
