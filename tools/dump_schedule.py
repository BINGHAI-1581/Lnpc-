# -*- coding: utf-8 -*-
"""把当前抓到的教务系统课表导出为 JSON 快照，供离线启动（--offline）做界面验证。

用法:
    python tools/dump_schedule.py [输出路径]
默认输出到 %TEMP%\\schedule_snapshot.json
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config
from app.school import SchoolClient


def main(argv):
    out = argv[0] if argv else os.path.join(tempfile.gettempdir(), "schedule_snapshot.json")
    cfg = config.load()
    client = SchoolClient()
    client.login(cfg["account"], config.decrypt_password(cfg["password_enc"]))
    courses = client.fetch_schedule()
    week = client.fetch_current_week()
    data = {
        "current_week": week,
        "class_name": "",
        "courses": [{
            "name": c.name, "teacher": c.teacher, "room": c.room, "building": c.building,
            "day": c.day, "weeks": sorted(c.weeks), "sec_start": c.sec_start,
            "sec_end": c.sec_end, "weeks_raw": c.weeks_raw, "klass": c.klass,
            "exam_type": c.exam_type,
        } for c in courses],
    }
    from collections import Counter
    klasses = Counter(c.klass for c in courses if c.klass)
    if klasses:
        data["class_name"] = klasses.most_common(1)[0][0]
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("已导出 %d 门课，当前第%s周 → %s" % (len(courses), week, out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
