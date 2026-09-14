# -*- coding: utf-8 -*-
"""强智教务系统 (jsxsd) 客户端：登录、抓取整学期课表、获取当前周次。

协议要点（以强智 jsxsd 系统为例）：
1. 登录 POST /jsxsd/xk/LoginToXk
   表单: userAccount=学号, userPassword=(留空), loginMethod=LoginToXk,
          encoded = base64(学号) + "%%%" + base64(密码)   （JS encodeInp，分开编码）
2. 课表 GET /jsxsd/xskb/xskb_list.do   默认返回整学期课表
   单元格为 <div id="{行GUID}-{星期1-7}-{视图}" class="kbcontent">
   （class="kbcontent1" 为摘要变体，忽略），单元格内多门课以 5 个以上连字符分隔；
   字段取 <font title="教师"/周次(节次)/教室> 与无 title 的课程名。
   周次形如 "1-4,7-9,13-18(周)"，节次形如 "[01-02节]"。
3. 当前周 GET /jsxsd/framework/xsMainV_new.htmlx，正文含 "第N周"。
"""
import base64
import datetime
import os
import re
import time

import requests
from bs4 import BeautifulSoup

def school_base() -> str:
    """教务系统地址（形如 http://your.school.edu.cn/jsxsd），从配置读取。

    各校地址不同，因此不写死在代码里；留空时登录会给出明确提示。
    """
    from . import config as _config
    base = (_config.load().get("school_base") or "").strip().rstrip("/")
    if base and not base.startswith(("http://", "https://")):
        base = "http://" + base
    return base


def room_buildings() -> dict:
    """教室首位数字 → 楼名 的映射（各校区不同，默认空表示不补楼名）。"""
    from . import config as _config
    m = _config.load().get("room_buildings") or {}
    return {str(k): str(v) for k, v in m.items()} if isinstance(m, dict) else {}


WEEKDAY_CN = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日"}

_ROOM_BARE = re.compile(r"^(\d{4})$")


def expand_room(text: str) -> str:
    """教室若只写四位数字，按首位数字补上楼名：1 求真楼 / 2 求善楼 / 3 求美楼。

    只处理"纯四位数字"的表达，其它写法（已带楼名、含括号教室等）原样返回。
    """
    room = (text or "").strip()
    if not _ROOM_BARE.match(room):
        return room
    # 四位教室号统一写成带括号的形式：3614 → 求美楼（3614）
    inner = "（%s）" % room
    building = room_buildings().get(room[0])
    return (building + inner) if building else inner

_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
}


class SchoolError(Exception):
    pass


def _js_base64(s: str) -> str:
    """与页面 conwork.js 中 encodeInp 等价（按 charCodeAt 字节做 base64）。"""
    return base64.b64encode(s.encode("latin-1", "replace")).decode("ascii")


class Course:
    __slots__ = ("name", "teacher", "room", "building", "day", "weeks",
                 "sec_start", "sec_end", "weeks_raw", "klass", "exam_type", "hours")

    def __init__(self, name, teacher, room, building, day, weeks,
                 sec_start, sec_end, weeks_raw, klass="", exam_type="", hours=""):
        self.name = name
        self.teacher = teacher
        self.room = room              # 教室，如 "大教室十（2415）"
        self.building = building      # 教学楼，如 "求善楼"，可能为空
        self.day = day                # 1=周一 ... 7=周日
        self.weeks = weeks            # set[int]
        self.sec_start = sec_start    # 节次，0 表示未知
        self.sec_end = sec_end
        self.weeks_raw = weeks_raw    # 原始周次文本，用于展示
        self.klass = klass            # 上课班级，用于匹配导入的课表文件
        self.exam_type = exam_type    # 考试 / 考查 / 实训
        self.hours = hours            # 学时构成，如 "理论:56" / "整周实训:26"

    @property
    def sec_text(self) -> str:
        if self.sec_start and self.sec_end:
            return "第%d-%d节" % (self.sec_start, self.sec_end)
        if self.sec_start:
            return "第%d节" % self.sec_start
        return "时间见课表"

    # 教务系统会用这些占位串表示"没有填"
    _PLACEHOLDER = ("未定义", "暂无", "无", "-")

    @classmethod
    def _clean_building(cls, text: str) -> str:
        text = (text or "").strip().strip("【】")
        if not text or any(p in text for p in cls._PLACEHOLDER):
            return ""
        return text

    @property
    def room_text(self) -> str:
        """完整教室文本：教学楼 + 教室；缺失时为「未定义教室」。

        教学楼为占位串（如"未定义教学楼"）时忽略；教室已含楼名时不重复拼接。
        """
        building = self._clean_building(self.building)
        room = (self.room or "").strip()
        if building and room:
            if _ROOM_BARE.match(room):
                return building + "（%s）" % room          # 2321 + 求善楼 → 求善楼（2321）
            text = room if building in room else building + room
        elif room:
            text = expand_room(room)          # 只写四位数字时按首位补楼名
        else:
            return building or "未定义教室"
        # 末尾若是裸露的四位数字，补上括号：求善楼2308 → 求善楼（2308）
        # 末尾若是裸露的四位数字，补上括号：求善楼2308 → 求善楼（2308）
        if len(text) >= 4 and text[-4:].isdigit() and not text.endswith("）"):
            text = text[:-4] + "（" + text[-4:] + "）"
        return text

    def key(self):
        return (self.name, self.day, self.teacher, self.room, self.sec_start, self.sec_end)


