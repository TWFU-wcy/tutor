#!/usr/bin/env python3
"""tutor_progress.py — 学习进度精准读写，避免全文加载 progress.json（省 token）

用法:
  tutor_progress.py where
  tutor_progress.py list
  tutor_progress.py get <领域> [概念]
  tutor_progress.py update <领域> <概念> <字段> <值>
  tutor_progress.py add-note <领域> <概念> <备注>

字段: mastery | lastPracticed | notes
领域: 自动发现（languages 下的语言 + 所有 {concepts:...} 顶层领域，如 vue/sql/go/blockchain/java/container/backend/dapp…）
（自动定位：优先 languages.<领域>，其次顶层领域）
用 `list` 查看当前实际有哪些领域。

原理: get 只输出该领域/概念的小片段，update 精准改一个字段，
     而不是把整个 progress.json（~16K token）读进上下文。

可移植性: 纯标准库，无第三方依赖；用 __file__ 定位自身，可整体拷到任意
      agent 的技能目录（~/.agents/skills、~/.claude/skills、DSH_HOME/skills…）。
      TUTOR_PROGRESS 可覆盖进度文件位置。
"""
import json, sys, os, tempfile, contextlib

# 进度文件定位：可用环境变量 TUTOR_PROGRESS 覆盖，默认取本脚本上一级的 references/progress.json
PROG = os.environ.get("TUTOR_PROGRESS") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, "references", "progress.json"
)
PROG = os.path.abspath(PROG)


SKILL_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
EXAMPLE = os.path.join(SKILL_DIR, "references", "progress.example.json")

EMPTY = {"languages": {}, "milestones": []}


def load():
    """读取进度；文件不存在时用 example 模板或空骨架自动初始化。

    首次安装（git clone 后）没有 progress.json，之前这里会直接抛异常。
    """
    if not os.path.exists(PROG):
        data = dict(EMPTY)
        if os.path.exists(EXAMPLE):
            try:
                with open(EXAMPLE, encoding="utf-8") as f:
                    data = json.load(f)
                data.pop("_comment", None)
            except (OSError, ValueError):
                data = dict(EMPTY)
        save(data)
        print(f"ℹ️ 进度文件不存在，已自动初始化: {PROG}", file=sys.stderr)
        return data
    try:
        with open(PROG, encoding="utf-8") as f:
            return json.load(f)
    except ValueError as e:
        bak = PROG + ".bak"
        try:
            os.replace(PROG, bak)
            print(f"⚠️ 进度文件损坏（{e}），已备份为 {bak} 并重建", file=sys.stderr)
        except OSError:
            print(f"⚠️ 进度文件损坏（{e}），重建失败，请检查权限", file=sys.stderr)
        return dict(EMPTY)


def _lock(fh):
    """多 agent 同时写同一份进度时串行化；拿不到锁就照常写（不阻塞教学）。"""
    try:
        import fcntl
        fcntl.flock(fh, fcntl.LOCK_EX)
    except Exception:
        pass


@contextlib.contextmanager
def locked():
    """独占锁，用来包住整段「读 → 改 → 写」。

    只锁写是不够的：两个 agent 若各自先读后写，后写的会覆盖先写的（丢更新）。
    因此 update / add-note 必须在这个锁里重新 load 一次。
    """
    lf = None
    try:
        os.makedirs(os.path.dirname(PROG) or ".", exist_ok=True)
        lf = open(PROG + ".lock", "a+")
        _lock(lf)
    except Exception:
        if lf:
            lf.close()
        lf = None
    try:
        yield
    finally:
        if lf:
            lf.close()


def save(data):
    """原子写：先写同目录临时文件再 os.replace，避免并发/中断写坏 JSON。

    调用方负责持锁（见 locked()）；本函数自身不加锁，否则同进程重入会死锁。
    """
    d = os.path.dirname(PROG) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".progress.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, PROG)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


# 领域别名 → progress.json 中实际存在的领域名。
# 历史原因：数据库进度存在 `sql` 下（没有顶层 `database`），工具链存在 `tools` 下。
# 用户/教学时可能说"数据库""区块链"等，这里统一映射，避免 get database 直接报错。
DOMAIN_ALIASES = {
    "database": "sql", "db": "sql", "mysql": "sql", "sqlite": "sql",
    "数据库": "sql", "sql数据库": "sql",
    "工具链": "tools", "工具": "tools", "git": "tools", "github": "tools",
    "区块链": "blockchain", "区块链知识栈": "blockchain",
    "智能合约": "smart-contract", "容器": "container", "容器化": "container",
    "后端": "backend", "前端": "vue",
}


