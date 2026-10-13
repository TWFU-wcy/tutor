#!/usr/bin/env python3
"""selftest.py — tutor_progress.py 的自检脚本（不需要 pytest，纯标准库）

做法：在一个临时目录里搭一份「全新安装」的技能骨架，把真实进度数据隔离在外，
然后逐条跑命令，断言输出与退出码。顺带验证脚本拷到别的目录也能正常工作。

用法:
  python3 scripts/selftest.py          # 全部通过则退出码 0
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_SCRIPT = os.path.join(HERE, "tutor_progress.py")
SRC_EXAMPLE = os.path.join(HERE, os.pardir, "references", "progress.example.json")

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}" + (f"\n     {detail}" if detail else ""))


def run(root, *args, expect=None):
    """在临时技能目录里执行命令，返回 (退出码, 合并输出)。"""
    env = dict(os.environ, TUTOR_PROGRESS=os.path.join(root, "references", "progress.json"))
    p = subprocess.run([sys.executable, os.path.join(root, "scripts", "tutor_progress.py"), *args],
                       capture_output=True, text=True, env=env)
    out = p.stdout + p.stderr
    if expect is not None:
        check(" ".join(args) or "(无参数)", p.returncode == expect,
              f"期望退出码 {expect}，实际 {p.returncode}\n     {out.strip()[:300]}")
    return p.returncode, out


def build_fresh_skill():
    root = tempfile.mkdtemp(prefix="tutor-selftest-")
    os.makedirs(os.path.join(root, "scripts"))
    os.makedirs(os.path.join(root, "references"))
    shutil.copy(SRC_SCRIPT, os.path.join(root, "scripts", "tutor_progress.py"))
    shutil.copy(SRC_EXAMPLE, os.path.join(root, "references", "progress.example.json"))
    return root


def main():
    root = build_fresh_skill()
    prog = os.path.join(root, "references", "progress.json")
    print(f"临时技能目录: {root}\n")

    print("【全新安装（无 progress.json）】")
    _, out = run(root, "where", expect=0)
    check("where 报告 SKILL_DIR 指向临时目录", root in out, out)
    _, out = run(root, "list", expect=0)
    check("list 不因缺文件而崩溃", "尚无进度数据" in out or "个概念" in out, out)
    check("只读命令不产生 progress.json", not os.path.exists(prog))

    print("\n【写入与别名映射】")
    run(root, "update", "python", "装饰器", "mastery", expect=1)  # 只有 3 个参数 → 应给用法提示
    run(root, "update", "python", "装饰器", "mastery", "初步了解", expect=0)
    check("update 后生成 progress.json", os.path.exists(prog))
    _, out = run(root, "list", expect=0)
    check("list 显示 python 领域", "python" in out, out)

    # 别名必须在目标领域尚不存在时也生效
    _, out = run(root, "update", "数据库", "索引原理", "mastery", "能独立使用", expect=0)
    data = json.load(open(prog, encoding="utf-8"))
    check("全新数据里「数据库」落成 sql 领域（不是新建 database/数据库）",
          "sql" in data and "数据库" not in data and "database" not in data, str(list(data.keys())))
    check("回显使用规范领域名", "已更新 sql/" in out, out)

    print("\n【参数校验：不再抛 Python 堆栈】")
    for args in (("get",), ("update", "sql"), ("add-note", "sql"), ("weak", "sql", "add"),
                 ("exercise", "sql", "练习一"), ("milestone", "sql", "概念")):
        code, out = run(root, *args)
        check(f"{' '.join(args)} 优雅退出", code == 1 and "Traceback" not in out,
              f"code={code}\n     {out.strip()[:200]}")
    _, out = run(root, "update", "sql", "x", "mastery", "乱填等级")
    check("非法掌握程度被拒绝", "掌握程度取值必须是" in out, out)
    _, out = run(root, "不存在的命令")
    check("未知命令给用法提示", "用法" in out and "Traceback" not in out, out)

    print("\n【概念名匹配】")
    _, out = run(root, "get", "sql", "索引原理", expect=0)
    check("精确匹配命中", "meta" not in out and "能独立使用" in out, out)
    _, out = run(root, "get", "sql", "索引", expect=0)
    check("唯一子串也能命中", "能独立使用" in out, out)
    code, out = run(root, "get", "sql", "完全不沾边的名字")
    check("匹配失败时给出候选提示", code == 1 and ("你是不是想找" in out or "未找到概念" in out), out)

    print("\n【exercises / weakPoints / milestone（原先缺失的能力）】")
    _, out = run(root, "exercise", "sql", "随堂练习：写 JOIN 查询", "未通过", "把 INNER 写成了 LEFT", expect=0)
    check("exercise 记录成功", "未通过" in out, out)
    _, out = run(root, "exercise", "sql", "随堂练习：写 JOIN 查询", "通过", expect=0)
    data = json.load(open(prog, encoding="utf-8"))
    ex = data["sql"]["exercises"]
    check("exercises 落盘且带日期与备注",
          len(ex) == 2 and ex[0]["result"] == "未通过" and ex[0].get("notes") and ex[0]["date"], str(ex))
    _, out = run(root, "exercise", "sql", "练习", "蒙对了")
    check("非法练习结果被拒绝", "结果必须是" in out, out)

    _, out = run(root, "weak", "sql", "add", "LEFT JOIN 与 INNER JOIN 的区别", expect=0)
    _, out = run(root, "weak", "sql", "add", "LEFT JOIN 与 INNER JOIN 的区别", expect=0)
    data = json.load(open(prog, encoding="utf-8"))
    check("薄弱点去重（重复添加不产生两条）", len(data["sql"]["weakPoints"]) == 1, str(data["sql"]["weakPoints"]))
    run(root, "weak", "sql", "remove", "LEFT JOIN 与 INNER JOIN 的区别", expect=0)
    data = json.load(open(prog, encoding="utf-8"))
    check("薄弱点可移除", data["sql"]["weakPoints"] == [], str(data["sql"]["weakPoints"]))
    _, out = run(root, "weak", "sql", "remove", "不存在的东西")
    check("移除不存在的薄弱点报错而非静默", "未找到薄弱点" in out, out)

    _, out = run(root, "milestone", "sql", "JOIN 多表连接", "能独立使用", "完成 3 道 JOIN 练习", expect=0)
    md = os.path.join(root, "references", "milestones.md")
    check("milestone 后生成 milestones.md", os.path.exists(md))
    body = open(md, encoding="utf-8").read() if os.path.exists(md) else ""
    check("milestones.md 含该条目", "JOIN 多表连接" in body and "能独立使用" in body, body[:300])
    _, out = run(root, "get", "sql", expect=0)
    check("get 汇总包含 weakPoints/exercises", "weakPoints" in out or "exercises" in out, out)

    print("\n【历史数据兼容（lang/domain、note/notes）】")
    data = json.load(open(prog, encoding="utf-8"))
    data["milestones"] += [
        {"lang": "vue", "level": "初步了解", "date": "2026-04-29", "note": "旧格式：用 lang + note"},
        {"domain": "go", "concept": "切片", "level": "能独立使用", "date": "2026-05-01"},
    ]
    json.dump(data, open(prog, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    run(root, "render", expect=0)
    body = open(md, encoding="utf-8").read()
    check("旧格式里程碑能渲染", "旧格式：用 lang + note" in body and "vue" in body, body[:400])

    print("\n【写入安全】")
    leftovers = [f for f in os.listdir(os.path.join(root, "references")) if f.endswith(".tmp")]
    check("没有残留临时文件", not leftovers, str(leftovers))
    check("没有残留 .lock 文件", not os.path.exists(prog + ".lock"))
    json.load(open(prog, encoding="utf-8"))
    check("progress.json 始终是合法 JSON", True)

    bak = prog + ".bak"
    open(prog, "w", encoding="utf-8").write("{ 这不是合法 JSON")
    _, out = run(root, "list", expect=0)
    check("损坏文件被接管并提示备份", os.path.exists(bak) and "损坏" in out, out)
    check("损坏后仍能继续工作", "个概念" in out or "尚无进度" in out, out)

    if os.name != "nt":
        print("\n【只读目录】")
        refs = os.path.join(root, "references")
        run(root, "update", "go", "goroutine", "mastery", "初步了解", expect=0)
        os.chmod(refs, 0o500)
        try:
            code, out = run(root, "list")
            check("只读时 list 仍能读取（exit 0）", code == 0 and "go" in out, f"code={code}\n     {out[:200]}")
            code, out = run(root, "update", "go", "channel", "mastery", "初步了解")
            check("只读时 update 给友好提示而非崩溃",
                  code == 1 and "Traceback" not in out and ("写" in out or "权限" in out), f"code={code}\n     {out[:200]}")
        finally:
            os.chmod(refs, 0o700)

    shutil.rmtree(root, ignore_errors=True)
    print(f"\n{'='*52}\n通过 {passed} 项，失败 {failed} 项")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
