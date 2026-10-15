#!/usr/bin/env python3
"""tutor_progress.py — 学习进度精准读写 CLI（纯标准库，零依赖，可整体拷贝到任意技能目录）

设计目标
  * 省 token：只读写需要的片段，不把整个 progress.json（实测 34029 字节 / 约 34 KB）塞进上下文
  * 可移植：用 __file__ 定位自身，可整体拷进任意 agent 的技能目录
  * 写入安全：临时文件 + 原子替换，写一半被打断也不会损坏数据
  * 不破坏历史数据：兼容早期字段形状（lang/domain、note/notes、字段不全的 exercises）

用法
  tutor_progress.py where
  tutor_progress.py list
  tutor_progress.py get <领域> [概念]
  tutor_progress.py update <领域> <概念> <字段> <值>        字段: mastery | lastPracticed | notes
  tutor_progress.py add-note <领域> <概念> <备注>
  tutor_progress.py weak <领域> add|remove <知识点>
  tutor_progress.py exercise <领域> <名称> <通过|未通过> [备注]
  tutor_progress.py milestone <领域> <概念> <掌握程度> [备注]
  tutor_progress.py render                                  由 progress.json 重新生成 milestones.md 视图

环境变量
  TUTOR_PROGRESS    覆盖进度文件路径（默认 <技能目录>/references/progress.json）
  TUTOR_MILESTONES  覆盖里程碑视图路径（默认与进度文件同目录下的 milestones.md）

领域名自动发现，并支持别名（数据库/database→sql、工具链/git→tools、智能合约→smart-contract …）。
保留键（languages / milestones / concepts / weakPoints / exercises / _comment / 版本号字段）不能当领域名，
写命令遇到保留键会直接报错退出，不会改动进度文件。
"""
import datetime
import difflib
import json
import os
import sys
import tempfile

USAGE = "用法" + __doc__.split("用法", 1)[1].split("环境变量", 1)[0].rstrip()

# ── 路径 ──────────────────────────────────────────────────────────────────────
SKILL_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
REFS = os.path.join(SKILL_DIR, "references")
PROG = os.path.abspath(os.environ.get("TUTOR_PROGRESS") or os.path.join(REFS, "progress.json"))
EXAMPLE = os.path.join(REFS, "progress.example.json")
# 里程碑视图默认跟着进度文件走：默认布局下仍是 references/milestones.md，
# 用 TUTOR_PROGRESS 指向别处时（例如测试用临时目录）不会误写真实数据。
MILESTONES_MD = os.path.abspath(
    os.environ.get("TUTOR_MILESTONES")
    or os.path.join(os.path.dirname(PROG), "milestones.md")
)

MASTERY = ("未学过", "初步了解", "能独立使用", "熟练掌握")
RESULTS = ("通过", "未通过")

# 进度文件的保留键：这些名字是结构本身（顶层容器、领域内字段、说明与版本号），
# 一旦被当成领域名写入，会把已有数据整体替换掉（例如 milestones 数组被换成领域字典）。
RESERVED_KEYS = (
    "languages", "milestones", "concepts", "weakPoints", "exercises",
    "_comment", "version", "schemaVersion", "schema_version",
)
RESERVED_LOWER = frozenset(k.lower() for k in RESERVED_KEYS)


def empty_data():
    """全新的空进度结构（就是真实 schema，不读取任何模板/示例文件）。"""
    return {"languages": {}, "milestones": []}

DOMAIN_ALIASES = {
    "database": "sql", "db": "sql", "mysql": "sql", "sqlite": "sql",
    "数据库": "sql", "sql数据库": "sql",
    "工具链": "tools", "工具": "tools", "git": "tools", "github": "tools",
    "区块链": "blockchain", "区块链知识栈": "blockchain",
    "智能合约": "smart-contract", "容器": "container", "容器化": "container",
    "后端": "backend", "前端": "vue",
}


