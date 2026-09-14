# -*- coding: utf-8 -*-
"""滚动条"跟手"自动化测试：拖动缩略图，检查它是否 1:1 跟随光标。

用法:
    python tools/test_scrollbar.py [vertical|horizontal]

原理：截图定位缩略图位置 → 合成鼠标从缩略图中心按下并下移 Δ 像素 →
再截图，检查缩略图位移是否 ≈ Δ（跟手），并输出实际/理论比例。
"""
import ctypes
import ctypes.wintypes as wt
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

user32 = ctypes.windll.user32
TITLE = "课程推送助手"
HWND_TOPMOST, HWND_NOTOPMOST = -1, -2
SWP_NOMOVE, SWP_NOSIZE, SWP_SHOWWINDOW = 0x0002, 0x0001, 0x0040


def find_window():
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buf, 256)
        if buf.value == TITLE and user32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True

    user32.EnumWindows(cb, 0)
    if not found:
        raise SystemExit("未找到应用窗口，请先启动程序")
    return found[0]


def window_rect(hwnd):
    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right - r.left, r.bottom - r.top


def grab(rect, path):
    """抓取窗口画面（整屏抓取后裁剪，能正确捕获 D3D 渲染内容）。"""
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    screen = QGuiApplication.primaryScreen()
    full = screen.grabWindow(0)
    x, y, w, h = rect
    full.copy(max(0, x), max(0, y), w, h).save(path, "PNG")
    return path


def find_thumb(path, vertical=True):
    """在窗口截图里找滚动条缩略图：一根细长的中灰色圆角条。"""
    from PySide6.QtGui import QImage, QColor
    img = QImage(path)
    W, H = img.width(), img.height()
    # vertical：外层扫列、内层扫 y；horizontal：外层扫行、内层扫 x
    outer = range(int(W * 0.90), W - 6) if vertical else range(H - 8, int(H * 0.55), -1)
    inner_end = H - 20 if vertical else W - 20
    best = None
    for c in outer:
        run = []
        for i in range(20, inner_end):
            col = QColor(img.pixel(c, i)) if vertical else QColor(img.pixel(i, c))
            lum = col.lightness()
            if 120 < lum < 225:
                run.append(i)
            else:
                if len(run) >= 24 and (best is None or len(run) > best[3]):
                    best = (c, run[0], run[-1], len(run))
                run = []
        if len(run) >= 24 and (best is None or len(run) > best[3]):
            best = (c, run[0], run[-1], len(run))
    return best  # (固定坐标, 起点, 终点, 长度)


def main(argv):
    vertical = "--horizontal" not in argv
    hwnd = find_window()
    rect = window_rect(hwnd)
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    user32.keybd_event(0x12, 0, 0, 0)
    user32.keybd_event(0x12, 0, 2, 0)
    user32.SetForegroundWindow(hwnd)
    for _ in range(3):
        user32.mouse_event(0x0004, 0, 0, 0, 0)     # 清掉可能残留的按下状态
    user32.SetCursorPos(5, 1555)
    time.sleep(1.5)

    tmp = os.environ.get("TEMP", ".")
    before = grab(rect, os.path.join(tmp, "sb_before.png"))
    t1 = find_thumb(before, vertical)
    if not t1:
        print("未找到滚动条缩略图")
        return 2
    fixed, start, end, length = t1
    print("拖动前缩略图：坐标轴=%s 固定位=%d 区间 %d..%d 长 %d"
          % ("y" if vertical else "x", fixed, start, end, length))

    delta = 140
    if vertical:
        x0, y0 = rect[0] + fixed, rect[1] + (start + end) // 2
        x1, y1 = x0, y0 + delta
    else:
        x0, y0 = rect[0] + (start + end) // 2, rect[1] + fixed
        x1, y1 = x0 + delta, y0

    user32.SetCursorPos(x0, y0)
    time.sleep(0.4)
    user32.mouse_event(0x0001, 0, 0, 0, 0)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.25)
    steps = 28
    for i in range(1, steps + 1):
        user32.SetCursorPos(int(x0 + (x1 - x0) * i / steps),
                            int(y0 + (y1 - y0) * i / steps))
        time.sleep(0.02)
    time.sleep(0.3)
    user32.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(0.8)
    for _ in range(3):
        user32.mouse_event(0x0004, 0, 0, 0, 0)

    after = grab(rect, os.path.join(tmp, "sb_after.png"))
    t2 = find_thumb(after, vertical)
    if not t2:
        print("拖动后未找到缩略图")
        return 2
    fixed2, start2, end2, length2 = t2
    moved = start2 - start
    print("拖动后缩略图：区间 %d..%d 长 %d" % (start2, end2, length2))
    print("光标位移 %d px，缩略图位移 %d px → 比例 %.2f（1.00 为完全跟手）"
          % (delta, moved, moved / float(delta)))
    ok = 0.75 <= moved / float(delta) <= 1.25
    print("结果:", "跟手 ✓" if ok else "不跟手 ✗")

    user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