# 考核类型：实训 → 以课程名/学时为据；其余按教务系统的"考核方式"
EXAM_COLORS = {"考试": "#FF3B30", "考查": "#FFCC00", "实训": "#34C759", "其它": "#8E8E93"}


# 括号里是"一二三 / 上下 / 数字"这类序号时保留，其余（如项目名"排球"）视为后缀
_SERIAL_GROUP = re.compile(r"^[（(]\s*([一二三四五六七八九十]{1,2}|\d{1,2}|上|下)\s*[）)]$")


def clean_course_name(name: str) -> str:
    """体育类课程只保留课名，去掉后面跟的运动名称。

    例：体育健康教育(三)(排球) → 体育健康教育(三)；体育(篮球) → 体育。
    非体育课程、以及括号里是序号的（如 创新创业教育（一））都不动。
    """
    text = (name or "").strip()
    if not text or "体育" not in text:
        return text
    while True:
        m = re.search(r"[（(]([^（）()]{1,12})[）)]\s*$", text)
        if not m or _SERIAL_GROUP.match(m.group(0)):
            break
        text = text[:m.start()].strip()
    return text or name


def classify_exam(name: str, exam_way: str, xsks: str = "") -> str:
    """判断课程属于 考试 / 考查 / 实训。"""
    text = "%s%s" % (name or "", xsks or "")
    if any(k in text for k in ("实训", "实习", "课程设计")):
        return "实训"
    if "考试" in (exam_way or ""):
        return "考试"
    if "考查" in (exam_way or ""):
        return "考查"
    return "其它"


def parse_weeks(text: str) -> set:
    """解析 "1-4,7-9,13-18(周)(单)" / "5(周)" 等格式为周次集合。"""
    weeks = set()
    parity = None
    if re.search(r"单", text):
        parity = 1
    elif re.search(r"双", text):
        parity = 0
    body = re.sub(r"[（(]周[）)]|[（(]单[）)]|[（(]双[）)]|周", " ", text)
    for part in re.split(r"[,，;；\s]+", body):
        part = part.strip()
        m = re.fullmatch(r"(\d+)-(\d+)", part)
        if m:
            weeks.update(range(int(m.group(1)), int(m.group(2)) + 1))
        elif part.isdigit():
            weeks.add(int(part))
    if parity == 1:
        weeks = {w for w in weeks if w % 2 == 1}
    elif parity == 0:
        weeks = {w for w in weeks if w % 2 == 0}
    return weeks


def _dump_bad_page(resp, html: str) -> None:
    """把异常响应落盘，便于排查教务系统的偶发返回。"""
    try:
        import tempfile
        path = os.path.join(tempfile.gettempdir(), "bad_schedule.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write("<!-- resp=%s url=%s len=%d -->\n"
                    % (resp.status_code, resp.url, len(html)))
            f.write(html)
    except Exception:
        pass


