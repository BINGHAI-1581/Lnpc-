# -*- coding: utf-8 -*-
"""解析学校发的课表/自习安排文件（Excel、Word），提取指定班级的教室安排。

支持的文件形态（两种都按"表格"处理）：
  · Excel (.xlsx/.xlsm)：用 openpyxl 读取（含合并单元格展开）
  · Word  (.docx)：用 python-docx 读取表格；没有表格时退化为按文本行解析

表格结构（以"早自习教室安排"为例）：
    行1:  周一    | 周二   | 周三   | ...
    行2:  一二节 三四节 | 一二节 三四节 | ...
    行3+: 煤化工2531 | 3614 | / | ...

识别逻辑：
  1. 找出含"周一…周五/周日"的行作为表头，建立 列 → 星期 映射
  2. 找出含"一二节/三四节…"的行，建立 列 → 大节序号 映射（早自习=第1-2节）
  3. 逐行取第一列作为班级名，与目标班级做归一化匹配
  4. 该行中每个格子：空或 "/" 视为没有安排，其它值视为教室
"""
import os
import re

WEEKDAY_NAMES = {
    "周一": 1, "星期一": 1, "礼拜一": 1,
    "周二": 2, "星期二": 2, "礼拜二": 2,
    "周三": 3, "星期三": 3, "礼拜三": 3,
    "周四": 4, "星期四": 4, "礼拜四": 4,
    "周五": 5, "星期五": 5, "礼拜五": 5,
    "周六": 6, "星期六": 6, "礼拜六": 6,
    "周日": 7, "星期日": 7, "周天": 7, "星期天": 7, "礼拜天": 7,
}

# 大节序号：1=第01-02节, 2=第03-04节, 3=第05-06节, 4=第07-08节, 5=第09-10节
PERIOD_PATTERNS = [
    (5, r"(九十|九、十|09-10|9-10|晚上|晚自习|晚间)"),
    (4, r"(七八|七、八|07-08|7-8)"),
    (3, r"(五六|五、六|05-06|5-6|下午)"),
    (2, r"(三四|三、四|03-04|3-4)"),
    (1, r"(一二|一、二|01-02|1-2|早上|早自习|早晨)"),
]

EMPTY_MARKS = {"", "/", "／", "\\", "-", "—", "无", "None", "none", "nan"}


def normalize_class(name: str) -> str:
    """班级名归一化，便于匹配（去空格、去"班"、统一大小写与全角）。"""
    if not name:
        return ""
    text = str(name)
    for a, b in (("（", "("), ("）", ")"), ("　", "")):
        text = text.replace(a, b)
    text = re.sub(r"[\s\-_]+", "", text)
    text = text.replace("级", "")
    if text.endswith("班"):
        text = text[:-1]
    return text.lower()


def _clean_cell(value) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _is_empty(value: str) -> bool:
    return _clean_cell(value) in EMPTY_MARKS


def _period_of(text: str):
    for period, pattern in PERIOD_PATTERNS:
        if re.search(pattern, text):
            return period
    return None


def _hint_period(text: str) -> int:
    """表头没有节次标签时，按文件名/表内文字推断这份安排属于哪一段自习。

    例：《…第三周晚自习安排.xlsx》里只有星期列没有节次列，应视为第09-10节（18:00 晚自习）。
    """
    if re.search(r"晚自习|晚课|夜间|晚自修|晚上|18[:：]\d|19[:：]\d|20[:：]\d", text):
        return 5
    if re.search(r"午自习|中午|午间|13[:：]\d", text):
        return 3
    if re.search(r"早自习|早自修|早读|早上|早晨|08[:：]\d|8[:：]\d", text):
        return 1
    return 1


# ---------------- 读取为二维表格 ----------------

def _grid_from_xlsx(path: str):
    import openpyxl

    wb = openpyxl.load_workbook(path, data_only=True)
    grids = []
    for ws in wb.worksheets:
        # 展开合并单元格：把左上角的值填到整个合并区域
        grid = [["" for _ in range(ws.max_column)] for _ in range(ws.max_row)]
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is not None:
                    grid[cell.row - 1][cell.column - 1] = _clean_cell(cell.value)
        for rng in ws.merged_cells.ranges:
            value = grid[rng.min_row - 1][rng.min_col - 1]
            if not value:
                continue
            for r in range(rng.min_row - 1, rng.max_row):
                for c in range(rng.min_col - 1, rng.max_col):
                    grid[r][c] = value
        if any(any(row) for row in grid):
            grids.append((ws.title, grid))
    return grids


