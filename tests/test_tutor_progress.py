#!/usr/bin/env python3
"""tutor_progress.py 的回归测试（纯标准库 unittest）。

安全约定（每个用例都强制执行）：
  * 子进程一律用 TUTOR_PROGRESS / TUTOR_MILESTONES 指向临时目录，绝不读写技能目录里的真实数据；
  * setUp/tearDown 会对真实 progress.json / milestones.md 做哈希比对，一旦被改动立即失败。

运行：python -m unittest discover -s tests -v
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TESTS_DIR)
SCRIPT = os.path.join(REPO, "scripts", "tutor_progress.py")
REAL_PROGRESS = os.path.join(REPO, "references", "progress.json")
REAL_MILESTONES = os.path.join(REPO, "references", "milestones.md")

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def file_hash(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def seed_data():
    """一份带历史数据的最小进度文件（含旧版字段形状，用来验证兼容读取）。"""
    return {
        "languages": {
            "vue": {
                "concepts": {
                    "v-for 列表渲染": {
                        "mastery": "能独立使用",
                        "lastPracticed": "2026-04-30",
                        "notes": "需注意 :key",
                    }
                },
                "weakPoints": ["ref 与 reactive 的区别"],
                "exercises": [
                    {"name": "作业1", "date": "2026-04-29", "result": "通过"},
                    {
                        "name": "随堂练习",
                        "date": "2026-04-30",
                        "result": "通过",
                        "lang": "vue",
                        "concept": "reactive 响应式对象",
                    },
                ],
            }
        },
        "sql": {
            "concepts": {"GROUP BY 分组统计": {"mastery": "初步了解", "lastPracticed": "", "notes": ""}},
            "weakPoints": ["HAVING 与 WHERE 的区别"],
            "exercises": [],
        },
        "milestones": [
            {"lang": "vue", "level": "初步了解", "date": "2026-04-29", "note": "掌握 Vue 基础概念"},
            {"domain": "sql", "concept": "JOIN 多表连接", "level": "能独立使用", "date": "2026-05-20", "note": "完成 3 道练习"},
        ],
    }


class RealDataGuard(unittest.TestCase):
    """任何用例都不许改动技能目录里的真实用户数据。"""

    def setUp(self):
        self._real_state = {p: file_hash(p) for p in (REAL_PROGRESS, REAL_MILESTONES)}
        self.addCleanup(self._assert_real_untouched)

    def _assert_real_untouched(self):
        for path, before in self._real_state.items():
            self.assertEqual(
                file_hash(path), before,
                f"测试改动了真实数据文件：{path}（测试必须只用 TUTOR_PROGRESS/TUTOR_MILESTONES 指向临时目录）",
            )


class CliTestCase(RealDataGuard):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.mkdtemp(prefix="tutor-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.prog = os.path.join(self.tmp, "progress.json")
        self.milestones = os.path.join(self.tmp, "milestones.md")

    def run_cli(self, *args, prog=None):
        env = dict(os.environ)
        env["TUTOR_PROGRESS"] = prog or self.prog
        env["TUTOR_MILESTONES"] = self.milestones
        env["PYTHONIOENCODING"] = "utf-8"
        self.assertFalse(
            os.path.abspath(env["TUTOR_PROGRESS"]).startswith(REPO + os.sep),
            "测试必须把 TUTOR_PROGRESS 指向技能目录之外",
        )
        return subprocess.run(
            [sys.executable, SCRIPT, *args],
            cwd=self.tmp, env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )

    def seed(self, data=None):
        with open(self.prog, "w", encoding="utf-8") as f:
            json.dump(data if data is not None else seed_data(), f, ensure_ascii=False, indent=2)

    def load_prog(self):
        with open(self.prog, encoding="utf-8") as f:
            return json.load(f)

    def raw_prog(self):
        with open(self.prog, encoding="utf-8") as f:
            return f.read()

    def area(self, data, domain):
        if domain in data.get("languages", {}):
            return data["languages"][domain]
        return data[domain]


class EmptyInstallTests(CliTestCase):
    """S1：全新安装不能凭空出现示例数据。"""

    def test_first_list_reports_no_data(self):
        p = self.run_cli("list")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("尚无进度数据", p.stdout)
        for fake in ("python:", "sql:", "blockchain:", "milestones: 1"):
            self.assertNotIn(fake, p.stdout)
        self.assertFalse(os.path.exists(self.prog), "只读命令不应创建进度文件")

    def test_get_on_missing_file_exits_1(self):
        p = self.run_cli("get", "sql")
        self.assertEqual(p.returncode, 1)
        self.assertIn("未找到领域", p.stderr)
        self.assertFalse(os.path.exists(self.prog))

    def test_get_concept_on_missing_file_exits_1(self):
        p = self.run_cli("get", "sql", "SQL 基础查询")  # 旧版就是被示例数据"命中"的假概念
        self.assertEqual(p.returncode, 1)
        self.assertIn("未找到领域", p.stderr)

    def test_first_write_starts_from_empty_structure(self):
        p = self.run_cli("update", "python", "装饰器", "mastery", "初步了解")
        self.assertEqual(p.returncode, 0, p.stderr)
        data = self.load_prog()
        self.assertEqual(data["languages"], {}, "languages 不应含示例数据")
        self.assertEqual(data["milestones"], [])
        self.assertEqual(set(data), {"languages", "milestones", "python"})
        self.assertEqual(list(data["python"]["concepts"]), ["装饰器"])
        self.assertEqual(data["python"]["concepts"]["装饰器"]["mastery"], "初步了解")

    def test_where_runs(self):
        p = self.run_cli("where")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn(self.prog, p.stdout)
        self.assertIn(self.milestones, p.stdout)


class ReservedKeyTests(CliTestCase):
    """S2：保留键不能被当领域名，且必须保证文件未被改动。"""

    RESERVED = ("milestones", "languages", "exercises", "concepts", "weakPoints", "MILESTONES", "_comment")

    def assert_untouched_and_rejected(self, *args):
        before = self.raw_prog()
        p = self.run_cli(*args)
        self.assertEqual(p.returncode, 1, f"{args} 应当被拒绝，stdout={p.stdout!r}")
        self.assertIn("保留键", p.stderr)
        self.assertEqual(self.raw_prog(), before, f"{args} 改动了进度文件")
        return p

    def test_update_milestones_does_not_wipe_history(self):
        self.seed()
        p = self.assert_untouched_and_rejected("update", "milestones", "foo", "mastery", "未学过")
        self.assertIn("进度文件未被改动", p.stderr)
        self.assertEqual(len(self.load_prog()["milestones"]), 2)

    def test_update_languages_does_not_wipe_areas(self):
        self.seed()
        self.assert_untouched_and_rejected("update", "languages", "foo", "mastery", "未学过")
        self.assertIn("vue", self.load_prog()["languages"])

    def test_all_write_commands_reject_reserved(self):
        self.seed()
        cases = [
            ("update", "exercises", "x", "notes", "y"),
            ("add-note", "milestones", "x", "y"),
            ("weak", "milestones", "add", "x"),
            ("exercise", "milestones", "x", "通过"),
            ("milestone", "milestones", "x", "初步了解"),
        ]
        for case in cases:
            self.assert_untouched_and_rejected(*case)

    def test_case_insensitive_and_read_path(self):
        self.seed()
        self.assert_untouched_and_rejected("update", "MILESTONES", "x", "notes", "y")
        p = self.run_cli("get", "milestones")
        self.assertEqual(p.returncode, 1)
        self.assertIn("保留键", p.stderr)

    def test_every_reserved_key_rejected(self):
        self.seed()
        for key in self.RESERVED:
            with self.subTest(key=key):
                self.assert_untouched_and_rejected("update", key, "x", "notes", "y")

    def test_normal_domain_still_works(self):
        self.seed()
        p = self.run_cli("update", "数据库", "GROUP BY 分组统计", "mastery", "能独立使用")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.load_prog()["sql"]["concepts"]["GROUP BY 分组统计"]["mastery"], "能独立使用")


class ExerciseResultTests(CliTestCase):
    """G3：result 只能是 通过 / 未通过，记录 schema 固定。"""

    def test_dirty_result_rejected(self):
        self.seed()
        before = self.raw_prog()
        p = self.run_cli("exercise", "sql", "题", "通过（需修正引号和 ===")
        self.assertEqual(p.returncode, 1)
        self.assertIn("通过 / 未通过", p.stderr)
        self.assertEqual(self.raw_prog(), before)

    def test_unknown_result_rejected(self):
        self.seed()
        for bad in ("pass", "Pass", "通过 ", "部分通过"):
            p = self.run_cli("exercise", "sql", "题", bad)
            self.assertEqual(p.returncode, 1, f"{bad!r} 应被拒绝")
            self.assertIn("通过 / 未通过", p.stderr)

    def test_record_schema_is_authoritative(self):
        self.seed()
        p = self.run_cli("exercise", "sql", "写 JOIN 查询", "未通过", "把 INNER 写成了 LEFT")
        self.assertEqual(p.returncode, 0, p.stderr)
        rec = self.area(self.load_prog(), "sql")["exercises"][-1]
        self.assertEqual(set(rec), {"name", "date", "result", "domain", "notes"})
        self.assertEqual(rec["name"], "写 JOIN 查询")
        self.assertEqual(rec["result"], "未通过")
        self.assertEqual(rec["domain"], "sql")
        self.assertEqual(rec["notes"], "把 INNER 写成了 LEFT")
        self.assertRegex(rec["date"], DATE_RE)

    def test_notes_defaults_to_empty_string(self):
        self.seed()
        p = self.run_cli("exercise", "sql", "题", "通过")
        self.assertEqual(p.returncode, 0, p.stderr)
        rec = self.area(self.load_prog(), "sql")["exercises"][-1]
        self.assertEqual(rec["notes"], "")
        self.assertEqual(rec["domain"], "sql")

    def test_domain_reflects_alias(self):
        self.seed()
        p = self.run_cli("exercise", "数据库", "题", "通过")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.area(self.load_prog(), "sql")["exercises"][-1]["domain"], "sql")

    def test_legacy_records_still_readable(self):
        self.seed()
        p = self.run_cli("get", "vue")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("作业1", p.stdout)  # 旧记录没有 domain/notes，读命令不能崩


class ExerciseParsingTests(CliTestCase):
    """G8：结果按位置解析，概念名本身叫「通过」也能记录。"""

    def test_concept_named_like_result(self):
        self.seed()
        p = self.run_cli("exercise", "sql", "通过", "未通过")
        self.assertEqual(p.returncode, 0, f"stdout={p.stdout!r} stderr={p.stderr!r}")
        rec = self.area(self.load_prog(), "sql")["exercises"][-1]
        self.assertEqual(rec["name"], "通过")
        self.assertEqual(rec["result"], "未通过")

    def test_concept_named_result_with_note(self):
        self.seed()
        p = self.run_cli("exercise", "sql", "未通过", "通过", "反例：名字就叫未通过")
        self.assertEqual(p.returncode, 0, p.stderr)
        rec = self.area(self.load_prog(), "sql")["exercises"][-1]
        self.assertEqual(rec["name"], "未通过")
        self.assertEqual(rec["result"], "通过")
        self.assertEqual(rec["notes"], "反例：名字就叫未通过")

    def test_unquoted_multiword_name_still_works(self):
        self.seed()
        p = self.run_cli("exercise", "go", "写", "并发", "程序", "通过", "备注")
        self.assertEqual(p.returncode, 0, p.stderr)
        rec = self.area(self.load_prog(), "go")["exercises"][-1]
        self.assertEqual(rec["name"], "写 并发 程序")
        self.assertEqual(rec["result"], "通过")
        self.assertEqual(rec["notes"], "备注")

    def test_explicit_result_flag(self):
        self.seed()
        p = self.run_cli("exercise", "python", "装饰器", "实践", "--result", "通过", "备注A")
        self.assertEqual(p.returncode, 0, p.stderr)
        rec = self.area(self.load_prog(), "python")["exercises"][-1]
        self.assertEqual(rec["name"], "装饰器 实践")
        self.assertEqual(rec["result"], "通过")
        self.assertEqual(rec["notes"], "备注A")

    def test_missing_result_token(self):
        self.seed()
        before = self.raw_prog()
        p = self.run_cli("exercise", "sql", "题", "某个结果")
        self.assertEqual(p.returncode, 1)
        self.assertIn("通过 / 未通过", p.stderr)
        self.assertEqual(self.raw_prog(), before)

    def test_too_few_args(self):
        self.seed()
        p = self.run_cli("exercise", "sql", "题")
        self.assertEqual(p.returncode, 1)
        self.assertIn("参数不足", p.stderr)


class RoundTripTests(CliTestCase):
    """load/save 往返：写入不丢历史，损坏可恢复。"""

    def test_update_preserves_history(self):
        self.seed()
        before = self.load_prog()
        p = self.run_cli("update", "sql", "GROUP BY 分组统计", "mastery", "能独立使用")
        self.assertEqual(p.returncode, 0, p.stderr)
        after = self.load_prog()
        self.assertEqual(after["milestones"], before["milestones"], "milestones 不应被写入命令改动")
        self.assertEqual(after["languages"], before["languages"], "其它领域不应被改动")
        self.assertEqual(after["sql"]["weakPoints"], before["sql"]["weakPoints"])
        self.assertEqual(after["sql"]["concepts"]["GROUP BY 分组统计"]["mastery"], "能独立使用")
        self.assertIn("v-for 列表渲染", after["languages"]["vue"]["concepts"])

    def test_repeated_writes_are_stable(self):
        self.seed()
        for value in ("初步了解", "能独立使用", "熟练掌握"):
            p = self.run_cli("update", "go", "切片", "mastery", value)
            self.assertEqual(p.returncode, 0, p.stderr)
        data = self.load_prog()
        self.assertEqual(data["go"]["concepts"]["切片"]["mastery"], "熟练掌握")
        self.assertEqual(len(data["milestones"]), 2)

    def test_weak_exercise_milestone_roundtrip(self):
        self.seed()
        self.assertEqual(self.run_cli("weak", "go", "add", "goroutine 泄漏").returncode, 0)
        self.assertEqual(self.run_cli("weak", "go", "remove", "goroutine 泄漏").returncode, 0)
        self.assertEqual(self.run_cli("add-note", "go", "切片", "底层数组共享").returncode, 0)
        p = self.run_cli("milestone", "go", "切片", "能独立使用", "完成 3 道练习")
        self.assertEqual(p.returncode, 0, p.stderr)
        data = self.load_prog()
        self.assertEqual(self.area(data, "go")["weakPoints"], [])
        self.assertEqual(self.area(data, "go")["concepts"]["切片"]["notes"], "底层数组共享")
        self.assertEqual(data["milestones"][-1]["concept"], "切片")
        self.assertEqual(data["milestones"][-1]["domain"], "go")

    def test_render_writes_isolated_view(self):
        self.seed()
        p = self.run_cli("render")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(os.path.exists(self.milestones), "milestones 视图应落在 TUTOR_MILESTONES 指定的位置")
        with open(self.milestones, encoding="utf-8") as f:
            body = f.read()
        self.assertIn("掌握 Vue 基础概念", body)   # 旧字段 lang/note 也要渲染出来
        self.assertIn("JOIN 多表连接", body)
        self.assertIn("2026-04-29", body)

    def test_milestone_triggers_view(self):
        self.seed()
        p = self.run_cli("milestone", "sql", "索引原理", "初步了解")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(os.path.exists(self.milestones))

    def test_corrupted_file_is_backed_up_and_rebuilt(self):
        with open(self.prog, "w", encoding="utf-8") as f:
            f.write('{"languages": {,,,')
        p = self.run_cli("list")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(os.path.exists(self.prog + ".bak"), "损坏文件应备份为 .bak")
        self.assertIn("尚无进度数据", p.stdout)
        p = self.run_cli("update", "sql", "索引原理", "mastery", "初步了解")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.load_prog()["sql"]["concepts"]["索引原理"]["mastery"], "初步了解")

    def test_help_and_unknown_command(self):
        self.assertEqual(self.run_cli("--help").returncode, 0)
        self.assertIn("用法", self.run_cli("--help").stdout)
        p = self.run_cli("nope")
        self.assertEqual(p.returncode, 1)
        self.assertIn("未知命令", p.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
