# -*- coding: utf-8 -*-
"""QML 后端：登录抓取、近七天数据、消息生成、微信发送、定时任务、托盘。"""
import datetime
import re
import sys
import threading
import traceback

from PySide6.QtCore import QObject, Signal, Slot, Property, QTimer, Qt
from PySide6.QtGui import QGuiApplication, QCursor, QPixmap, QColor, QPainter, QFont, QIcon

from . import config, formatting, importer, wechat
from .school import SchoolClient, SchoolError, next_seven_days


def _weekday_of(date_iso: str) -> int:
    try:
        return datetime.date.fromisoformat(date_iso).isoweekday()
    except Exception:
        return 0


def _period_label(sec: int) -> str:
    block = (int(sec) + 1) // 2
    return {1: "第1-2节", 2: "第3-4节", 3: "第5-6节",
            4: "第7-8节", 5: "第9-10节"}.get(block, "第%d节" % sec)


def _start_of(sec_start: int) -> int:
    """节次 → 该大节的起始分钟，用于和临时课程的时间文本比对。"""
    block = (int(sec_start) + 1) // 2 if sec_start else 0
    return {1: 8 * 60, 2: 10 * 60 + 25, 3: 13 * 60 + 30,
            4: 15 * 60 + 10, 5: 18 * 60}.get(block, -1)


def _dominant_class(courses) -> str:
    """从抓到的课程里统计出现最多的班级名。"""
    from collections import Counter
    names = [c.klass for c in courses if getattr(c, "klass", "")]
    return Counter(names).most_common(1)[0][0] if names else ""


def _week_from_name(name: str):
    """从文件名里取周次，如"第三周"→3、"第12周"→12，取不到返回 None。"""
    cn = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7,
          "八": 8, "九": 9, "十": 10}
    m = re.search(r"第\s*(\d{1,2})\s*周", name)
    if m:
        return int(m.group(1))
    m = re.search(r"第\s*([一二三四五六七八九十]{1,2})\s*周", name)
    if m:
        s = m.group(1)
        if len(s) == 1:
            return cn.get(s)
        if s.startswith("十"):
            return 10 + cn.get(s[1], 0)
        if s.endswith("十"):
            return cn.get(s[0], 0) * 10
        return cn.get(s[0], 0) * 10 + cn.get(s[2], 0) if len(s) == 3 else None
    return None


def _now_str() -> str:
    return datetime.datetime.now().strftime("%H:%M")


