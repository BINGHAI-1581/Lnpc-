# -*- coding: utf-8 -*-
"""配置持久化：JSON 存储于 %APPDATA%/CoursePusher/config.json，密码使用 Windows DPAPI 加密。"""
import base64
import ctypes
import ctypes.wintypes as wt
import json
import os
import sys
import winreg

APP_NAME = "CoursePusher"

DEFAULTS = {
    "account": "",
    "password_enc": "",          # DPAPI 加密后的 base64，绝不以明文落盘
    "send_mode": "scheduled",    # manual / scheduled
    "send_hour": 7,
    "send_minute": 30,
    "send_target": "文件传输助手",  # 微信群名或联系人
    "scope": "today",            # today / seven
    "style": "detailed",         # detailed / compact
    "emoji": True,
    "autostart": False,
    "wechat_path": "",           # 留空自动检测
    "last_sent_date": "",
    "window": {},                # 上次窗口位置与大小
    # 节次 → 时间：每两项小节合为一大节（第01-02、03-04、05-06、07-08、09-10 节）
    "period_times": ["08:00-10:05", "10:25-12:00", "13:30-15:05",
                     "15:10-16:45", "18:00-19:40"],
    # 临时添加的课程：[{name, day(1-7), time, room, weeks}]
    "temp_courses": [],
    # 上午（第一大节）没课时自动补一节自习
    "auto_study": True,
    # 用户手动删除的课程：[{date, name, secStart}]，系统课按"某天某节"隐藏
    "hidden_courses": [],
    # 我的班级（用于匹配导入文件里的行；留空则从教务系统抓到的班级自动填充）
    "class_name": "",
    # 已导入的自习/课表文件：[{path, source, week, slots:[{day,period,room}], matched}]
    "selfstudy_files": [],
    # 界面风格：normal 正常 / beautify 美化（液态玻璃）
    "ui_style": "normal",
    # 教务系统地址（形如 http://your.school.edu.cn/jsxsd），首次使用需填写
    "school_base": "",
    # 教室首位数字 → 楼名（各校区不同，按需填写；留空则不补楼名）
    "room_buildings": {},
    # 界面配色：强调色 + 背景三档渐变色
    "accent": "#0A84FF",
    "bg_top": "#eaf2ff",
    "bg_mid": "#e6ecff",
    "bg_bottom": "#eef0ff",
}

# 历史默认值 → 新默认值：仅在用户从未改过节次时间时自动升级
_LEGACY_PERIOD_TIMES = ["08:30-10:05", "10:25-12:00", "13:30-15:05",
                        "15:10-16:45", "16:50-18:25"]


# ---------------- DPAPI ----------------

class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wt.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_char))]


def dpapi_protect(data: bytes) -> bytes:
    buf = ctypes.create_string_buffer(data, len(data))
    blob_in = _DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = _DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out))
    if not ok:
        raise OSError("CryptProtectData failed")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def dpapi_unprotect(data: bytes) -> bytes:
    buf = ctypes.create_string_buffer(data, len(data))
    blob_in = _DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = _DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out))
    if not ok:
        raise OSError("CryptUnprotectData failed")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def encrypt_password(plain: str) -> str:
    return base64.b64encode(dpapi_protect(plain.encode("utf-8"))).decode("ascii")


def decrypt_password(enc: str) -> str:
    if not enc:
        return ""
    try:
        return dpapi_unprotect(base64.b64decode(enc)).decode("utf-8")
    except Exception:
        return ""


# ---------------- 配置文件 ----------------

def config_dir() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def config_path() -> str:
    return os.path.join(config_dir(), "config.json")


def load() -> dict:
    cfg = dict(DEFAULTS)
    try:
        with open(config_path(), "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    # 未自定义过节次时间的老配置：升级为新的默认时间
    if cfg.get("period_times") == _LEGACY_PERIOD_TIMES:
        cfg["period_times"] = list(DEFAULTS["period_times"])
    return cfg


def save(cfg: dict) -> None:
    with open(config_path(), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ---------------- 开机自启（注册表） ----------------

def _launch_command() -> str:
    if getattr(sys, "frozen", False):
        return '"%s"' % os.path.abspath(sys.executable)
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = sys.executable
    main_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
    return '"%s" "%s"' % (pythonw, main_py)


def set_autostart(enabled: bool) -> None:
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0, winreg.KEY_SET_VALUE)
    try:
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _launch_command())
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
    finally:
        winreg.CloseKey(key)