def die(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def need(args, n, form):
    """参数不足时给用法提示，而不是抛 Python 堆栈。"""
    if len(args) < n:
        die(f"❌ 参数不足\n  用法: tutor_progress.py {form}")


def is_reserved(name):
    """该名字是否是进度文件的结构保留键（不能当领域名）。"""
    key = str(name).strip()
    return key in RESERVED_KEYS or key.lower() in RESERVED_LOWER


def reserved_msg(domain, writing=True):
    msg = (f"❌ 「{domain}」是进度文件的保留键，不能当领域名。\n"
           f"  保留键: {', '.join(RESERVED_KEYS)}\n"
           f"  这些名字是进度结构的容器/字段，写成领域名会覆盖已有数据。\n"
           f"  请换一个领域名（例如 python、sql、blockchain）。")
    if writing:
        msg += "\n  进度文件未被改动。"
    return msg


def reject_reserved(domain, writing=True):
    if is_reserved(domain):
        die(reserved_msg(domain, writing))


# ── 领域与概念解析 ────────────────────────────────────────────────────────────
def resolve_domain(data, domain):
    """别名 → 规范领域名。

    无条件映射：即使目标领域还不存在，也落到规范名上，
    避免「数据库」和「sql」被记成两个割裂的领域。
    """
    if domain in data.get("languages", {}) or domain in data:
        return domain
    return DOMAIN_ALIASES.get(domain) or DOMAIN_ALIASES.get(str(domain).lower()) or domain


def locate(data, domain):
    domain = resolve_domain(data, domain)
    if domain in data.get("languages", {}):
        return data["languages"][domain]
    return data.get(domain) if isinstance(data.get(domain), dict) else None


def all_areas(data):
    """自动发现领域：languages 下的语言 + 所有形如 {concepts:…} 的顶层键。"""
    areas = list(data.get("languages", {}).keys())
    for dom, val in data.items():
        if dom in areas or is_reserved(dom):
            continue
        if isinstance(val, dict) and "concepts" in val:
            areas.append(dom)
    return areas


def area_of(data, domain):
    """取领域字典，不存在则建骨架（供写命令使用）。返回 (领域字典, 规范领域名)。

    保留键直接报错退出——在建立骨架前就拦住，保证进度文件不被改动。
    """
    reject_reserved(domain)
    name = resolve_domain(data, domain)
    reject_reserved(name)
    if name in data.get("languages", {}):
        return data["languages"][name], name
    if isinstance(data.get(name), dict) and "concepts" in data[name]:
        return data[name], name
    new = {"concepts": {}, "weakPoints": [], "exercises": []}
    data[name] = new
    return new, name


def match_concept(concepts, name):
    """概念名匹配：精确 → 唯一子串。失败时返回候选列表供提示。"""
    if name in concepts:
        return name, None
    low = name.strip().lower()
    hits = [c for c in concepts if low and low in c.lower()]
    if len(hits) == 1:
        return hits[0], None
    close = difflib.get_close_matches(name, list(concepts), n=3, cutoff=0.5)
    return None, (close or hits[:3])


# ── 读写 ──────────────────────────────────────────────────────────────────────
def load():
    """读进度。只读命令不落盘；文件缺失时返回全新的空结构。返回 (data, 文件是否存在)。

    注意：**不读 references/progress.example.json**。示例文件只是 schema 文档，
    把它当成初始数据会让全新安装凭空出现「python: 1 个概念」这类假进度，
    并会在首次写入时把示例固化进真实进度文件。
    """
    if not os.path.exists(PROG):
        return empty_data(), False
    try:
        with open(PROG, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("顶层结构不是 JSON 对象")
        data.pop("_comment", None)
        return data, True
    except ValueError as e:
        bak = PROG + ".bak"
        try:
            os.replace(PROG, bak)
            print(f"⚠️ 进度文件损坏（{e}），已备份为 {bak}，将重建", file=sys.stderr)
        except OSError:
            print(f"⚠️ 进度文件损坏（{e}），且无法备份，请检查权限", file=sys.stderr)
        return empty_data(), False


def save(data):
    """原子写：同目录临时文件 → os.replace。失败时给可操作提示，不抛堆栈。"""
    d = os.path.dirname(PROG) or "."
    try:
        os.makedirs(d, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".progress.", suffix=".tmp")
    except OSError as e:
        die(f"❌ 无法写入进度文件：{e}\n  路径: {PROG}\n"
            f"  若当前会话只能写工作目录（只读沙箱 / DSH 的 workspace-write 等），"
            f"请放开该目录写权限后重试。")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, PROG)
    except OSError as e:
        if os.path.exists(tmp):
            os.unlink(tmp)
        die(f"❌ 写入进度文件失败：{e}\n  路径: {PROG}")


def write_milestones_md(data):
    """由 progress.json 的 milestones 生成人类可读视图（兼容历史字段形状）。"""
    rows = []
    for m in data.get("milestones", []):
        if not isinstance(m, dict):
            continue
        date = m.get("date") or ""
        concept = m.get("concept") or m.get("lang") or m.get("domain") or "（未标注）"
        level = m.get("level") or ""
        note = m.get("note") or m.get("notes") or ""
        line = f"- {date} · {concept} → {level}".rstrip(" →")
        if note:
            line += f" · {note}"
        rows.append((date, line))
    rows.sort(key=lambda r: r[0])

    body = [
        "# 学习里程碑",
        "",
        "> 本文件由 `scripts/tutor_progress.py` 自动生成（数据源：progress.json 的 `milestones`）。",
        "> 手改会在下次生成时被覆盖；补记请用：",
        "> `tutor_progress.py milestone <领域> <概念> <掌握程度> [备注]`",
        "",
        "格式：`日期 · 知识点 → 掌握程度 · 说明`",
        "",
    ]
    body += [line for _, line in rows] or ["（暂无）"]
    body.append("")
    try:
        with open(MILESTONES_MD, "w", encoding="utf-8") as f:
            f.write("\n".join(body))
        return len(rows)
    except OSError as e:
        print(f"⚠️ 进度已保存，但 milestones.md 写入失败：{e}", file=sys.stderr)
        return None


# ── 命令 ──────────────────────────────────────────────────────────────────────
def cmd_where():
    writable = os.access(os.path.dirname(PROG) or ".", os.W_OK)
    print(f"SKILL_DIR  = {SKILL_DIR}")
    print(f"PROGRESS   = {PROG}  ({'存在' if os.path.exists(PROG) else '尚未创建，首次记录进度时自动生成'})")
    print(f"MILESTONES = {MILESTONES_MD}  ({'存在' if os.path.exists(MILESTONES_MD) else '尚未生成'})")
    print(f"EXAMPLE    = {EXAMPLE}  ({'存在' if os.path.exists(EXAMPLE) else '缺失'})")
    print(f"目录可写   = {'是' if writable else '否（只读：读取正常，记录进度会失败）'}")
    print(f"python     = {sys.executable}")


def cmd_list(data, exists):
    if not exists and not all_areas(data):
        print(f"尚无进度数据（{PROG} 不存在，第一次记录进度时自动创建）")
        return
    for dom in all_areas(data):
        area = locate(data, dom) or {}
        extras = []
        if area.get("weakPoints"):
            extras.append(f"{len(area['weakPoints'])} 薄弱")
        if area.get("exercises"):
            extras.append(f"{len(area['exercises'])} 练习")
        suffix = (" · " + " · ".join(extras)) if extras else ""
        print(f"{dom}: {len(area.get('concepts', {}))} 个概念{suffix}")
    n_ms = len(data.get("milestones", []))
    print(f"milestones: {n_ms} 条" + ("（milestones.md 已生成）" if os.path.exists(MILESTONES_MD) else "（可用 render 生成视图）"))


def cmd_get(data, domain, concept=None):
    reject_reserved(domain, writing=False)
    area = locate(data, domain)
    if area is None:
        die(f"未找到领域: {domain}\n  现有领域: {', '.join(all_areas(data)) or '（无）'}")
    concepts = area.get("concepts", {})
    if concept:
        real, cands = match_concept(concepts, concept)
        if real is None:
            msg = f"未找到概念: {concept}"
            if cands:
                msg += "\n  你是不是想找：\n    " + "\n    ".join(cands)
            die(msg)
        c = concepts[real]
        print(f"{real}: mastery={c.get('mastery')}, lastPracticed={c.get('lastPracticed') or '无'}")
        if c.get("notes"):
            print(f"  notes: {c['notes']}")
        return
    for name, c in concepts.items():
        print(f"{name}: {c.get('mastery')} (last: {c.get('lastPracticed') or '无'})")
    if area.get("weakPoints"):
        print("weakPoints:", "、".join(area["weakPoints"]))
    if area.get("exercises"):
        print(f"exercises: {len(area['exercises'])} 条")
        for e in area["exercises"][-3:]:
            print(f"  - {e.get('date', '')} {e.get('name', '')} → {e.get('result', '')}")


def cmd_update(data, domain, concept, field, value):
    if field not in ("mastery", "lastPracticed", "notes"):
        die(f"字段不支持: {field}（仅 mastery / lastPracticed / notes）")
    if field == "mastery" and value not in MASTERY:
        die(f"掌握程度取值必须是: {' / '.join(MASTERY)}")
    area, real_domain = area_of(data, domain)
    concepts = area.setdefault("concepts", {})
    real, cands = match_concept(concepts, concept)
    if real is None:
        real = concept
        if cands:
            print(f"⚠️ 已新建概念「{concept}」——注意已有相似概念：{'、'.join(cands)}；"
                  f"若想更新已有条目，请用其原名。", file=sys.stderr)
    c = concepts.setdefault(real, {"mastery": "未学过", "lastPracticed": "", "notes": ""})
    c[field] = value
    save(data)
    print(f"✓ 已更新 {real_domain}/{real}.{field} = {value}")


def cmd_add_note(data, domain, concept, note):
    area, real_domain = area_of(data, domain)
    concepts = area.setdefault("concepts", {})
    real, cands = match_concept(concepts, concept)
    if real is None:
        real = concept
        if cands:
            print(f"⚠️ 已新建概念「{concept}」——注意已有相似概念：{'、'.join(cands)}", file=sys.stderr)
    c = concepts.setdefault(real, {"mastery": "未学过", "lastPracticed": "", "notes": ""})
    c["notes"] = note
    save(data)
    print(f"✓ 已写备注 {real_domain}/{real}")


def cmd_weak(data, domain, action, point):
    if action not in ("add", "remove", "添加", "删除"):
        die(f"动作不支持: {action}（add | remove）")
    adding = action in ("add", "添加")
    area, real_domain = area_of(data, domain)
    weak = area.setdefault("weakPoints", [])
    if adding:
        if point in weak:
            print(f"= {real_domain} 的薄弱点已存在: {point}")
            return
        weak.append(point)
    else:
        if point not in weak:
            die(f"未找到薄弱点: {point}\n  现有: {'、'.join(weak) or '（无）'}")
        weak.remove(point)
    save(data)
    print(f"✓ 已{'记入' if adding else '移除'} {real_domain} 薄弱点: {point}（共 {len(weak)} 条）")


def parse_exercise_args(args):
    """解析 exercise 的位置参数，返回 (领域, 名称, 结果, 备注)。

    规则（不依赖「第一个等于 通过/未通过 的参数」，所以概念名本身叫「通过」也能用）：
      1. 结果优先取固定位置的 args[2]（<领域> <名称> <结果> [备注]）；
      2. args[2] 不是合法结果时，回退到「从 args[2] 起第一个合法结果」这个旧用法，
         以便不加引号的多词名称（exercise sql 写 JOIN 查询 未通过）继续可用；
      3. 也可以用 --result/-r 显式指定结果，此时结果前的都是名称、后面都是备注。
    """
    flag = next((i for i, a in enumerate(args) if a in ("--result", "-r")), None)
    if flag is not None:
        if flag + 1 >= len(args):
            die("❌ --result 后面要跟 通过 或 未通过\n"
                "  用法: tutor_progress.py exercise <领域> <名称> --result <通过|未通过> [备注]")
        result = args[flag + 1]
        name = " ".join(args[1:flag]).strip()
        note = " ".join(args[flag + 2:])
    else:
        result = args[2]
        if result in RESULTS:
            name, note = args[1], " ".join(args[3:])
        else:
            hit = next((i for i, a in enumerate(args[2:], start=2) if a in RESULTS), None)
            if hit is None:
                name, note = args[1], " ".join(args[3:])
            else:
                result = args[hit]
                name, note = " ".join(args[1:hit]).strip(), " ".join(args[hit + 1:])
    if result not in RESULTS:
        die(f"❌ 练习结果必须是 {' / '.join(RESULTS)}（收到「{result}」）\n"
            f"  用法: tutor_progress.py exercise <领域> <名称> <通过|未通过> [备注]\n"
            f"  名称含空格时请加引号，或用 --result 显式指定结果。")
    if not name:
        die("❌ 缺少练习名称\n"
            "  用法: tutor_progress.py exercise <领域> <名称> <通过|未通过> [备注]")
    return args[0], name, result, note


def cmd_exercise(data, domain, name, result, note=""):
    """练习记录 schema（权威定义）：{name, date, result, domain, notes}

    result 只能是 通过 / 未通过（调用前已校验）；domain 取当前领域（含别名解析结果）。
    """
    area, real_domain = area_of(data, domain)
    record = {
        "name": name,
        "date": datetime.date.today().isoformat(),
        "result": result,
        "domain": real_domain,
        "notes": note,
    }
    area.setdefault("exercises", []).append(record)
    save(data)
    print(f"✓ 已记录练习 {real_domain}/{name} → {result}")


def cmd_milestone(data, domain, concept, level, note=""):
    if level not in MASTERY:
        die(f"掌握程度取值必须是: {' / '.join(MASTERY)}")
    reject_reserved(domain)
    entry = {"domain": resolve_domain(data, domain), "concept": concept,
             "level": level, "date": datetime.date.today().isoformat()}
    if note:
        entry["note"] = note
    data.setdefault("milestones", []).append(entry)
    save(data)
    n = write_milestones_md(data)
    print(f"✓ 已记录里程碑: {entry['date']} · {concept} → {level}"
          + (f"（milestones.md 共 {n} 条）" if n is not None else ""))


# ── 入口 ──────────────────────────────────────────────────────────────────────
def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(USAGE)
        return 0 if argv else 1
    cmd, args = argv[0], argv[1:]

    if cmd == "where":
        cmd_where()
        return 0

    if cmd == "list":
        cmd_list(*load())
        return 0

    if cmd == "get":
        need(args, 1, "get <领域> [概念]")
        data, _ = load()
        cmd_get(data, args[0], args[1] if len(args) > 1 else None)
        return 0

    if cmd == "update":
        need(args, 4, "update <领域> <概念> <字段> <值>")
        data, _ = load()
        cmd_update(data, args[0], args[1], args[2], " ".join(args[3:]))
        return 0

    if cmd == "add-note":
        need(args, 3, "add-note <领域> <概念> <备注>")
        data, _ = load()
        cmd_add_note(data, args[0], args[1], " ".join(args[2:]))
        return 0

    if cmd == "weak":
        need(args, 3, "weak <领域> add|remove <知识点>")
        data, _ = load()
        cmd_weak(data, args[0], args[1], " ".join(args[2:]))
        return 0

    if cmd == "exercise":
        need(args, 3, "exercise <领域> <名称> <通过|未通过> [备注]")
        domain, name, result, note = parse_exercise_args(args)
        data, _ = load()
        cmd_exercise(data, domain, name, result, note)
        return 0

    if cmd == "milestone":
        need(args, 3, "milestone <领域> <概念> <掌握程度> [备注]")
        data, _ = load()
        cmd_milestone(data, args[0], args[1], args[2], " ".join(args[3:]))
        return 0

    if cmd == "render":
        data, _ = load()
        n = write_milestones_md(data)
        if n is not None:
            print(f"✓ 已由 progress.json 生成 milestones.md（{n} 条）")
        return 0

    die(f"未知命令: {cmd}\n\n{USAGE}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
