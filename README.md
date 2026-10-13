# tutor · 苏格拉底式学习助手

一个**跨 agent 通用**的学习技能（Agent Skill）：用苏格拉底式提问引导你学编程、区块链、数据库和开发工具链，并把**掌握程度、薄弱点、练习记录持久化到本地**，跨会话、跨 agent 都能接着上次继续。

不直接给答案，而是分层提问让你自己推导；答错给提示而非答案；连续错两次就直接讲。进度会随练习自动升降级。

## 特性

- **苏格拉底式教学**：递进式提问、常识跳过、按掌握程度动态调整策略
- **进度持久化**：`progress.json` 记录每个知识点的掌握程度 / 最近练习 / 备注，跨会话不丢
- **省 token 的进度读写**：配套脚本精准读写单字段，避免把整个进度文件塞进上下文（约 16K token → 几百）
- **自动降级**：超过 14 天没练的知识点自动降一级，12-14 天时先提醒复习
- **四种模式**：苏格拉底引导 / 直接讲解 / 出题练习 / 项目实战（说「别问了」「出题」即可切换）
- **领域指南按需加载**：区块链、数据库、工具链各自独立指南，避免一次性灌满上下文
- **多目标并行规划**：考证 + 升学 + 学习路径排期，主线/副线/留白，按 deadline 倒推
- **并发安全**：进度写入用临时文件 + 原子替换 + 文件锁，多个 agent 同时用不会写坏文件

## 安装

技能就是一个目录，把它放到你的 agent 会扫描的技能目录即可。

```bash
git clone https://github.com/<你的用户名>/tutor.git
```

然后按你的 agent 选择位置（`SKILL_DIR` = 技能目录绝对路径）：

| Agent | 用户级位置 | 项目级位置 |
| --- | --- | --- |
| 公共/共享 Agent 目录（多 agent 复用） | `~/.agents/skills/tutor` | `<项目>/.agents/skills/tutor` |
| DSH（DeepSeek Harness） | `<DSH_HOME>/skills/tutor`（默认 `~/.dsh/skills/tutor`） | `<项目>/.dsh/skills/tutor` |
| Claude Code | `~/.claude/skills/tutor` | `<项目>/.claude/skills/tutor` |
| Codex / Copilot 等 | `~/.codex/skills/tutor`、`~/.copilot/skills/tutor` | 见各自文档 |

例：

```bash
mkdir -p ~/.agents/skills && mv tutor ~/.agents/skills/tutor
python3 ~/.agents/skills/tutor/scripts/tutor_progress.py where   # 确认自检通过
```

只要一个 Python 3（标准库即可，无第三方依赖）。可选设置环境变量 `TUTOR_SKILL_DIR` / `TUTOR_PROGRESS` 覆盖默认定位。

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
| `references/progress.json` | 你的学习进度（权威数据） | ❌ 已 gitignore，首次运行自动生成 |
| `references/milestones.md` | 里程碑记录 | ❌ 已 gitignore |
| `references/local.md` | 课表/校历路径、个人目标等 | ❌ 已 gitignore |
| `references/*.example.*` | 上面三者的模板 | ✅ |

从模板开始：`cp references/local.example.md references/local.md` 然后填上你的目标与资料路径。

## 目录结构

```
SKILL.md                        # 技能主体：教学模式、规则、路径约定、能力映射
references/
  progress.example.json         # 进度文件模板
  milestones.example.md         # 里程碑模板
  local.example.md              # 个人配置模板
  guides/progress-schema.md     # 进度 schema、升降级规则、读写流程
  guides/blockchain.md          # 区块链知识栈
  guides/database.md            # 数据库
  guides/tools.md               # 开发工具链
  guides/scenarios.md           # 教学场景处理（代码粘贴/调试/作业…）
  guides/question-templates.md  # 出题模板与难度分级
scripts/tutor_progress.py       # 进度精准读写 CLI（纯标准库）
```

## 进度脚本

```bash
python3 scripts/tutor_progress.py where                    # 报告自身与进度文件位置
python3 scripts/tutor_progress.py list                     # 各领域概念数
python3 scripts/tutor_progress.py get vue                  # 某领域全部概念
python3 scripts/tutor_progress.py get sql "索引原理"        # 单个概念
python3 scripts/tutor_progress.py update go 切片 mastery 能独立使用
python3 scripts/tutor_progress.py add-note sql "LEFT JOIN" "和 INNER JOIN 混淆"
```

- 领域名自动发现，不用注册；中英文别名会自动映射（`数据库`→`sql`、`工具链`→`tools` 等）
- 字段：`mastery` / `lastPracticed` / `notes`；掌握程度：未学过 → 初步了解 → 能独立使用 → 熟练掌握
- 进度文件损坏会自动备份为 `progress.json.bak` 并重建

## 跨 agent 说明

`SKILL.md` 里不写死任何工具名，而是用一张映射表说明"需要什么能力 → 各 agent 对应什么工具"；文件引用统一用 `{{SKILL_DIR}}` 占位符，并在「路径约定」一节给出解析真实路径的步骤。所以同一份技能可以同时装给 DSH、Claude Code、Codex 等使用，并共享同一份进度数据。

## License

[MIT](LICENSE)
