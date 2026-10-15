# tutor

一个给**计算机大类专业学生**用的 Agent Skill：**苏格拉底式引导**的教学助手，覆盖编程语言、区块链、数据库、开发工具链。

教学时不直接给答案，而是分层提问让用户自己推导；答错先给提示、换个角度再问，连续答错两次才直接讲。每轮结束把掌握程度、薄弱点、练习记录写进本地进度文件，下次打开（换会话、换 agent）接着上次继续。

只依赖 Python 3 标准库。版本变更见 [CHANGELOG.md](CHANGELOG.md)。

## 安装

技能就是一个目录，放进 agent 会扫描技能的位置即可（各 agent 的技能目录见其文档）。下面以公共 Agent 目录为例：macOS / Linux 是 `~/.agents/skills/tutor`，Windows 是 `%USERPROFILE%\.agents\skills\tutor`。

**macOS / Linux（bash / zsh）**

```bash
# 目标目录必须不存在或为空；git clone 会连同父目录一起创建
git clone https://github.com/TWFU-wcy/tutor.git ~/.agents/skills/tutor

SKILL_DIR=~/.agents/skills/tutor                  # 技能目录的绝对路径，下文命令统一用它
python3 "$SKILL_DIR/scripts/tutor_progress.py" where   # 自检：技能路径、进度文件路径、目录是否可写
```

**Windows（PowerShell）**

```powershell
git clone https://github.com/TWFU-wcy/tutor.git "$env:USERPROFILE\.agents\skills\tutor"

$SKILL_DIR = "$env:USERPROFILE\.agents\skills\tutor"
python "$SKILL_DIR\scripts\tutor_progress.py" where
```

> **目标目录已存在时**：`git clone` 会直接报错——这是有意的，用 `mkdir -p` + `mv`（或 PowerShell 的 `Move-Item`）覆盖已存在的目录时，源目录会被**嵌套**成 `tutor/tutor`，命令看似成功但技能装错位置。
> 已经有安装时改用更新：
>
> ```bash
> git -C ~/.agents/skills/tutor pull
> ```
>
> 想换安装位置，先删掉旧目录再 clone（`progress.json`、`milestones.md`、`local.md` 是本地数据，删目录前记得先备份）。

装好后可选手工初始化个人配置（**路径必须写全**，会话工作目录通常不是技能目录，相对路径会找不到文件）：

```bash
cp "$SKILL_DIR/references/local.example.md" "$SKILL_DIR/references/local.md"
```

环境变量 `TUTOR_PROGRESS` 可覆盖进度文件位置，`TUTOR_MILESTONES` 可覆盖里程碑视图位置（默认都放在技能目录的 `references/` 下）。

## 用法

装好后直接说话触发：

- 「学 Python 的装饰器」「教教我 Go 的 goroutine」
- 「出题」「给我三道 SQL 题」
- 「我的进度」「我学到哪了」
- 「直接讲，别问了」

## 进度脚本

`SKILL_DIR` 是技能目录的绝对路径（见上面安装一节）；Windows 上把 `python3` 换成 `python`（或 `py -3`）。

```bash
T="$SKILL_DIR/scripts/tutor_progress.py"           # 脚本的绝对路径

python3 "$T" where                                 # 路径与写权限自检
python3 "$T" list                                  # 各领域概念数 / 薄弱 / 练习数
python3 "$T" get vue                               # 某领域全部概念 + 薄弱点 + 最近练习
python3 "$T" get sql "GROUP BY"                    # 单个概念（支持唯一子串匹配）
python3 "$T" update go 切片 mastery 能独立使用       # 字段：mastery / lastPracticed / notes
python3 "$T" add-note sql "LEFT JOIN" "和 INNER JOIN 混淆"
python3 "$T" weak sql add "HAVING 与 WHERE 的区别"   # remove 可移除
python3 "$T" exercise sql "写 JOIN 查询" 未通过 "把 INNER 写成了 LEFT"
python3 "$T" milestone sql "JOIN 多表连接" 能独立使用 "完成 3 道练习"
python3 "$T" render                                # 由 progress.json 重新生成 milestones.md
```

PowerShell 等价写法（变量名换成 `$T`，其余参数一致）：

```powershell
$T = "$SKILL_DIR\scripts\tutor_progress.py"
python $T list
python $T get sql "GROUP BY"
python $T exercise sql "写 JOIN 查询" 未通过 "把 INNER 写成了 LEFT"
```

- 领域名自动发现，不用注册；中英文别名自动映射（`数据库`→`sql`、`工具链`/`git`→`tools` 等）
- 新领域、新概念首次写入时自动建结构；概念名写错会提示相似项
- 掌握程度：未学过 → 初步了解 → 能独立使用 → 熟练掌握
- 写入用临时文件 + 原子替换；文件损坏自动备份为 `progress.json.bak` 并重建
- 目录只读时读取正常，写入会被拒绝并提示放开权限
- 进度文件不存在时按空结构起步（不会拿示例数据充数）
- `exercise` 的名称含空格要加引号；`result` 只能是 `通过` / `未通过`，说明性文字写进备注

## 测试

回归测试只依赖标准库，用 `TUTOR_PROGRESS` / `TUTOR_MILESTONES` 指向临时目录，不会碰真实进度数据：

```bash
python3 -m unittest discover -s tests -v
```

## 目录结构

```
SKILL.md                        # 技能主体：路径约定、教学规则、进度写入时机、能力映射
CHANGELOG.md                    # 版本变更记录
references/
  progress.example.json         # progress.json 的 schema 示例（空骨架，脚本不读取）
  milestones.example.md         # 里程碑视图格式说明
  local.example.md              # 个人配置模板
  guides/progress-schema.md     # 【开场必读】掌握程度等级与读写流程
  guides/progress-data.md       # 【按需】数据结构、字段、别名、里程碑机制、展示格式
  guides/blockchain.md          # 区块链知识栈
  guides/database.md            # 数据库
  guides/tools.md               # 开发工具链
  guides/scenarios.md           # 教学场景处理（代码粘贴、调试、作业…）
  guides/question-templates.md  # 出题模板与难度分级
scripts/tutor_progress.py       # 进度读写 CLI
tests/test_tutor_progress.py    # 回归测试（unittest，纯标准库）
.github/workflows/ci.yml        # CI：语法检查 + 跑测试
```

## License

[MIT](LICENSE)