class SchoolClient:
    def __init__(self, timeout=15, base=None):
        self.timeout = timeout
        self.base = (base or school_base()).rstrip("/")
        self.http = requests.Session()
        self.http.headers.update({"User-Agent": _HEADERS["User-Agent"],
                                  "Referer": (self.base + "/") if self.base else ""})
        self.courses = []
        self.week = None        # 当前教学周
        self.xnxq = ""          # 当前学期，如 2026-2027-1
        self._account = ""
        self._password = ""

    # ---------- 登录 ----------

    TRANSIENT = "__TRANSIENT__"

    def login(self, account: str, password: str, retries: int = 3) -> None:
        """登录。教务系统偶发不建立会话（短时间反复登录可能被限流），此处退避重试。"""
        if not self.base:
            raise SchoolError("还没有填写教务系统地址，请在「设置 → 登录信息」里填写后重试")
        self._account, self._password = account, password
        delays = [1.2, 2.5, 4.0]
        for attempt in range(retries):
            try:
                self._do_login()
                return
            except SchoolError as e:
                if str(e) != self.TRANSIENT:
                    raise                       # 账号密码错误等，直接抛出
                if attempt == retries - 1:
                    raise SchoolError(
                        "教务系统没有建立会话（可能登录过于频繁被限制）。"
                        "请稍后重试；若一直失败，请核对学号与密码。")
                time.sleep(delays[min(attempt, len(delays) - 1)])

    def _do_login(self) -> None:
        try:
            self.http.get(self.base + "/", timeout=self.timeout)
            self.http.post(
                self.base + "/xk/LoginToXk",
                data={
                    "userAccount": self._account,
                    "userPassword": "",
                    "encoded": _js_base64(self._account) + "%%%" + _js_base64(self._password),
                    "loginMethod": "LoginToXk",
                },
                timeout=self.timeout,
                allow_redirects=True,
            )
        except requests.RequestException as e:
            raise SchoolError("无法连接教务系统：%s" % e)

        html = self._schedule_html(retry=False)
        if "kbcontent" in html:
            return
        # 仍是登录表单：只有能识别出账号/密码类提示才算凭据错误，否则按"未建立会话"重试
        msg = self._login_error(html)
        if msg and any(k in msg for k in ("密码", "账号", "用户", "不存在")):
            raise SchoolError(msg)
        raise SchoolError(self.TRANSIENT)

    @staticmethod
    def _login_error(html: str) -> str:
        m = re.search(r'id="showMsg"[^>]*>\s*([^<]{2,60})', html)
        return m.group(1).strip() if m else ""

    # ---------- 课表 ----------

    def _schedule_html(self, retry: bool = True, attempts: int = 3) -> str:
        """取课表页 HTML；失败时重试，必要时自动重新登录。"""
        last = "未知错误"
        for i in range(attempts):
            try:
                resp = self.http.get(self.base + "/xskb/xskb_list.do",
                                     timeout=self.timeout)
                html = resp.text
            except requests.RequestException as e:
                last = str(e)
                time.sleep(0.6)
                continue
            if "kbcontent" in html:
                return html
            last = "会话可能已失效"
            _dump_bad_page(resp, html)
            if not retry:
                return html
            time.sleep(0.6)
            if i == attempts - 2 and self._account:
                try:
                    self._do_login()
                except SchoolError as e:
                    last = str(e)
        raise SchoolError("获取课表失败（%s），请稍后重试" % last)

    def fetch_schedule(self) -> list:
        html = self._schedule_html()
        soup = BeautifulSoup(html, "html.parser")
        courses, seen = [], set()
        for div in soup.find_all("div", class_="kbcontent"):
            classes = div.get("class") or []
            if "kbcontent1" in classes:
                continue
            m = re.fullmatch(r"([A-F0-9]{8,})-(\d)-(\d+)", div.get("id", ""))
            if not m:
                continue
            day = int(m.group(2))
            if not 1 <= day <= 7:
                continue
            inner = div.decode_contents()
            for chunk in re.split(r"-{5,}", inner):
                fragment = BeautifulSoup("<div>%s</div>" % chunk, "html.parser")
                name = teacher = wksec = room = building = klass = ""
                exam_way = xsks = ""
                for font in fragment.find_all("font"):
                    title = (font.get("title") or "").strip()
                    tag_name = (font.get("name") or "").strip()
                    text = font.get_text(strip=True)
                    if not text:
                        continue
                    if title == "教师":
                        teacher = text
                    elif title == "周次(节次)":
                        wksec = text
                    elif title == "教室":
                        room = text
                    elif title == "教学楼" or tag_name == "jxlmc":
                        building = text.strip("【】")
                    elif title == "考核方式":
                        exam_way = text.replace("考核方式：", "").replace("考核方式:", "").strip()
                    elif tag_name == "xsks":
                        xsks = text
                    elif tag_name == "ktmcstr" or title == "班级":
                        klass = text.replace("班级：", "").replace("班级:", "").strip()
                    elif not title and not name:
                        name = text
                if not name:
                    continue
                sec_start = sec_end = 0
                ms = re.search(r"\[(\d+)-(\d+)节\]", wksec)
                if ms:
                    sec_start, sec_end = int(ms.group(1)), int(ms.group(2))
                else:
                    ms = re.search(r"\[(\d+)节\]", wksec)
                    if ms:
                        sec_start = sec_end = int(ms.group(1))
                weeks_raw = re.sub(r"\[[^\]]*\]", "", wksec).strip(" (周)（）")
                course = Course(clean_course_name(name), teacher, room, building, day,
                                parse_weeks(wksec) or {0}, sec_start, sec_end, weeks_raw,
                                klass, classify_exam(name, exam_way, xsks), xsks)
                if course.key() in seen:
                    continue
                seen.add(course.key())
                courses.append(course)
        if not courses and "kbcontent" not in html:
            raise SchoolError("会话已过期，请重新登录")
        self.courses = courses
        return courses

    def fetch_current_week(self) -> int:
        try:
            html = self.http.get(self.base + "/framework/xsMainV_new.htmlx",
                                 timeout=self.timeout).text
        except requests.RequestException:
            return None
        m = re.search(r"第\s*(\d+)\s*周", html)
        return int(m.group(1)) if m else None

    def fetch_xnxq(self) -> str:
        html = self._schedule_html()
        m = re.search(r'value="(\d{4}-\d{4}-\d)"\s+selected', html)
        return m.group(1) if m else ""


