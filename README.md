# tutor · 苏格拉底式学习助手

一个学习技能（Agent Skill）：用苏格拉底式提问引导你学编程、区块链、数据库和开发工具链，并把**掌握程度、薄弱点、练习记录持久化到本地**，下次打开接着上次继续。

不直接给答案，而是分层提问让你自己推导；答错给提示而非答案；连续错两次就直接讲。进度会随练习自动升降级。

## 特性

- **苏格拉底式教学**：递进式提问、常识跳过、按掌握程度动态调整策略
- **进度持久化**：每个知识点的掌握程度 / 最近练习 / 备注都记在本地，跨会话不丢
- **省 token 的进度读写**：配套 CLI 精准读写单字段，不必把整个进度文件（约 35KB）塞进上下文
- **练习与薄弱点有地方放**：`exercise` 记错题、`weak` 记薄弱点，出题时优先覆盖
- **里程碑自动成文**：`milestone` 追加后自动渲染出人类可读的 `milestones.md`
- **自动降级**：超过 14 天没练的知识点自动降一级，12-14 天时先提醒复习
- **四种模式**：苏格拉底引导 / 直接讲解 / 出题练习 / 项目实战（说「别问了」「出题」即可切换）
- **领域指南按需加载**：区块链、数据库、工具链各自独立指南，避免一次性灌满上下文
- **多目标并行规划**：考证 + 升学 + 学习路径排期，主线/副线/留白，按 deadline 倒推
- **写入安全**：临时文件 + 原子替换，写一半被打断也不会损坏数据；文件坏了自动备份重建

## 安装

技能就是一个目录，把它放到你的 agent 会扫描的技能目录即可。

```bash
git clone https://github.com/TWFU-wcy/tutor.git
```

然后按你的 agent 选择位置（`SKILL_DIR` = 技能目录绝对路径）：

| Agent | 用户级位置 | 项目级位置 |
| --- | --- | --- |
| 公共/共享 Agent 目录 | `~/.agents/skills/tutor` | `<项目>/.agents/skills/tutor` |
| DSH（DeepSeek Harness） | `<DSH_HOME>/skills/tutor`（默认 `~/.dsh/skills/tutor`） | `<项目>/.dsh/skills/tutor` |
| Claude Code | `~/.claude/skills/tutor` | `<项目>/.claude/skills/tutor` |
| Codex / Copilot 等 | `~/.codex/skills/tutor`、`~/.copilot/skills/tutor` | 见各自文档 |

例：

```bash
mkdir -p ~/.agents/skills && mv tutor ~/.agents/skills/tutor
python3 ~/.agents/skills/tutor/scripts/tutor_progress.py where   # 自检：路径 + 是否可写
python3 ~/.agents/skills/tutor/scripts/selftest.py               # 可选：跑 53 项自检
```

只要一个 Python 3（标准库即可，无第三方依赖）。可选设置 `TUTOR_PROGRESS` 覆盖进度文件位置。

## 用法

装好后正常说话即可触发：

- 「学 Python 的装饰器」「教教我 Go 的 goroutine」
- 「出题」「给我三道 SQL 题」
- 「我的进度」「我学到哪了」
- 「学 Solidity」「部署合约」「直接讲，别问了」

## 数据与隐私

仓库里**只有模板**，你的真实学习数据不会被提交：

| 文件 | 说明 | 是否入库 |
| --- | --- | --- |
| `references/progress.json` | 学习进度（权威源） | ❌ 已 gitignore，首次记录时自动创建 |
| `references/milestones.md` | 里程碑视图（由脚本生成） | ❌ 已 gitignore |
| `references/local.md` | 课表/校历路径、个人目标等 | ❌ 已 gitignore |
| `references/*.example.*` | 上面三者的模板 | ✅ |

从模板开始：`cp references/local.example.md references/local.md`，填上你的目标与资料路径。

## 目录结构

```
SKILL.md                        # 技能主体：教学模式、规则、路径约定、能力映射、写入时机
references/
  progress.example.json         # 进度文件模板
  milestones.example.md         # 里程碑视图格式说明
  local.example.md              # 个人配置模板
  guides/progress-schema.md     # 【开场必读】掌握程度等级、降级规则、读写流程
  guides/progress-data.md       # 【按需】数据结构、字段、别名、里程碑机制、展示格式
  guides/blockchain.md          # 区块链知识栈
  guides/database.md            # 数据库
  guides/tools.md               # 开发工具链
  guides/scenarios.md           # 教学场景处理（代码粘贴/调试/作业…）
  guides/question-templates.md  # 出题模板与难度分级
scripts/tutor_progress.py       # 进度读写 CLI（纯标准库）
scripts/selftest.py             # 自检脚本（53 项断言，不需要 pytest）
```

## 进度脚本

```bash
S=~/.agents/skills/tutor/scripts/tutor_progress.py

python3 $S where                                   # 自检：路径、是否可写
python3 $S list                                    # 各领域概念数 / 薄弱 / 练习数
python3 $S get vue                                 # 某领域全部概念 + 薄弱点 + 最近练习
python3 $S get sql "GROUP BY"                      # 单个概念（支持唯一子串匹配）
python3 $S update go 切片 mastery 能独立使用        # 掌握程度 / lastPracticed / notes
python3 $S add-note sql "LEFT JOIN" "和 INNER JOIN 混淆"
python3 $S weak sql add "HAVING 与 WHERE 的区别"    # 记薄弱点（remove 可移除）
python3 $S exercise sql "写 JOIN 查询" 未通过 "把 INNER 写成了 LEFT"
python3 $S milestone sql "JOIN 多表连接" 能独立使用 "完成 3 道练习"
python3 $S render                                  # 由 progress.json 重新生成 milestones.md
```

- 领域名自动发现，不用注册；中英文别名自动映射（`数据库`→`sql`、`工具链`/`git`→`tools` 等）
- 新领域、新概念首次写入时自动建结构；概念名写错会提示相似项
- 掌握程度：未学过 → 初步了解 → 能独立使用 → 熟练掌握
- 进度文件损坏会自动备份为 `progress.json.bak` 并重建；只读目录下读取照常、写入会给出提示

## 自检

```bash
python3 scripts/selftest.py
```

在临时目录里搭一份全新安装，逐条验证写入、别名、参数校验、只读目录、损坏恢复、历史格式兼容等 53 项断言，不会碰你的真实进度数据。

## License

[MIT](LICENSE)
