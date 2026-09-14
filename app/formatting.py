# -*- coding: utf-8 -*-
"""消息排版。

详细风格严格遵循以下格式（分隔线为四个短横线，时间用全角括号）：

    2025年11月19日 星期三 课程如下
    ----
    自习
    （08:30-10:05）
    求真楼（1117）
    ----
    外语
    （10:25-12:00）
    求真楼-求真楼（1117）

- 时间由节次映射而来，映射表可在设置中修改（period_times）
- 临时添加的课程直接使用其填写的「HH:MM-HH:MM」时间
"""

DEFAULT_PERIOD_TIMES = [
    "08:30-10:05",   # 第01-02节
    "10:25-12:00",   # 第03-04节
    "13:30-15:05",   # 第05-06节
    "15:10-16:45",   # 第07-08节
    "16:50-18:25",   # 第09-10节
]

SEP = "----"


def period_time(sec_start, sec_end, period_times=None):
    """把节次映射为时间段文本；无法映射时返回空串。"""
    if not sec_start:
        return ""
    times = period_times or DEFAULT_PERIOD_TIMES
    block = (int(sec_start) + 1) // 2          # 每两小节合为一大节
    if 1 <= block <= len(times):
        return times[block - 1]
    return ""


def course_time_text(course, period_times=None) -> str:
    """课程的显示时间：优先用临时课程自带的时间文本，否则由节次换算。"""
    if course.get("timeText"):
        return course["timeText"]
    return period_time(course.get("secStart"), course.get("secEnd"), period_times)


def _day_header(entry, with_week=True, for_detail=True):
    """详细风格严格输出「YYYY年M月D日 星期X 课程如下」，不带其它后缀。"""
    if for_detail:
        return "%s %s 课程如下" % (entry.get("fullDateLabel") or entry["dateLabel"],
                                   entry.get("fullDayLabel") or entry["dayLabel"])
    head = "%s %s" % (entry["dateLabel"], entry["dayLabel"])
    if with_week and entry.get("weekNum"):
        head += "（第%d周）" % entry["weekNum"]
    return head


# ---------------- 详细风格 ----------------

def build_day_block_detailed(entry, period_times=None, with_week=True):
    """单个日期块，无课程时返回 None。"""
    courses = entry["courses"]
    if not courses:
        return None
    lines = [_day_header(entry, with_week, for_detail=True)]
    for c in courses:
        lines.append(SEP)
        lines.append(c["name"])
        t = course_time_text(c, period_times)
        lines.append("（%s）" % (t or "时间待定"))
        lines.append(c.get("room") or "未定义教室")
    return "\n".join(lines)


# ---------------- 紧凑风格 ----------------

def _compact_line(idx, c, period_times):
    t = course_time_text(c, period_times)
    seg = ["%d. %s" % (idx, c["name"])]
    if t:
        seg.append(t)
    if c.get("room"):
        seg.append(c["room"])
    return " ｜ ".join(seg)


def build_day_block_compact(entry, period_times=None, with_week=True):
    courses = entry["courses"]
    if not courses:
        return None
    lines = [_day_header(entry, with_week, for_detail=False)]
    for i, c in enumerate(courses, 1):
        lines.append(_compact_line(i, c, period_times))
    return "\n".join(lines)


# ---------------- 入口 ----------------

def build_message(days, scope="today", style="detailed", emoji=True,
                  period_times=None, empty_hint=True):
    """days 为 school.next_seven_days() 的输出。"""
    days = days or []
    if not days:
        return "（暂无课表数据）"

    if scope == "today":
        entry = days[0]
        if not entry["courses"]:
            head = _day_header(entry, for_detail=(style == "detailed"))
            return "%s\n%s" % (head, "今天没有课" if style == "detailed" else "无课")
        if style == "compact":
            return build_day_block_compact(entry, period_times)
        return build_day_block_detailed(entry, period_times)

    blocks = []
    for entry in days:
        if style == "compact":
            b = build_day_block_compact(entry, period_times)
        else:
            b = build_day_block_detailed(entry, period_times)
        if b:
            blocks.append(b)
    if not blocks:
        return "近七天都没有课" if empty_hint else ""
    joiner = "\n\n" if style == "detailed" else "\n\n"
    return joiner.join(blocks)