def _grid_from_docx(path: str):
    import docx

    doc = docx.Document(path)
    grids = []
    for i, table in enumerate(doc.tables):
        grid = []
        for row in table.rows:
            cells = [_clean_cell(c.text) for c in row.cells]
            grid.append(cells)
        # 合并单元格会重复取值，去掉行内连续重复以贴近原始结构
        if any(any(r) for r in grid):
            grids.append(("表%d" % (i + 1), grid))
    return grids


def _grid_from_text(text: str):
    rows = [re.split(r"[\t,，;；]+|\s{2,}", line.strip())
            for line in text.splitlines() if line.strip()]
    return [("文本", rows)] if rows else []


# ---------------- 表格解析 ----------------

def _analyze_grid(grid):
    """从二维表格中提取 星期→列 与 列→大节 的映射。"""
    day_cols, period_cols = {}, {}
    header_row = -1
    for r, row in enumerate(grid[:6]):          # 表头通常在前几行
        found = {}
        for c, cell in enumerate(row):
            key = _clean_cell(cell)
            if not key:
                continue
            for name, idx in WEEKDAY_NAMES.items():
                if name in key:
                    found.setdefault(c, idx)
                    break
        if len(found) >= 3:
            day_cols = found
            header_row = r
            break
    if not day_cols:
        return None

    # 大节行：表头下方第一行里有"一二节"之类的标签
    for r in range(header_row + 1, min(header_row + 4, len(grid))):
        found = {}
        for c, cell in enumerate(grid[r]):
            p = _period_of(_clean_cell(cell))
            if p:
                found[c] = p
        if found:
            period_cols = found
            break
    return {"day_cols": day_cols, "period_cols": period_cols, "header_row": header_row}


def _class_column(grid, header_row):
    """班级名所在列：表头下方各行的第一个非空单元格最左列。"""
    for r in range(header_row + 1, min(header_row + 4, len(grid))):
        for c, cell in enumerate(grid[r]):
            if not _is_empty(cell) and not _period_of(_clean_cell(cell)):
                return c
    return 0


def parse_file(path: str) -> dict:
    """解析文件，返回 {source, grids, days, periods, classes, slots}。

    slots 为所有班级的安排：[{klass, day, period, room}]
    """
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xlsm"):
        grids = _grid_from_xlsx(path)
    elif ext == ".docx":
        grids = _grid_from_docx(path)
    elif ext in (".txt", ".csv"):
        grids = _grid_from_text(open(path, encoding="utf-8", errors="ignore").read())
    else:
        raise ValueError("暂不支持的文件类型：%s（请用 .xlsx / .docx）" % (ext or "未知"))

    # 文件名 + 表内文字 → 推断基准大节（没有节次标签的列以此为准）
    all_text = [os.path.basename(path)]
    for sheet_name, grid in grids:
        all_text.append(sheet_name)
        for row in grid[:8]:
            all_text.extend(c for c in row if c)
    base_period = _hint_period(" ".join(all_text))
    if _period_of(" ".join(all_text)):
        base_period = _period_of(" ".join(all_text))

    result = {"source": os.path.basename(path), "path": path, "base_period": base_period,
              "sheets": [], "days": [], "periods": [], "classes": [], "slots": []}
    for sheet_name, grid in grids:
        info = _analyze_grid(grid)
        if not info:
            continue
        day_cols = info["day_cols"]
        period_cols = info["period_cols"] or {}
        klass_col = _class_column(grid, info["header_row"])

        # 每个"星期"占用的列范围（表头合并后同一天的列值相同）
        wanted_days = sorted(set(day_cols.values()))
        rows_found = 0
        for r in range(info["header_row"] + 1, len(grid)):
            row = grid[r]
            if klass_col >= len(row):
                continue
            klass = _clean_cell(row[klass_col])
            if _is_empty(klass) or _period_of(klass):
                continue
            rows_found += 1
            if klass not in result["classes"]:
                result["classes"].append(klass)
            for c, day in day_cols.items():
                if c >= len(row):
                    continue
                room = _clean_cell(row[c])
                if _is_empty(room):
                    continue
                period = period_cols.get(c)
                if period is None:
                    # 没标节次：同一天只有一列就是"基准大节"，多列则从基准往后排
                    same_day = sorted(k for k, v in day_cols.items() if v == day)
                    offset = same_day.index(c) if c in same_day else 0
                    period = min(5, base_period + offset)
                result["slots"].append({"klass": klass, "day": day,
                                        "period": period, "room": room})
        if rows_found:
            result["sheets"].append(sheet_name)
            result["days"] = wanted_days
            result["periods"] = sorted(set(period_cols.values())) or [1]
    return result