# ---------- 近七天视图 ----------

STUDY_NAME = "自习"


def _start_minutes(item: dict, period_times=None) -> int:
    """排序键：上课开始时间（分钟）。优先按时间文本解析，其次按节次换算。"""
    text = (item.get("timeText") or "").strip()
    m = re.match(r"(\d{1,2})[:：](\d{2})", text)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    start = item.get("secStart") or 0
    if start:
        block = (int(start) + 1) // 2
        times = period_times or []
        if 1 <= block <= len(times):
            m = re.match(r"(\d{1,2})[:：](\d{2})", times[block - 1])
            if m:
                return int(m.group(1)) * 60 + int(m.group(2))
        return 8 * 60 + (block - 1) * 60      # 无映射表时的兜底
    return 24 * 60                            # 时间未知的排在最后


def next_seven_days(courses, current_week, temp_courses=None,
                    auto_study=False, hidden=None, period_times=None,
                    selfstudy=None, day_offset=0, moves=None):
    """返回未来 7 天（含今天）的课表，每项含日期标签与当日课程。

    - temp_courses: 用户临时添加的课程
    - auto_study:  上午（第一大节）没课时自动补一节自习
    - hidden:      用户手动删除的课程 [{date, name, secStart}]
    - period_times: 节次→时间映射，用于排序
    - selfstudy:   学校发来的自习安排 [{week, day, period, room, name?}]（已按班级筛过）
    - day_offset:  起始日期相对今天的偏移（用于查看前后几周）
    - moves:       用户拖动调整的课程 [{date, name, fromSec, toSec}]，改到目标大节
    """
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    start = today + datetime.timedelta(days=int(day_offset or 0))
    temp = [_normalize_temp(t) for t in (temp_courses or [])]
    hidden_set = {(h.get("date"), h.get("name"), int(h.get("secStart") or 0))
                  for h in (hidden or [])}
    move_map = {(m.get("date"), m.get("name"), int(m.get("fromSec") or 0)):
                int(m.get("toSec") or 0) for m in (moves or [])}
    result = []
    for offset in range(7):
        d = start + datetime.timedelta(days=offset)
        date_iso = d.isoformat()
        week_num = current_week + (d - monday).days // 7 if current_week else None
        dow = d.isoweekday()
        day_courses = []
        if week_num is not None:
            day_courses = [c for c in courses if c.day == dow and week_num in c.weeks]
        items = [course_to_dict(c) for c in day_courses]
        for t in temp:
            if t["day"] != dow:
                continue
            if t["weeks"] and week_num is not None and week_num not in t["weeks"]:
                continue
            items.append(t["data"])

        # ---- 自习规则（详见 plan_selfstudy 的说明）----
        used_secs = {(x.get("secStart") or 0) for x in items}
        week_ok = lambda sl: sl.get("week") in (None, "", week_num)
        mine = [sl for sl in (selfstudy or []) if sl.get("day") == dow and week_ok(sl)]
        file_slots = {sl["period"]: (sl.get("room") or "") for sl in mine if sl.get("room")}
        covered = {sl["period"] for sl in mine}
        # 串休判定（逐天）：① 用户文件在这一天（周六/周日）排了安排
        #                   ② 国家法定调休（chinesecalendar）
        file_weekend = any(sl.get("day") == dow and dow in (6, 7)
                           and sl.get("room") and week_ok(sl) for sl in (selfstudy or []))
        rest, makeup = calendar_flags(d)
        makeup = makeup or file_weekend
        full_day = all(sec in used_secs for sec in (1, 3, 5, 7, 9))

        for period, room in plan_selfstudy(
                dow=dow, used_secs=used_secs, has_class=bool(day_courses),
                full_day=full_day, rest=rest, makeup=makeup,
                file_slots=file_slots, covered=covered):
            if period in file_slots and room == file_slots[period]:
                sl = next((x for x in mine if x["period"] == period), {})
                items.append(_selfstudy_item(period, room, period_times,
                                             sl.get("name") or "",
                                             sl.get("timeText") or ""))
            else:
                items.append(_selfstudy_item(period, room, period_times))

        # 应用拖动调整：把课程改到目标大节（时间随之变化）
        for x in items:
            key = (date_iso, x["name"], int(x.get("secStart") or 0))
            to_sec = move_map.get(key)
            if to_sec:
                x["secStart"] = to_sec
                x["secEnd"] = to_sec + 1
                x["timeText"] = period_time_text(to_sec, period_times)
                x["moved"] = True
                x["secText"] = "第%d-%d节" % (to_sec, to_sec + 1)

        # 剔除手动删除的课程（在补自习之后过滤，删掉的自习才不会被重新补上）
        items = [x for x in items
                 if (date_iso, x["name"], int(x.get("secStart") or 0)) not in hidden_set]

        for x in items:
            if not x.get("timeText"):
                x["timeText"] = period_time_text(x.get("secStart"), period_times)
        items.sort(key=lambda x: (_start_minutes(x, period_times), x["name"]))
        # 当天序号，供"课程详情"显示"现在是第几节课"
        for idx, x in enumerate(items, 1):
            x["dayIndex"] = idx
            x["dayTotal"] = len(items)
        result.append({
            "date": date_iso,
            "dateLabel": "%d月%d日" % (d.month, d.day),
            "fullDateLabel": "%d年%d月%d日" % (d.year, d.month, d.day),
            "dayLabel": WEEKDAY_CN[dow],
            "fullDayLabel": "星期" + "一二三四五六日"[dow - 1],
            "relLabel": ("今天" if d == today else
                         ("明天" if d == today + datetime.timedelta(days=1) else "")),
            "isToday": d == today,
            "weekNum": week_num,
            "courses": items,
        })
    return result