class Backend(QObject):
    # 后台线程 → 主线程
    loginDone = Signal(bool, str)      # 登录/刷新结果（用于提示条）
    sendDone = Signal(bool, str)       # 发送/复制/保存结果
    stateChanged = Signal()            # 所有状态属性的 notify
    previewChanged = Signal()          # days / previewText 变化

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.cfg = config.load()
        self.client = None
        self._courses = []          # 教务系统抓到的原始课程
        self._my_class = ""         # 从教务系统识别到的班级
        self._day_offset = 0        # 主页查看的日期偏移（前后几周）
        self._days = []
        self._logged_in = False
        self._login_state = "未登录"
        self._loading = False
        self._last_error = ""
        self._last_updated = ""
        self._current_week = 0
        self._preview = ""
        self._sending_state = ""
        self._busy = threading.Lock()

        self._timer = QTimer(self)
        self._timer.setInterval(20_000)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

        self._init_tray()

    # ---------------- 属性 ----------------

    @Property(str, notify=stateChanged)
    def account(self):
        return self.cfg.get("account", "")

    @Property(bool, notify=stateChanged)
    def loggedIn(self):
        return self._logged_in

    @Property(str, notify=stateChanged)
    def loginState(self):
        return self._login_state

    @Property(bool, notify=stateChanged)
    def loading(self):
        return self._loading

    @Property(str, notify=stateChanged)
    def lastError(self):
        return self._last_error

    @Property(str, notify=stateChanged)
    def lastUpdated(self):
        return self._last_updated

    @Property(int, notify=stateChanged)
    def currentWeek(self):
        return self._current_week

    @Property(str, notify=stateChanged)
    def sendingState(self):
        return self._sending_state

    @Property(bool, notify=stateChanged)
    def needsOnboarding(self):
        return not (self.cfg.get("account") and self.cfg.get("password_enc"))

    @Property("QVariantList", notify=previewChanged)
    def days(self):
        return self._days

    @Property(str, notify=previewChanged)
    def previewText(self):
        return self._preview

    @Property("QVariantMap", constant=True)
    def settings(self):
        s = {k: v for k, v in self.cfg.items() if k != "password_enc"}
        s["hasPassword"] = bool(self.cfg.get("password_enc"))
        return s

    # ---------------- 启动 ----------------

    @Slot()
    def startup(self):
        if self.cfg.get("account") and self.cfg.get("password_enc"):
            self.refresh()

    # ---------------- 登录 / 抓取 ----------------

    @Slot()
    def refresh(self):
        self._start_worker(self._do_refresh)

    @Slot(str, str)
    def saveLogin(self, account, password):
        account = account.strip()
        if not account:
            self.loginDone.emit(False, "学号不能为空")
            return
        self.cfg["account"] = account
        if password:
            self.cfg["password_enc"] = config.encrypt_password(password)
        config.save(self.cfg)
        self._start_worker(self._do_refresh)

    @Slot(str, str)
    def testLogin(self, account, password):
        """测试连接：临时账号密码不落盘；密码传 __SAVED__ 表示用已保存的密码。"""
        if password == "__SAVED__":
            password = ""
        self._start_worker(self._do_refresh, account.strip(), password or None)

    def _do_refresh(self, account=None, password=None):
        account = account or self.cfg.get("account", "")
        password = password or config.decrypt_password(self.cfg.get("password_enc", ""))
        if not account or not password:
            self._set_state(loading=True, login_state="待配置")
            self.loginDone.emit(False, "请先填写学号与密码")
            return
        self._set_state(loading=True, login_state="正在登录教务系统…", last_error="")
        client = SchoolClient()
        try:
            client.login(account, password)
            courses = client.fetch_schedule()
            week = client.fetch_current_week()
        except SchoolError as e:
            self._set_state(loading=False, login_state="登录失败", last_error=str(e))
            self.loginDone.emit(False, str(e))
            return
        except Exception as e:
            traceback.print_exc()
            msg = "网络异常：%s" % e
            self._set_state(loading=False, login_state="登录失败", last_error=msg)
            self.loginDone.emit(False, msg)
            return
        self.client = client
        self._courses = courses
        self._my_class = _dominant_class(courses)
        self._current_week = week or 0
        self._logged_in = True
        self._set_state(loading=False, login_state="已登录",
                        last_error="", last_updated=_now_str())
        self._recompute_days()
        self.loginDone.emit(True, "课表已更新 · 共 %d 门课 · %s" % (len(courses), _now_str()))

    def _selfstudy_slots(self):
        """把已导入文件的安排摊平成 [{week, day, period, room}]。"""
        slots = []
        for f in self.cfg.get("selfstudy_files") or []:
            week = f.get("week")
            for s in f.get("slots") or []:
                slots.append({"week": week, "day": s.get("day"),
                              "period": s.get("period"), "room": s.get("room")})
        return slots

    def _recompute_days(self):
        """由原始课程 + 临时课程 + 导入的自习安排重算近七天视图与消息预览。"""
        self._days = next_seven_days(
            self._courses, self._current_week,
            temp_courses=self.cfg.get("temp_courses") or [],
            auto_study=bool(self.cfg.get("auto_study", True)),
            hidden=self.cfg.get("hidden_courses") or [],
            period_times=self.cfg.get("period_times"),
            selfstudy=self._selfstudy_slots(),
            day_offset=self._day_offset,
            moves=self.cfg.get("course_moves") or [])
        self._rebuild_preview()

    def _set_state(self, **kw):
        for k, v in kw.items():
            setattr(self, "_" + k, v)
        self.stateChanged.emit()

    def _start_worker(self, fn, *args):
        if not self._busy.acquire(blocking=False):
            self.loginDone.emit(False, "正在处理上一个任务，请稍候")
            return
        threading.Thread(target=self._run_worker, args=(fn, args), daemon=True).start()

    def _run_worker(self, fn, args):
        try:
            fn(*args)
        except Exception:
            traceback.print_exc()
        finally:
            self._busy.release()

    # ---------------- 设置 ----------------

    @Slot("QVariantMap")
    def saveSettings(self, qmap):
        for k in ("send_mode", "send_target", "scope", "style", "wechat_path"):
            if k in qmap:
                self.cfg[k] = str(qmap[k])
        if "auto_study" in qmap:
            self.cfg["auto_study"] = bool(qmap["auto_study"])
        if "school_base" in qmap:
            self.cfg["school_base"] = str(qmap["school_base"]).strip()
        if "class_name" in qmap:
            self.cfg["class_name"] = str(qmap["class_name"]).strip()
        if "ui_style" in qmap:
            self.cfg["ui_style"] = str(qmap["ui_style"])
        for k in ("send_hour", "send_minute"):
            if k in qmap:
                try:
                    self.cfg[k] = int(qmap[k])
                except (TypeError, ValueError):
                    pass
        if "autostart" in qmap:
            enabled = bool(qmap["autostart"])
            self.cfg["autostart"] = enabled
            try:
                config.set_autostart(enabled)
            except Exception as e:
                self.sendDone.emit(False, "开机自启设置失败：%s" % e)
                return
        config.save(self.cfg)
        self._rebuild_preview()
        self.sendDone.emit(True, "设置已保存")

    def _rebuild_preview(self):
        if not self._days:
            self._preview = "（登录成功后自动生成预览）"
        else:
            self._preview = formatting.build_message(
                self._days, self.cfg.get("scope", "today"),
                self.cfg.get("style", "detailed"), self.cfg.get("emoji", True),
                self.cfg.get("period_times"))
        self.previewChanged.emit()

    @Slot(str, result=str)
    def loadOffline(self, path):
        """从快照加载课表（离线调试用，不访问教务系统）。"""
        import json as _json
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = _json.load(f)
        except Exception as e:
            return "快照读取失败：%s" % e
        from .school import Course, clean_course_name
        self._courses = [
            Course(clean_course_name(c["name"]), c.get("teacher", ""), c.get("room", ""),
                   c.get("building", ""), int(c["day"]), set(c.get("weeks") or []),
                   int(c.get("sec_start") or 0), int(c.get("sec_end") or 0),
                   c.get("weeks_raw", ""), c.get("klass", ""), c.get("exam_type", ""))
            for c in data.get("courses", [])
        ]
        self._my_class = data.get("class_name", "")
        self._current_week = int(data.get("current_week") or 0)
        self._logged_in = True
        self._set_state(loading=False, login_state="离线快照",
                        last_error="", last_updated=_now_str())
        self._recompute_days()
        print("[offline] 载入 %d 门课，第%s周" % (len(self._courses), self._current_week),
              file=sys.stderr, flush=True)
        return "已载入离线快照：%d 门课" % len(self._courses)

    # ---------------- 主页周次导航 ----------------

    @Property(int, notify=stateChanged)
    def dayOffset(self):
        return self._day_offset

    @Property(str, notify=stateChanged)
    def viewLabel(self):
        """当前视图的日期区间与周次，例如 9月14日 – 9月20日 · 第3周。"""
        if not self._days:
            return ""
        first, last = self._days[0], self._days[-1]
        span = "%s – %s" % (first["dateLabel"], last["dateLabel"])
        weeks = sorted({d["weekNum"] for d in self._days if d.get("weekNum")})
        if weeks:
            span += " · 第%s周" % ("、".join(str(w) for w in weeks))
        if self._day_offset == 0:
            span += " · 本周"
        elif self._day_offset == 7:
            span += " · 下周"
        elif self._day_offset == -7:
            span += " · 上周"
        return span

    @Property(str, notify=stateChanged)
    def uiStyle(self):
        return self.cfg.get("ui_style", "normal")

    @Property(str, notify=stateChanged)
    def accent(self):
        return self.cfg.get("accent", "#0A84FF")

    @Property(str, notify=stateChanged)
    def bgTop(self):
        return self.cfg.get("bg_top", "#eaf2ff")

    @Property(str, notify=stateChanged)
    def bgMid(self):
        return self.cfg.get("bg_mid", "#e6ecff")

    @Property(str, notify=stateChanged)
    def bgBottom(self):
        return self.cfg.get("bg_bottom", "#eef0ff")

    @Property("QVariantMap", constant=True)
    def theme(self):
        """给 QML 读的配色表（含强调色的半透明变体）。"""
        from PySide6.QtGui import QColor
        a = QColor(self.accent)
        # 注意：这里只给数值分量。QML 的 color 类型不认识 CSS 的 "rgba(...)" 字符串，
        # 直接赋字符串会静默退回默认黑色（曾导致今日卡片出现黑边）。
        return {
            "accent": self.accent,
            "r": a.redF(), "g": a.greenF(), "b": a.blueF(),
            "accentDark": "#%02x%02x%02x" % (max(0, int(a.red() * 0.62)),
                                             max(0, int(a.green() * 0.62)),
                                             max(0, int(a.blue() * 0.62))),
            "bgTop": self.bgTop, "bgMid": self.bgMid, "bgBottom": self.bgBottom,
        }

    @Slot(str, str, str, str)
    def saveTheme(self, accent, bg_top, bg_mid, bg_bottom):
        if accent:
            self.cfg["accent"] = accent
        if bg_top and bg_mid and bg_bottom:
            self.cfg["bg_top"] = bg_top
            self.cfg["bg_mid"] = bg_mid
            self.cfg["bg_bottom"] = bg_bottom
        config.save(self.cfg)
        self.stateChanged.emit()
        self.sendDone.emit(True, "已更新配色")

    @Property(bool, notify=stateChanged)
    def fancyUi(self):
        return self.cfg.get("ui_style", "normal") == "beautify"

    @Property(str, notify=stateChanged)
    def viewTitle(self):
        """主页大标题：本周显示"近七天课程"，其它周显示"第N周课程"。"""
        if not self._days:
            return "近七天课程"
        if self._day_offset == 0:
            return "近七天课程"
        weeks = sorted({d["weekNum"] for d in self._days if d.get("weekNum")})
        if not weeks:
            return "课程安排"
        if len(weeks) == 1:
            return "第%d周课程" % weeks[0]
        return "第%d–%d周课程" % (weeks[0], weeks[-1])

    @Slot(int)
    def shiftView(self, delta_days):
        """按天平移主页视图（按周查看时传 ±7 的倍数）。"""
        self._day_offset = max(-70, min(70, self._day_offset + int(delta_days)))
        self._recompute_days()
        self.stateChanged.emit()

    @Slot()
    def resetView(self):
        self._day_offset = 0
        self._recompute_days()
        self.stateChanged.emit()

    # ---------------- 班级 / 文件导入 ----------------

    @Property(str, notify=stateChanged)
    def myClass(self):
        """优先用设置里手填的班级，否则用教务系统抓到的班级。"""
        return self.cfg.get("class_name") or self._my_class

    @Property(str, notify=stateChanged)
    def detectedClass(self):
        return self._my_class

    @Property("QVariantList", notify=stateChanged)
    def importedFiles(self):
        return self.cfg.get("selfstudy_files") or []

    @Slot()
    def pickAndImportFile(self):
        """弹出文件选择框，解析学校发来的自习/课表文件并匹配本班安排。"""
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            None, "选择课表/自习安排文件", "",
            "表格或文档 (*.xlsx *.xlsm *.docx);;所有文件 (*)")
        if not path:
            return
        self.importFile(path)

    @Slot(str, result=str)
    def importFile(self, path):
        try:
            parsed = importer.parse_file(path)
        except Exception as e:
            msg = "解析失败：%s" % e
            self.sendDone.emit(False, msg)
            return msg

        target = self.myClass
        if not target:
            msg = "还没识别到你的班级，请先在下方填写班级名称"
            self.sendDone.emit(False, msg)
            return msg

        slots, exact = importer.slots_for_class(parsed, target)
        print("[import] 文件=%s 基准大节=%s 班级=%s 匹配=%s 安排=%s"
              % (parsed["source"], parsed.get("base_period"), target, exact,
                 [(x["day"], x["period"], x["room"]) for x in slots]),
              file=sys.stderr, flush=True)
        week = _week_from_name(parsed["source"]) or self._current_week or None
        record = {
            "path": path,
            "source": parsed["source"],
            "week": week,
            "class": target,
            "matched": exact,
            "slots": [{"day": s["day"], "period": s["period"], "room": s["room"]}
                      for s in slots],
            "classes": parsed["classes"],
        }
        items = [f for f in (self.cfg.get("selfstudy_files") or [])
                 if f.get("source") != parsed["source"]]
        items.append(record)
        self.cfg["selfstudy_files"] = items[-20:]
        config.save(self.cfg)
        self.stateChanged.emit()
        self._recompute_days()

        if not slots:
            msg = "已导入《%s》，但没有找到「%s」的安排（文件里有 %d 个班级）" % (
                parsed["source"], target, len(parsed["classes"]))
        else:
            detail = "、".join("周%s第%d大节 %s" % ("一二三四五六日"[s["day"] - 1],
                                              s["period"], s["room"])
                              for s in record["slots"][:4])
            msg = "已导入《%s》%s：%s" % (parsed["source"],
                                        "第%d周" % week if week else "",
                                        detail)
        self.sendDone.emit(True, msg)
        return msg

    @Slot(str, str, int, result=str)
    def importText(self, text, title, week):
        """解析手动输入/粘贴的安排描述，并入课表。"""
        items = importer.parse_text(text)
        if not items:
            msg = "没有解析出可用安排，请写成「周二 一二节 3614」或「周三 3-4节 高等数学 求真楼1117」这样的形式"
            self.sendDone.emit(False, msg)
            return msg
        room = ""
        slots = [{"day": it["day"], "period": it["period"],
                  "room": importer.expand_room(it["room"]) if hasattr(importer, "expand_room")
                          else it["room"],
                  "name": it["name"], "timeText": it["timeText"]}
                 for it in items]
        # 教室楼名规则统一走 school.expand_room
        from .school import expand_room
        for sl in slots:
            sl["room"] = expand_room(sl["room"])
        record = {
            "path": "",
            "source": (title or "手动描述").strip(),
            "week": int(week) if week else (self._current_week or None),
            "class": self.myClass,
            "matched": True,
            "slots": slots,
            "classes": [],
            "manual": True,
        }
        items_list = [f for f in (self.cfg.get("selfstudy_files") or [])
                      if f.get("source") != record["source"]]
        items_list.append(record)
        self.cfg["selfstudy_files"] = items_list[-20:]
        config.save(self.cfg)
        self.stateChanged.emit()
        self._recompute_days()
        detail = "、".join("周%s %s %s" % ("一二三四五六日"[sl["day"] - 1],
                                        sl.get("name") or "自习",
                                        sl["room"] or "教室待定")
                         for sl in slots[:4])
        msg = "已解析 %d 条：%s%s" % (len(slots), detail,
                                     " …" if len(slots) > 4 else "")
        self.sendDone.emit(True, msg)
        return msg

    @Slot(int)
    def removeImportedFile(self, index):
        items = list(self.cfg.get("selfstudy_files") or [])
        if 0 <= index < len(items):
            name = items.pop(index).get("source", "")
            self.cfg["selfstudy_files"] = items
            config.save(self.cfg)
            self.stateChanged.emit()
            self._recompute_days()
            self.sendDone.emit(True, "已移除《%s》" % name)

    # ---------------- 临时课程 ----------------

    @Property("QVariantList", notify=stateChanged)
    def tempCourses(self):
        return self.cfg.get("temp_courses") or []

    @Property("QVariantList", notify=stateChanged)
    def periodTimes(self):
        return self.cfg.get("period_times") or formatting.DEFAULT_PERIOD_TIMES

    @Slot("QVariantMap", result=bool)
    def addTempCourse(self, qmap):
        name = str(qmap.get("name", "")).strip()
        if not name:
            self.sendDone.emit(False, "请填写课程名称")
            return False
        item = {
            "name": name,
            "teacher": str(qmap.get("teacher", "")).strip(),
            "day": int(qmap.get("day") or 1),
            "time": str(qmap.get("time", "")).strip(),
            "room": str(qmap.get("room", "")).strip(),
            "weeks": str(qmap.get("weeks", "")).strip(),
        }
        items = list(self.cfg.get("temp_courses") or [])
        items.append(item)
        self.cfg["temp_courses"] = items
        config.save(self.cfg)
        self.stateChanged.emit()
        self._recompute_days()
        self.sendDone.emit(True, "已添加临时课程「%s」" % name)
        return True

    @Slot(int)
    def removeTempCourse(self, index):
        items = list(self.cfg.get("temp_courses") or [])
        if 0 <= index < len(items):
            removed = items.pop(index)["name"]
            self.cfg["temp_courses"] = items
            config.save(self.cfg)
            self.stateChanged.emit()
            self._recompute_days()
            self.sendDone.emit(True, "已删除「%s」" % removed)

    @Slot(str, str, int, int)
    def moveCourse(self, date, name, from_sec, to_sec):
        """把某天的某门课移动到另一个大节（时间随之变化）。

        临时课程/自习直接改存储值；教务系统课程记入 moves 覆盖表（按天生效）。
        """
        from_sec, to_sec = int(from_sec or 0), int(to_sec or 0)
        if from_sec == to_sec:
            return
        # 临时课程：直接改它的时间
        items = list(self.cfg.get("temp_courses") or [])
        changed = False
        for t in items:
            m = re.match(r"(\d{1,2})[:：](\d{2})", (t.get("time") or ""))
            same_day = t.get("name") == name and _weekday_of(date) == (t.get("day") or 0)
            if same_day and (not m or _start_of(from_sec) == int(m.group(1)) * 60 + int(m.group(2))):
                times = self.cfg.get("period_times") or []
                block = (to_sec + 1) // 2
                if 1 <= block <= len(times):
                    t["time"] = times[block - 1]
                    changed = True
                break
        if changed:
            self.cfg["temp_courses"] = items
        else:
            moves = [m for m in (self.cfg.get("course_moves") or [])
                     if not (m.get("date") == date and m.get("name") == name
                             and int(m.get("fromSec") or 0) == from_sec)]
            moves.append({"date": date, "name": name,
                          "fromSec": from_sec, "toSec": to_sec})
            self.cfg["course_moves"] = moves[-300:]
        config.save(self.cfg)
        self.stateChanged.emit()
        self._recompute_days()
        self.sendDone.emit(True, "已把「%s」移到%s" % (name, _period_label(to_sec)))

    @Slot(str, str, int)
    def deleteCourse(self, date, name, sec_start):
        """删除某天的某门课。

        临时课程直接删除；教务系统课程按"日期+课程名+节次"隐藏（刷新后依然隐藏）；
       自动补出的自习同样记入隐藏列表，否则重算时会被再次补上。
        """
        sec = int(sec_start or 0)
        items = list(self.cfg.get("temp_courses") or [])
        removed_temp = False
        for i, t in enumerate(items):
            if t.get("name") == name and (t.get("day") or 0) == _weekday_of(date):
                m = re.match(r"(\d{1,2})[:：](\d{2})", (t.get("time") or ""))
                if not m or (int(m.group(1)) * 60 + int(m.group(2))) == _start_of(sec):
                    items.pop(i)
                    removed_temp = True
                    break
        if removed_temp:
            self.cfg["temp_courses"] = items
        else:
            hidden = [h for h in (self.cfg.get("hidden_courses") or [])
                      if not (h.get("date") == date and h.get("name") == name
                              and int(h.get("secStart") or 0) == sec)]
            hidden.append({"date": date, "name": name, "secStart": sec})
            self.cfg["hidden_courses"] = hidden[-200:]
        config.save(self.cfg)
        self.stateChanged.emit()
        self._recompute_days()
        self.sendDone.emit(True, "已删除「%s」" % name)

    @Slot("QVariantList")
    def savePeriodTimes(self, qlist):
        times = [str(t).strip() for t in qlist]
        if len(times) == 5 and all(times):
            self.cfg["period_times"] = times
            config.save(self.cfg)
            self.stateChanged.emit()
            self._rebuild_preview()
            self.sendDone.emit(True, "节次时间已保存")

    # ---------------- 发送 ----------------

    @Slot()
    def copyPreview(self):
        QGuiApplication.clipboard().setText(self._preview)
        self._set_state(sending_state="已复制到剪贴板")
        self.sendDone.emit(True, "已复制到剪贴板")

    @Slot()
    def sendNow(self):
        self._send_to(self.cfg.get("send_target", "文件传输助手"))

    @Slot()
    def sendTest(self):
        self._send_to("文件传输助手")

    def _send_to(self, target):
        if not self._days:
            self._set_state(sending_state="")
            self.sendDone.emit(False, "还没有课表数据，请先刷新")
            return
        text = formatting.build_message(
            self._days, self.cfg.get("scope", "today"),
            self.cfg.get("style", "detailed"), self.cfg.get("emoji", True),
            self.cfg.get("period_times"))
        self._set_state(sending_state="正在通过微信发送…")

        def job():
            try:
                wechat.send_text(target, text, self.cfg.get("wechat_path", ""))
                self._set_state(sending_state="已发送至「%s」· %s" % (target, _now_str()))
                self.sendDone.emit(True, "已发送至「%s」" % target)
            except Exception as e:
                self._set_state(sending_state="发送失败")
                self.sendDone.emit(False, str(e))
        threading.Thread(target=job, daemon=True).start()

    # ---------------- 定时任务 ----------------

    def _tick(self):
        if self.cfg.get("send_mode") != "scheduled":
            return
        now = datetime.datetime.now()
        target_min = int(self.cfg.get("send_hour", 7)) * 60 + int(self.cfg.get("send_minute", 30))
        if (now.hour * 60 + now.minute) < target_min:
            return
        today = now.date().isoformat()
        if self.cfg.get("last_sent_date") == today:
            return
        if not (self.cfg.get("account") and self.cfg.get("password_enc")):
            return
        # 先占坑再发送，防止 20 秒心跳内重复触发
        self.cfg["last_sent_date"] = today
        config.save(self.cfg)

        def job():
            self._do_refresh()
            if self._logged_in:
                self._send_to(self.cfg.get("send_target", "文件传输助手"))
        threading.Thread(target=job, daemon=True).start()

    # ---------------- 窗口 / 托盘 ----------------

    @Slot(result="QVariantMap")
    def cursorPos(self):
        """全局光标位置，供无边框窗口的边缘缩放计算使用。"""
        p = QCursor.pos()
        return {"x": p.x(), "y": p.y()}

    @Property("QVariantMap", constant=True)
    def windowGeometry(self):
        """上次退出时的窗口位置与大小，无记录时返回空表。"""
        g = self.cfg.get("window") or {}
        return g if isinstance(g, dict) else {}

    @Slot(int, int, int, int)
    def saveWindowGeometry(self, x, y, w, h):
        if w < 400 or h < 300:
            return
        self.cfg["window"] = {"x": int(x), "y": int(y), "w": int(w), "h": int(h)}
        config.save(self.cfg)

    @Slot()
    def hideWindow(self):
        from PySide6.QtWidgets import QSystemTrayIcon
        for w in self.app.allWindows():
            w.hide()
        self._tray.showMessage("课程推送助手", "已最小化到托盘，定时发送继续运行",
                               QSystemTrayIcon.Information, 3000)

    @Slot()
    def showWindow(self):
        for w in self.app.allWindows():
            w.showNormal()
            w.raise_()
            w.requestActivate()

    def _init_tray(self):
        from PySide6.QtWidgets import QSystemTrayIcon, QMenu
        self._tray = QSystemTrayIcon(self._make_icon(), self)
        self._tray.setToolTip("课程推送助手")
        menu = QMenu()
        menu.addAction("显示主窗口", self.showWindow)
        menu.addAction("立即发送", self.sendNow)
        menu.addSeparator()
        menu.addAction("退出", self.app.quit)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(
            lambda reason: self.showWindow() if reason == QSystemTrayIcon.DoubleClick else None)
        self._tray.show()

    @staticmethod
    def _make_icon() -> QIcon:
        pm = QPixmap(64, 64)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor("#5B8CFF"))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(2, 2, 60, 60, 16, 16)
        p.setPen(QColor("white"))
        p.setFont(QFont("Microsoft YaHei UI", 30, QFont.Bold))
        p.drawText(pm.rect(), Qt.AlignCenter, "课")
        p.end()
        return QIcon(pm)
