# -*- coding: utf-8 -*-
"""生成应用图标（多尺寸 .ico），并把快捷方式创建到桌面。

用法：
    python tools/create_shortcut.py            # 生成图标 + 创建桌面快捷方式
    python tools/create_shortcut.py --icon-only # 只生成图标
"""
import ctypes
import ctypes.wintypes as wt
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICON_PATH = os.path.join(ROOT, "assets", "app.ico")
SHORTCUT_NAME = "课程推送助手.lnk"
SIZES = (256, 128, 64, 48, 32, 16)


# ---------------- 图标 ----------------

def _draw(size: int):
    """画一个 Apple 风格的圆角方块 + 白色「课」字。"""
    from PySide6.QtCore import Qt, QRectF
    from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QLinearGradient, QPen

    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.TextAntialiasing, True)

    pad = max(1.0, size * 0.045)
    radius = size * 0.235
    rect = QRectF(pad, pad, size - pad * 2, size - pad * 2)

    grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
    grad.setColorAt(0.0, QColor("#4C9BFF"))
    grad.setColorAt(1.0, QColor("#5B5BFF"))
    p.setBrush(grad)
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(rect, radius, radius)

    # 顶部高光，模仿 iOS 图标质感
    gloss = QLinearGradient(rect.topLeft(), QRectF(rect).bottomLeft())
    gloss.setColorAt(0.0, QColor(255, 255, 255, 70))
    gloss.setColorAt(0.55, QColor(255, 255, 255, 0))
    p.setBrush(gloss)
    p.drawRoundedRect(rect.adjusted(0, 0, 0, -rect.height() * 0.35), radius, radius)

    p.setPen(QPen(QColor(255, 255, 255)))
    font = QFont("Microsoft YaHei UI")
    font.setBold(True)
    font.setPixelSize(max(6, int(size * 0.56)))
    p.setFont(font)
    p.drawText(pm.rect(), Qt.AlignCenter, "课")
    p.end()
    return pm


def build_icon(path: str = ICON_PATH) -> str:
    """把多个尺寸的 PNG 打包成 .ico（Vista+ 支持 PNG 压缩的图标条目）。"""
    from PySide6.QtCore import QBuffer, QByteArray
    from PySide6.QtGui import QImage

    os.makedirs(os.path.dirname(path), exist_ok=True)
    pngs = []
    for size in SIZES:
        pm = _draw(size)
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QBuffer.WriteOnly)
        pm.save(buf, "PNG")
        buf.close()
        pngs.append((size, bytes(ba.data())))

    header = bytearray()
    header += (0).to_bytes(2, "little")            # reserved
    header += (1).to_bytes(2, "little")            # type: icon
    header += len(pngs).to_bytes(2, "little")      # count

    offset = 6 + 16 * len(pngs)
    entries = bytearray()
    body = bytearray()
    for size, data in pngs:
        entries += bytes([0 if size >= 256 else size,    # width
                          0 if size >= 256 else size,    # height
                          0, 0,                          # palette, reserved
                          1, 0])                         # color planes
        entries += (32).to_bytes(2, "little")            # bpp
        entries += len(data).to_bytes(4, "little")
        entries += offset.to_bytes(4, "little")
        offset += len(data)
        body += data

    with open(path, "wb") as f:
        f.write(bytes(header) + bytes(entries) + bytes(body))
    return path


# ---------------- 桌面路径 / 快捷方式 ----------------

def desktop_dir() -> str:
    """取桌面目录（兼容 OneDrive 重定向），失败时回退到 ~/Desktop。"""
    try:
        import uuid
        FOLDERID_Desktop = uuid.UUID("{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}")
        buf = ctypes.c_wchar_p()
        ole = ctypes.windll.ole32
        ole.CoInitialize(0)
        guid = ctypes.c_buffer(16)
        ctypes.memmove(guid, FOLDERID_Desktop.bytes_le, 16)
        if ctypes.windll.shell32.SHGetKnownFolderPath(
                guid, 0, None, ctypes.byref(buf)) == 0:
            path = buf.value
            ctypes.windll.ole32.CoTaskMemFree(buf)
            if path and os.path.isdir(path):
                return path
    except Exception:
        pass
    return os.path.join(os.path.expanduser("~"), "Desktop")


def pythonw() -> str:
    cand = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return cand if os.path.exists(cand) else sys.executable


def create_shortcut() -> str:
    target = pythonw()
    main_py = os.path.join(ROOT, "main.py")
    link = os.path.join(desktop_dir(), SHORTCUT_NAME)
    ps = (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut('{link}');"
        "$s.TargetPath = '{target}';"
        "$s.Arguments = '\"{main}\"';"
        "$s.WorkingDirectory = '{dir}';"
        "$s.IconLocation = '{icon}';"
        "$s.Description = '课程推送助手 —— 自动抓取课表并推送到微信';"
        "$s.WindowStyle = 1;"
        "$s.Save()"
    ).format(link=link, target=target, main=main_py, dir=ROOT, icon=ICON_PATH)
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                   check=True, capture_output=True)
    return link


def read_shortcut(link: str) -> dict:
    ps = ("$s = (New-Object -ComObject WScript.Shell).CreateShortcut('{0}');"
          "Write-Output $s.TargetPath; Write-Output $s.Arguments;"
          "Write-Output $s.WorkingDirectory; Write-Output $s.IconLocation").format(link)
    out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                         capture_output=True, text=True)
    lines = [l.strip() for l in out.stdout.splitlines() if l.strip()]
    return {"link": link, "target": lines[0] if lines else "",
            "args": lines[1] if len(lines) > 1 else "",
            "cwd": lines[2] if len(lines) > 2 else "",
            "icon": lines[3] if len(lines) > 3 else ""}


def main(argv):
    from PySide6.QtWidgets import QApplication
    app = QApplication(argv)          # QPixmap 需要 QGuiApplication

    icon = build_icon()
    print("图标已生成: %s (%d 字节)" % (icon, os.path.getsize(icon)))
    if "--icon-only" in argv:
        return 0

    link = create_shortcut()
    info = read_shortcut(link)
    print("桌面快捷方式: %s" % info["link"])
    print("  目标: %s" % info["target"])
    print("  参数: %s" % info["args"])
    print("  工作目录: %s" % info["cwd"])
    print("  图标: %s" % info["icon"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