def resolve_domain(data, domain):
    """把别名/中文叫做映射到实际领域名；已存在的名字原样返回。"""
    if domain in data.get("languages", {}) or domain in data:
        return domain
    alias = DOMAIN_ALIASES.get(domain) or DOMAIN_ALIASES.get(str(domain).lower())
    if alias and (alias in data.get("languages", {}) or alias in data):
        return alias
    return domain


def locate(data, domain):
    domain = resolve_domain(data, domain)
    if domain in data.get("languages", {}):
        return data["languages"][domain]
    if domain in data:
        return data[domain]
    return None


def all_areas(data):
    """自动发现所有领域：languages 下的每个语言 + 所有形如 {concepts:...} 的顶层键。

    不再硬编码领域名，避免新增领域（java / container / backend / dapp 等）
    在 list 总览里被静默漏掉。
    """
    areas = list(data.get("languages", {}).keys())
    for dom, val in data.items():
        if dom in ("languages", "milestones") or dom in areas:
            continue
        if isinstance(val, dict) and "concepts" in val:
            areas.append(dom)
    return areas


def cmd_list(data):
    for dom in all_areas(data):
        n = len(locate(data, dom).get("concepts", {}))
        print(f"{dom}: {n} 个概念")
    print(f"milestones: {len(data.get('milestones', []))} 条")


def cmd_get(data, domain, concept=None):
    area = locate(data, domain)
    if area is None:
        print(f"未找到领域: {domain}（现有领域: {', '.join(all_areas(data))}）", file=sys.stderr)
        sys.exit(1)
    concepts = area.get("concepts", {})
    if concept:
        c = concepts.get(concept)
        if c is None:
            print(f"未找到概念: {concept}", file=sys.stderr)
            sys.exit(1)
        print(f"{concept}: mastery={c.get('mastery')}, lastPracticed={c.get('lastPracticed')}")
        if c.get("notes"):
            print(f"  notes: {c['notes']}")
    else:
        for name, c in concepts.items():
            print(f"{name}: {c.get('mastery')} (last: {c.get('lastPracticed') or '无'})")
        if area.get("weakPoints"):
            print("weakPoints:", ", ".join(area["weakPoints"]))


def cmd_update(domain, concept, field, value):
    if field not in ("mastery", "lastPracticed", "notes"):
        print(f"字段不支持: {field}（仅 mastery/lastPracticed/notes）", file=sys.stderr)
        sys.exit(1)
    with locked():
        data = load()
        area = locate(data, domain)
        if area is None:
            area = data.setdefault(resolve_domain(data, domain), {"concepts": {}, "weakPoints": [], "exercises": []})
            print(f"ℹ️ 新领域已初始化: {resolve_domain(data, domain)}")
        c = area.setdefault("concepts", {}).setdefault(concept, {"mastery": "未学过", "lastPracticed": "", "notes": ""})
        c[field] = value
        save(data)
    print(f"✓ 已更新 {domain}/{concept}.{field} = {value}")


def cmd_add_note(domain, concept, note):
    with locked():
        data = load()
        area = locate(data, domain)
        if area is None:
            area = data.setdefault(resolve_domain(data, domain), {"concepts": {}, "weakPoints": [], "exercises": []})
            print(f"ℹ️ 新领域已初始化: {resolve_domain(data, domain)}")
        c = area.setdefault("concepts", {}).setdefault(concept, {"mastery": "未学过", "lastPracticed": "", "notes": ""})
        c["notes"] = note
        save(data)
    print(f"✓ 已写备注 {domain}/{concept}")


def cmd_where():
    print(f"SKILL_DIR = {SKILL_DIR}")
    print(f"PROGRESS  = {PROG}  ({'存在' if os.path.exists(PROG) else '不存在，首次读写时自动创建'})")
    print(f"EXAMPLE   = {EXAMPLE}  ({'存在' if os.path.exists(EXAMPLE) else '缺失'})")
    print(f"python    = {sys.executable}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("用法: tutor_progress.py {where|list|get <领域> [概念]|update <领域> <概念> <字段> <值>|add-note <领域> <概念> <备注>}", file=sys.stderr)
        sys.exit(1)
    cmd = args[0]
    if cmd == "where":
        cmd_where()
        sys.exit(0)
    if cmd == "list":
        cmd_list(load())
    elif cmd == "get":
        cmd_get(load(), *args[1:3])
    elif cmd == "update":
        cmd_update(*args[1:5])
    elif cmd == "add-note":
        cmd_add_note(args[1], args[2], " ".join(args[3:]))
    else:
        print(f"未知命令: {cmd}", file=sys.stderr)
        sys.exit(1)