# 大节序号 → 该大节的首个小节（1→第01节, 2→第03节 …）
def period_sec_start(period: int) -> int:
    return max(1, (int(period) - 1) * 2 + 1)


def period_time_text(sec_start, period_times=None) -> str:
    """节次 → 上课时间文本（如 08:00-10:05）。"""
    times = period_times or DEFAULT_PERIOD_TIMES
    start = int(sec_start or 0)
    if not start:
        return ""
    block = (start + 1) // 2
    return times[block - 1] if 1 <= block <= len(times) else ""


def calendar_flags(d: "datetime.date"):
    """返回 (rest, makeup)：

    - rest：周一~周五里的法定休息日（放假不上课）
    - makeup：周末但法定调休上班（串休）

    依赖 chinesecalendar（含国家法定节假日与调休数据）；未安装时返回 (False, False)，
    此时周末一律按法定双休处理。
    """
    try:
        import chinese_calendar as cc
    except ImportError:
        return False, False
    try:
        workday = cc.is_workday(d)
    except Exception:
        return False, False
    weekend = d.isoweekday() in (6, 7)
    if weekend:
        return False, bool(workday)          # 周末上班 = 串休
    return (not workday), False              # 工作日放假 = 不上课


def plan_selfstudy(*, dow: int, used_secs: set, has_class: bool, full_day: bool,
                   rest: bool, makeup: bool,
                   file_slots: dict, covered: set) -> list:
    """决定这一天要补哪些自习，返回 [(大节序号, 教室)]。

    规则（已与用户逐条确认）：
      · 用户文件/描述里写了的时段 → 一律以它为准（含"明确不排"）
      · 早自习(第1-2节)：有其它课且该节空、且第3-4节有课 → 补
      · 第3-4节自习：第1-2节有课、第3-4节空 → 补
      · 整天没课：只有"周末串休"才补早自习，其它情况不补
      · 晚自习(第9-10节)：周五取消；周末没课时周六不补、周日补；
        工作日不上课(法定放假)不补；有其它课则补
      · 满课(五个大节全满) → 不补任何自习
    """
    out = []
    busy1 = 1 in used_secs      # 第01-02节
    busy2 = 3 in used_secs      # 第03-04节
    busy5 = 9 in used_secs      # 第09-10节

    # ---- 早自习：第01-02节 ----
    if 1 in covered:
        if 1 in file_slots:
            out.append((1, file_slots[1]))
    elif full_day or busy1:
        pass
    elif has_class:
        if busy2 and not busy1:
            out.append((1, ""))                       # 1-2空、3-4有课 → 补早自习
    else:
        if dow in (6, 7) and makeup:
            out.append((1, ""))                       # 周末串休才补

    # ---- 第03-04节自习 ----
    if 2 in covered:
        if 2 in file_slots:
            out.append((2, file_slots[2]))
    elif not full_day and has_class and busy1 and not busy2:
        out.append((2, ""))

    # ---- 晚自习：第09-10节 ----
    if 5 in covered:
        if 5 in file_slots:
            out.append((5, file_slots[5]))
    elif dow == 5:
        pass                                          # 周五取消晚自习
    elif full_day or busy5:
        pass
    elif has_class:
        out.append((5, ""))
    elif dow == 6:
        pass                                          # 周六没课不补
    elif rest:
        pass                                          # 工作日法定放假
    else:
        out.append((5, ""))                           # 周日没课等

    return out