def slots_for_class(parsed: dict, class_name: str):
    """挑出目标班级的安排；返回 (slots, 是否精确匹配)。"""
    target = normalize_class(class_name)
    exact = [s for s in parsed["slots"] if normalize_class(s["klass"]) == target]
    if exact:
        return exact, True
    # 退一步：包含关系（如文件写"煤化工2531班"、系统里是"煤化工2531"）
    loose = [s for s in parsed["slots"]
             if target and (target in normalize_class(s["klass"])
                            or normalize_class(s["klass"]) in target)]
    return loose, False


# ---------------- 手动输入描述的解析 ----------------

TIME_RANGE = re.compile(r"(\d{1,2})[:：](\d{2})\s*[-~—－至到]\s*(\d{1,2})[:：](\d{2})")
BARE_ROOM = re.compile(r"^\d{4}$")
# 整体教室表达：大教室十（2415） / 求真楼1117 / 4号教学楼301 / 纯四位数字
ROOM_TOKEN = re.compile(
    r"([一-龥A-Za-z0-9]{0,8}(?:教室|教学楼|楼)[一-龥A-Za-z0-9（）()]{0,12}"
    r"|(?<![\d:])\d{4}(?![\d:]))")


def _period_from_time(hh: int, mm: int):
    """按开始时间判断属于哪一大节（与默认作息一致）。"""
    minutes = hh * 60 + mm
    for period, start in ((1, 8 * 60), (2, 10 * 60 + 25), (3, 13 * 60 + 30),
                          (4, 15 * 60 + 10), (5, 18 * 60)):
        if minutes < start + 30:          # 落在该大节开始前后即归入该大节
            return period
    return 5


def parse_text(text: str) -> list:
    """把口语化的安排描述解析成条目。

    支持一行一条，例如：
        周二 一二节 3614
        周三 3-4节 高等数学 求真楼1117
        周四晚自习 18:00-19:40 3614
        周五 13:30-15:05 大教室十（2415） 化工原理
    识别不出星期或时段的行会被忽略。
    返回 [{day, period, room, name, timeText}]
    """
    items = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        # 星期
        day = None
        for name, idx in WEEKDAY_NAMES.items():
            if name in line:
                day = idx
                break
        if day is None:
            m = re.search(r"周([一二三四五六日天1-7])", line)
            if m:
                ch = m.group(1)
                day = {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7}.get(
                    ch, "一二三四五六日".find(ch) + 1 if ch in "一二三四五六日" else None)
        if not day:
            continue

        # 时段：优先看具体时间，其次看"第几节/大节"关键词
        time_text = ""
        period = None
        mt = TIME_RANGE.search(line)
        if mt:
            hh, mm = int(mt.group(1)), int(mt.group(2))
            time_text = "%02d:%s-%02d:%s" % (hh, mt.group(2), int(mt.group(3)), mt.group(4))
            period = _period_from_time(hh, mm)
        else:
            period = _period_of(line)
        if period is None:
            continue

        # 教室：整体匹配"XX楼XXX""大教室十（2415）"，其次纯四位数字，最后括号内容
        room = ""
        mroom = re.search(ROOM_TOKEN, line)
        if mroom:
            room = mroom.group(1).strip()
        if not room:
            mr = re.search(r"[（(]([^（）()]{2,20})[）)]", line)
            if mr and not re.search(r"\d{1,2}[:：]\d{2}", mr.group(1)):
                room = mr.group(1).strip()

        # 名称：去掉星期/时段/教室后剩下的中文短语
        rest = line
        for pat in (r"周[一二三四五六日天1-7]", TIME_RANGE,
                    r"第?[0-9一二三四五六七八九十]{1,2}[-~]?[0-9一二三四五六七八九十]{0,2}节",
                    r"(?:晚上|下午|上午|早上|中午|傍晚)?\d{1,2}\s*[点時时](?:半)?",
                    r"晚上|下午|上午|早上|中午|傍晚|早自习|晚自习|自习",
                    ROOM_TOKEN, r"[（(][^（）()]*[）)]"):
            rest = re.sub(pat, " ", rest)
        if room and BARE_ROOM.match(room):
            rest = rest.replace(room, " ")
        name = re.sub(r"\s+", "", rest)
        name = re.sub(r"^[\s,，、:：-]+|[\s,，、:：-]+$", "", name)
        if name in ("早自习", "晚自习", "自习"):
            name = ""

        items.append({"day": day, "period": period,
                      "room": room, "name": name, "timeText": time_text})
    return items
