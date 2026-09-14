# -*- coding: utf-8 -*-
"""停止本程序的所有实例并清掉单实例锁文件（调试/自动化测试前用）。

用法:
    python tools/stop_app.py
"""
import os
import pathlib
import subprocess
import sys
import time


def main():
    me = os.getpid()
    for exe in ("python.exe", "pythonw.exe"):
        # 注意排除自己：否则 taskkill /IM python.exe 会把正在执行本脚本的进程一起杀掉
        subprocess.run(["taskkill", "/F", "/IM", exe,
                        "/FI", "PID ne %d" % me],
                       capture_output=True, text=True,
                       encoding="gbk", errors="ignore")
    time.sleep(2.5)
    lock = pathlib.Path(os.environ["APPDATA"]) / "CoursePusher" / "app.lock"
    for _ in range(6):
        try:
            lock.unlink(missing_ok=True)
            break
        except OSError:
            time.sleep(1)
    time.sleep(0.5)
    left = 0
    for exe in ("python.exe", "pythonw.exe"):
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq " + exe, "/FO", "CSV"],
                             capture_output=True, text=True,
                             encoding="gbk", errors="ignore").stdout
        left += out.count(exe)
    print("剩余实例 %d，锁文件 %s" % (left, "已清除" if not lock.exists() else "仍在"))
    return 0 if left == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