def _selfstudy_item(period: int, room: str = "", period_times=None,
                    name: str = "", time_text: str = "") -> dict:
    """生成一条自习（或带名称的临时课程）：period 为大节序号。"""
    sec = period_sec_start(period)
    if name:
        label = name
    elif period == 1:
        label = "早自习"
    elif period == 5:
        label = "晚自习"
    else:
        label = STUDY_NAME
    return {
        "name": label,
        "teacher": "",
        "room": expand_room(room) or "未定义教室",
        "secStart": sec,
        "secEnd": sec + 1,
        "timeText": time_text or period_time_text(sec, period_times),
        "secText": "第%d-%d节" % (sec, sec + 1),
        "weeksText": "",
        "hue": 210,
        "temp": False,
        "auto": True,
        "examType": "",
        "typeColor": "",
    }


def _normalize_temp(t: dict) -> dict:
    """把配置里的临时课程统一成内部结构。"""
    weeks = t.get("weeks") or ""
    return {
        "day": int(t.get("day") or 1),
        "weeks": parse_weeks(weeks) if weeks else set(),
        "data": {
            "name": t.get("name", ""),
            "teacher": t.get("teacher", "") or t.get("teacher", ""),
            "room": expand_room(t.get("room", "")) or "未定义教室",
            "secStart": float(t.get("secStart") or 0),
            "secEnd": 0,
            "timeText": t.get("time", ""),
            "secText": t.get("time", "") or "时间待定",
            "weeksText": weeks or "每周",
            "hue": sum(ord(ch) * 31 for ch in (t.get("name") or "T")) % 360,
            "temp": True,
            "auto": False,
            "examType": "",
            "typeColor": "",
        },
    }


def course_to_dict(c: Course) -> dict:
    hue = sum(ord(ch) * 31 for ch in c.name) % 360
    return {
        "name": c.name,
        "teacher": c.teacher,
        "room": c.room_text,
        "secStart": c.sec_start,
        "secEnd": c.sec_end,
        "secText": c.sec_text,
        "weeksText": c.weeks_raw,
        "hue": hue,
        "temp": False,
        "auto": False,
        "klass": c.klass,
        "examType": c.exam_type or "其它",
        "hours": (c.hours or "").strip(),
        "typeColor": EXAM_COLORS.get(c.exam_type or "其它", EXAM_COLORS["其它"]),
    }
