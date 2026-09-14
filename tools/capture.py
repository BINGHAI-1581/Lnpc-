# -*- coding: utf-8 -*-
"""截取应用窗口为 PNG（整屏抓取后裁剪）。

要点：必须先创建 QApplication（进程切到 DPI 感知），GetWindowRect 才会返回
与整屏抓图一致的物理像素坐标；否则会被 DPI 虚拟化成逻辑坐标导致裁剪错位。
"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

user32 = ctypes.windll.user32
TITLE = "课程推送助手"
SW_RESTORE = 9
HWND_TOPMOST, HWND_NOTOPMOST = -1, -2
SWP_NOMOVE, SWP_NOSIZE, SWP_SHOWWINDOW = 0x0002, 0x0001, 0x0040

hwnds = []


@ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
def enum_proc(hwnd, lparam):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, buf, 256)
    if buf.value == TITLE and user32.IsWindowVisible(hwnd):
        hwnds.append(hwnd)
    return True


def main(out_path):
    # 1. 先初始化 Qt，使进程具备 DPI 感知
    app = QApplication(sys.argv)
    screen = QGuiApplication.primaryScreen()

    user32.EnumWindows(enum_proc, 0)
    if not hwnds:
        print("未找到窗口")
        return 1
    hwnd = hwnds[0]

    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    user32.SetForegroundWindow(hwnd)
    time.sleep(2.5)

    rect = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    cx, cy = (rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2
    top = user32.WindowFromPoint(wt.POINT(cx, cy))
    owner = user32.GetAncestor(top, 2) or top
    if owner != hwnd:
        print("警告: 窗口中心被其它窗口遮挡")

    full = screen.grabWindow(0)
    x = max(0, rect.left)
    y = max(0, rect.top)
    w = min(rect.right - rect.left, full.width() - x)
    h = min(rect.bottom - rect.top, full.height() - y)
    full.copy(x, y, w, h).save(out_path, "PNG")

    user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    print("saved %s  crop=(%d,%d,%d,%d) dpr=%.2f screen=%dx%d" % (
        out_path, x, y, w, h, screen.devicePixelRatio(),
        full.width(), full.height()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "shot.png"))
