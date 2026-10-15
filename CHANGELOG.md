# 更新日志

本文件记录 tutor 技能的版本变更。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循[语义化版本](https://semver.org/lang/zh-CN/)。技能的版本号写在 `SKILL.md` 的 frontmatter `version`。

## [1.1.0] - 2026-10-15

修掉审查发现的进度数据安全问题（示例数据污染、保留键静默清空历史、练习记录 schema 不一致），
统一文档里的路径/体量/引用描述，并补上自动化回归。

### 修复

- **S1 示例模板污染新用户进度**：`load()` 在 `progress.json` 不存在时不再读取 `references/progress.example.json`，
  改为直接构造全新空结构 `{"languages": {}, "milestones": []}`。全新安装的 `list` 只报「尚无进度数据」，
  不再出现「python: 1 个概念」这类假进度；`get sql` 不再命中示例里的「SQL 基础查询」；
  首次写入也不会把示例数据固化进真实进度文件。`references/progress.example.json` 缩成真正的空骨架，仅作 schema 示例。
- **S2 保留键可被当领域名并静默清空历史**：`update milestones foo mastery 未学过` 过去会把整个 `milestones` 数组
  替换成领域字典（`languages`、`exercises`、`concepts`、`weakPoints`、`_comment` 及版本号字段同理）。
  现在所有写命令遇到保留键都会输出中文错误并 `exit 1`，**进度文件保持原样**。
- **G3 exercise 记录 schema 三处不一致**：权威 schema 统一为 `{name, date, result, domain, notes}`
  （`domain` 自动取当前领域，`notes` 缺省为空字符串），脚本、`progress-data.md`、`question-templates.md` 三处一致；
  `result` 只接受 `通过` / `未通过`，非法值（例如「通过（需修正引号）」）报错拒绝写入——说明性文字请写进备注。
- **G4 交叉引用失效**：`references/guides/scenarios.md` 中指向「进度追踪」「出题模式」的引用，
  改为明确指向 `SKILL.md` 的对应章节（并补上出题模板文件路径）。
- **G5 路径约定自相矛盾**：`README.md` 与 `references/milestones.example.md` 改用技能目录绝对路径
  （`SKILL_DIR` / `{{SKILL_DIR}}`），与 `SKILL.md` 的「路径约定」说法一致。
- **G6 README 命令块踩坑**：不再用同一个 `S` 表示 scripts 目录和 .py 文件两种东西，
  进度命令统一写成 `$SKILL_DIR/scripts/tutor_progress.py`；安装块补上 PowerShell 版本；
  把会把目录嵌套成 `tutor/tutor` 的 `mkdir -p` + `mv` 换成直接 `git clone` 到目标目录（目标已存在时明确报错）
  加 `git pull` 更新，并说明「目标已存在」的处理方式。
- **G7 体量描述不一致**：删掉「该文件约 16K token」这类换算错误且指代不明的说法，
  统一为实测值 34029 字节（约 34 KB）并写明指代 `progress.json`；`SKILL.md`、`progress-schema.md` 同步。
- **G8 解析边界**：`exercise` 的结果改为稳定按位置解析，概念名本身叫「通过」时
  `exercise sql 通过 未通过` 能正确记成「名称=通过，结果=未通过」；
  不写引号的多词名称（`exercise go 写 并发 程序 通过`）和 `--result` 显式写法同时支持。
- **G9 无 CI / 无测试 / 无 CHANGELOG**：新增 `tests/test_tutor_progress.py`（30 个用例：
  空进度首跑、保留键攻击、`result` 非法值、解析边界、`load`/`save` 往返、损坏文件恢复等；
  全部把 `TUTOR_PROGRESS`/`TUTOR_MILESTONES` 指向临时目录，且每个用例前后比对真实数据哈希，
  一旦碰到真实个人数据立即失败）、`.github/workflows/ci.yml`（语法检查 + 跑测试 + 确认没写出个人数据文件）、
  以及本文件。

### 变更

- 里程碑视图路径默认跟随进度文件所在目录，并新增 `TUTOR_MILESTONES` 覆盖，
  使 `render` / `milestone` 可以在临时目录里测试而不会覆盖真实 `milestones.md`。
- `exercise <领域> <名称> <通过|未通过> [备注]` 中名称含空格时建议加引号（或用 `--result`），
  以免解析歧义；文档与错误提示已同步。

## [1.0.0] - 2026-10-13

首个稳定版：苏格拉底式教学 + 进度追踪（`progress.json` 权威源 + 自动生成的 `milestones.md` 视图），
覆盖编程语言、区块链、数据库、开发工具链四个方向。此前 0.x 的迭代记录见 git 历史。
