# 进度追踪 Schema 与流程

## 存储方案

**本地进度文件（主要）：**
- 路径：`{{SKILL_DIR}}/references/progress.json`（`{{SKILL_DIR}}` 解析见 SKILL.md 的「路径约定」）
- 格式：结构化 JSON，精确读写
- **权威源**：所有进度数据以 progress.json 为准

**里程碑文件（辅助）：**
- 路径：`{{SKILL_DIR}}/references/milestones.md`
- 用途：只记录关键里程碑（如"已掌握 Python 基础"），方便跨对话快速回忆
- 时机：用户达到新的掌握程度等级时追加一行
- **与 progress.json 的关系**：先写 progress.json，再追加 milestones.md。progress.json 是权威源，milestones.md 只做辅助召回
- **注意**：多数 agent 没有可靠的跨会话记忆，教学连续性完全依赖这两个文件

## progress.json 数据结构

```json
{
  "languages": {
    "python": {
      "concepts": {
        "变量与数据类型": {
          "mastery": "熟练掌握",
          "lastPracticed": "2026-04-30",
          "notes": "列表推导式还需加强"
        },
        "函数": {
          "mastery": "初步了解",
          "lastPracticed": "2026-04-29",
          "notes": ""
        }
      },
      "weakPoints": ["列表推导式", "异常处理"],
      "exercises": [
        {"name": "练习1：变量赋值", "domain": "python", "concept": "变量与数据类型", "date": "2026-04-30", "result": "通过"}
      ]
    }
  },
  "blockchain": {
    "concepts": {
      "哈希函数": {"mastery": "能独立使用", "lastPracticed": "2026-05-07", "notes": ""},
      "Solidity 基础语法": {"mastery": "初步了解", "lastPracticed": "2026-05-06", "notes": "mapping 和 struct 还不太熟"},
      "重入攻击防护": {"mastery": "未学过", "lastPracticed": "", "notes": ""}
    },
    "weakPoints": ["mapping", "Gas 优化"],
    "exercises": [
      {"name": "练习1：ERC20 合约", "domain": "blockchain", "concept": "Solidity 基础语法", "date": "2026-05-06", "result": "未通过", "notes": "msg.sender 和 address(this) 混淆"}
    ]
  },
  "tools": {
    "concepts": {
      "git commit": {"mastery": "熟练掌握", "lastPracticed": "2026-05-07", "notes": ""},
      "GitHub Pull Request": {"mastery": "初步了解", "lastPracticed": "2026-05-05", "notes": ""}
    },
    "weakPoints": ["rebase"],
    "exercises": []
  },
  "sql": {
    "concepts": {
      "SQL 基础查询": {"mastery": "能独立使用", "lastPracticed": "2026-05-07", "notes": ""},
      "JOIN 多表连接": {"mastery": "初步了解", "lastPracticed": "2026-05-06", "notes": "LEFT JOIN 和 INNER JOIN 的区别容易搞混"},
      "索引原理": {"mastery": "未学过", "lastPracticed": "", "notes": ""}
    },
    "weakPoints": ["LEFT JOIN", "子查询"],
    "exercises": [
      {"name": "练习1：用户订单查询", "domain": "sql", "concept": "SQL 基础查询", "date": "2026-05-07", "result": "通过", "notes": ""}
    ]
  },
  "milestones": [
    {"lang": "python", "level": "初步了解", "date": "2026-04-30"},
    {"domain": "blockchain", "concept": "哈希函数", "level": "能独立使用", "date": "2026-05-07"}
  ]
}
```

### 字段说明
- `languages`：编程语言进度（键为语言名：vue / go / java …）
- 其余**顶层领域键**（`sql`、`blockchain`、`blockchain-deploy`、`smart-contract`、`dapp`、`container`、`backend` …）：结构与 languages 下的语言相同（`concepts` / `weakPoints` / `exercises`）
- 领域名**不硬编码**，脚本自动发现；新增领域用 `update` 时自动初始化
- 别名：`database` / `db` / `数据库` → `sql`；`工具链` / `git` → `tools`；`智能合约` → `smart-contract`
- `exercises` 字段：
  - `domain`：练习归属领域（`"vue"` / `"go"` / `"sql"` / `"blockchain"` / `"smart-contract"` 等）
  - `notes`：具体错因或备注
- `milestones` 字段：
  - `domain`：里程碑所属领域（与 `lang` 二选一）
  - `concept`：具体知识点名称

## 掌握程度等级

| 等级 | 含义 | 教学策略 |
|------|------|---------|
| 未学过 | 从未接触该知识点 | 从难到易详细引导 |
| 初步了解 | 知道概念但不能独立写代码 | 中等引导，跳过基础定义 |
| 能独立使用 | 能独立完成常见任务 | 回忆式引导，直接进入进阶 |
| 熟练掌握 | 能灵活运用并理解底层原理 | 几乎不提问，直接高阶应用 |

## 降级规则（两阶段机制）

用脚本读取进度时（`get <领域>` 或 `list`），检查每个知识点的 lastPracticed：

### 第一阶段：预警（12-14 天）

距上次练习 **12-14 天** 且掌握程度为「能独立使用」或「熟练掌握」时：
- 教学开始时提示用户："XX 知识点已经快两周没练了，要不要复习一下？"
- 不自动降级，等用户决定是否复习
- 用户说"不用复习" → 跳过预警，进入第二阶段判断

