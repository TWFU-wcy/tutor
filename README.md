# tutor

一个 Agent Skill：**苏格拉底式引导**的教学助手，覆盖编程语言、区块链、数据库、开发工具链。

教学时不直接给答案，而是分层提问让用户自己推导；答错先给提示、换个角度再问，连续答错两次才直接讲。每轮结束把掌握程度、薄弱点、练习记录写进本地进度文件，下次打开（换会话、换 agent）接着上次继续。

只依赖 Python 3 标准库。

## 安装

技能就是一个目录，放进 agent 会扫描技能的位置即可（各 agent 的技能目录见其文档）：

```bash
git clone <仓库地址> tutor
mkdir -p ~/.agents/skills && mv tutor ~/.agents/skills/tutor

S=~/.agents/skills/tutor/scripts
python3 $S/tutor_progress.py where   # 自检：技能路径、进度文件路径、目录是否可写
```

环境变量 `TUTOR_PROGRESS` 可覆盖进度文件位置。首次使用建议 `cp references/local.example.md references/local.md`，填上课表和个人目标路径——教学和规划会先读它。

## 用法

装好后直接说话触发：

- 「学 Python 的装饰器」「教教我 Go 的 goroutine」
- 「出题」「给我三道 SQL 题」
- 「我的进度」「我学到哪了」
- 「直接讲，别问了」

## 进度脚本

```bash
S=~/.agents/skills/tutor/scripts/tutor_progress.py

python3 $S where                                   # 路径与写权限自检
python3 $S list                                    # 各领域概念数 / 薄弱 / 练习数
python3 $S get vue                                  # 某领域全部概念 + 薄弱点 + 最近练习
python3 $S get sql "GROUP BY"                       # 单个概念（支持唯一子串匹配）
python3 $S update go 切片 mastery 能独立使用          # 字段：mastery / lastPracticed / notes
python3 $S add-note sql "LEFT JOIN" "和 INNER JOIN 混淆"
python3 $S weak sql add "HAVING 与 WHERE 的区别"      # remove 可移除
python3 $S exercise sql "写 JOIN 查询" 未通过 "把 INNER 写成了 LEFT"
python3 $S milestone sql "JOIN 多表连接" 能独立使用 "完成 3 道练习"
python3 $S render                                   # 由 progress.json 重新生成 milestones.md
```

- 领域名自动发现，不用注册；中英文别名自动映射（`数据库`→`sql`、`工具链`/`git`→`tools` 等）
- 新领域、新概念首次写入时自动建结构；概念名写错会提示相似项
- 掌握程度：未学过 → 初步了解 → 能独立使用 → 熟练掌握
- 写入用临时文件 + 原子替换；文件损坏自动备份为 `progress.json.bak` 并重建
- 目录只读时读取正常，写入会被拒绝并提示放开权限

## 目录结构

```
SKILL.md                        # 技能主体：路径约定、教学规则、进度写入时机、能力映射
references/
  progress.example.json         # 进度文件模板（progress.json 首次记录时自动生成）
  milestones.example.md         # 里程碑视图格式说明
  local.example.md              # 个人配置模板
  guides/progress-schema.md     # 【开场必读】掌握程度等级、降级规则、读写流程
  guides/progress-data.md       # 【按需】数据结构、字段、别名、里程碑机制、展示格式
  guides/blockchain.md          # 区块链知识栈
  guides/database.md            # 数据库
  guides/tools.md               # 开发工具链
  guides/scenarios.md           # 教学场景处理（代码粘贴、调试、作业…）
  guides/question-templates.md  # 出题模板与难度分级
scripts/tutor_progress.py       # 进度读写 CLI
scripts/selftest.py             # CLI 回归自检（开发者用，可选）
```

## 自检（可选）

```bash
python3 scripts/selftest.py
```

在临时目录搭一份全新安装跑 53 项断言，覆盖写入、别名映射、参数校验、只读目录、损坏恢复、旧格式兼容；改过脚本后跑一遍，确认没弄坏已有行为。

## License

[MIT](LICENSE)