### 第二阶段：降级（>14 天）

距上次练习 **>14 天** 时执行降级：
- 「能独立使用」→ 降为「初步了解」
- 「熟练掌握」→ 降为「能独立使用」
- 「初步了解」和「未学过」不降级

### 降级范围限制

- 单次教学开始时最多降级 1 个等级（不会从「熟练掌握」直接跳到「初步了解」）
- 降级后在 notes 中追加：`"⚠️ 已降级：距上次练习 X 天"`
- 降级后不自动写 milestones.md，等用户实际练习后再决定是否重新升级

### 降级备注清理

- 用户重新练习并升级时，清理 notes 中的降级备注（`"⚠️ 已降级：..."`）
- 保留 notes 中用户原有的其他备注内容

## 新领域初始化

当用户开始学习 progress.json 中不存在的新领域时：
1. **新语言**：在 languages 下创建空结构：`{"concepts": {}, "weakPoints": [], "exercises": []}`
2. **新领域知识点**：在对应领域下自动追加
3. 不需要用户手动"注册"，检测到即自动创建

## 错误处理

- **文件不存在**：创建空的 progress.json（`{"languages":{},"milestones":[]}` 即可，领域会在首次 `update` 时自动初始化），不中断教学
- **文件内容损坏**：备份为 `progress.json.bak`，创建新的空 progress.json，在 notes 中记录"文件已重建"
- **读取失败**：当轮教学照常进行，结束后尝试重新写入；仍然失败则提示用户检查文件权限

## 追踪时机

以下任一情况视为一次教学结束，触发进度更新：
1. 用户告别（"再见"、"拜拜"、"今天就到这"等）
2. 用户切换主题（从编程学习切换到其他无关话题）
3. 用户完成一个练习或作业
4. 对话即将结束（用户长时间无回复后的新消息，视为新一轮）
5. 用户主动说"更新进度"或"记录一下"

## 读写流程

1. **教学开始时**：用脚本读取进度（含降级检查），用于进度感知规则
2. **教学过程中**：根据用户表现判断掌握程度变化
3. **教学结束时**：更新对应知识点的 mastery、lastPracticed、notes
4. **里程碑时**：先写 progress.json，再追加一行到 milestones.md

**读写方式（用脚本，省 token）：**
不要用文件读取工具全文加载 progress.json（约 16K token），用 `{{SKILL_DIR}}/scripts/tutor_progress.py`：

- `where` → 报告脚本自身与进度文件的真实位置
- `list` → 查看所有领域及概念数
- `get <领域> [概念]` → 只输出该领域/概念的小片段
- `update <领域> <概念> <字段> <值>` → 精准改单字段（字段：mastery / lastPracticed / notes）
- `add-note <领域> <概念> <备注>` → 追加/覆盖备注

**写权限提示**：会话若只能写工作目录（DSH 的 `workspace-write`、只读沙箱等），写不进技能目录的 progress.json。写入被拒时先告知用户放开该目录写权限，再更新进度（读取不受影响）。

**并发安全**：脚本写入用「临时文件 + 原子替换」并加文件锁，多个 agent 同时读写同一份进度不会写坏文件。

## 进度查询

用户说"我的进度"、"我学到哪了"、"各语言情况"、"区块链学到哪了"时：
1. 用 `tutor_progress.py list` + `get <领域>` 读取（含降级检查），不要全文加载
2. 按领域汇总展示
3. 给出下一步学习建议

**展示格式：**
```
📊 学习进度总览
━━━━━━━━━━━━━━

🐍 编程语言
  Python（已学 5 个概念）
    ✅ 熟练掌握：变量与数据类型
    🟡 能独立使用：函数、循环
    🟠 初步了解：列表推导式、异常处理
    ⚠️ 薄弱：列表推导式、异常处理

⛓️ 区块链（已学 3 个概念）
  ✅ 熟练掌握：哈希函数
  🟡 能独立使用：区块结构
  🟠 初步了解：Solidity 基础语法
  ⚠️ 薄弱：mapping、Gas 优化

🗄️ 数据库（已学 2 个概念）
  🟡 能独立使用：SQL 基础查询
  🟠 初步了解：JOIN 多表连接
  ⚠️ 薄弱：LEFT JOIN、子查询

🔧 开发工具（已学 4 个概念）
  ✅ 熟练掌握：git commit、git push
  🟡 能独立使用：git branch
  🟠 初步了解：GitHub Pull Request
  ⚠️ 薄弱：rebase

📝 练习统计：通过 12 / 未通过 3
🎯 建议：复习 Solidity mapping，然后学重入攻击防护
━━━━━━━━━━━━━━
```

**按需展示**：如果用户只问某个领域（"区块链进度"），只展示该领域，不展开其他领域。

## 多语言项目引导

当用户要做一个运用多个编程语言的项目时：
1. 用 `tutor_progress.py list` + 按需 `get`，查看各语言的学习进度
2. 识别哪些语言/概念已经够用，哪些还需要补
3. 制定学习路径：先补哪个语言的哪些知识点
4. 在项目推进中，对用户已掌握的部分少引导，对薄弱部分多引导
