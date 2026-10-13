# 进度数据参考（按需查阅）

> 开场教学只需要 `progress-schema.md`。本文件是**数据层参考**：结构、字段、别名、里程碑机制、展示格式。
> 命令语法见 `SKILL.md`「进度追踪」。

## 数据结构

`references/progress.json`（权威源）：

```json
{
  "languages": {
    "vue": {
      "concepts": {
        "v-for 列表渲染": {"mastery": "能独立使用", "lastPracticed": "2026-04-30", "notes": "需注意 :key"}
      },
      "weakPoints": ["ref 与 reactive 的区别"],
      "exercises": [{"name": "随堂练习：v-for 渲染表格", "date": "2026-04-30", "result": "通过"}]
    }
  },
  "sql": {
    "concepts": {"GROUP BY 分组统计": {"mastery": "初步了解", "lastPracticed": "2026-05-12", "notes": ""}},
    "weakPoints": ["HAVING 与 WHERE 的区别"],
    "exercises": []
  },
  "milestones": [
    {"domain": "sql", "concept": "JOIN 多表连接", "level": "能独立使用", "date": "2026-05-20", "note": "完成 3 道 JOIN 练习"}
  ]
}
```

## 字段说明

**领域（area）**——`languages` 下的每个语言，以及任何顶层键，只要它形如：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `concepts` | 对象 | 知识点 → `{mastery, lastPracticed, notes}` |
| `weakPoints` | 数组 | 薄弱点，出题时优先覆盖 |
| `exercises` | 数组 | 练习记录，`{name, date, result}`，`result` 为 `通过` / `未通过` |

**概念（concept）**：

| 字段 | 取值 | 说明 |
| --- | --- | --- |
| `mastery` | 未学过 / 初步了解 / 能独立使用 / 熟练掌握 | 掌握程度 |
| `lastPracticed` | `YYYY-MM-DD` 或空 | 降级判断依据 |
| `notes` | 字符串 | 错因、备注、降级标记 |

**里程碑（`milestones` 数组）**：`{domain 或 lang, concept, level, date, note}`。
领域名放在 `domain` 或旧版的 `lang` 都能识别；说明字段新旧版是 `note` / `notes`，两种都能读。

**历史数据兼容**：早期版本写入的 `lang`、`note`、以及字段不全的 `exercises` 条目都能正常读取和渲染，不需要手工迁移。

## 领域自动发现与别名

领域列表**不硬编码**：`languages` 下的语言 + 所有含 `concepts` 的顶层键，都会被 `list` 识别。新增领域不需要注册，第一次写入时自动建结构。

以下别名会自动映射到规范领域名（无论该领域是否已存在）：

| 你可能会说 | 实际写入 |
| --- | --- |
| 数据库 / database / db / mysql / sqlite | `sql` |
| 工具链 / 工具 / git / github | `tools` |
| 区块链 / 区块链知识栈 | `blockchain` |
| 智能合约 | `smart-contract` |
| 容器 / 容器化 | `container` |
| 后端 / 前端 | `backend` / `vue` |

概念名支持**唯一子串匹配**（`get sql 索引` 能命中 `索引原理`）；匹配不到时会列出相近候选。

## 里程碑机制

- **权威源是 `progress.json` 的 `milestones` 数组**，用 `milestone` 命令追加
- `references/milestones.md` 是**自动生成的人类可读视图**（脚本每次追加后重新渲染，也可用 `render` 手动重生成）
- **不要手改 milestones.md**，改了下一次生成会被覆盖；要补记请用命令
- 视图格式：`日期 · 知识点 → 掌握程度 · 说明`（按日期排序）
- 只记学习里程碑，不要塞课表、竞赛报名等非学习进度数据——那些放 `local.md`

## 进度查询展示格式（完整版）

```
📊 学习进度总览
━━━━━━━━━━━━━━

🐍 编程语言
  vue（已学 29 个概念）
    ✅ 熟练掌握：v-for 列表渲染、:key 绑定
    🟡 能独立使用：组件通信 props/emit
    🟠 初步了解：ref 与 reactive
    ⚠️ 薄弱：v-model 修饰符

⛓️ 区块链（已学 15 个概念）
  ✅ 熟练掌握：哈希函数
  🟡 能独立使用：geth 基础操作
  🟠 初步了解：Solidity 基础语法
  ⚠️ 薄弱：Gas 优化

🗄️ 数据库 / SQL（已学 17 个概念）
  🟠 初步了解：数据库基础概念、数据类型、CRUD
  ⚠️ 薄弱：HAVING 与 WHERE 的区别

📝 练习统计：通过 12 / 未通过 3
🎯 建议：先补 Solidity 的 mapping，再做一道重入攻击防护题
━━━━━━━━━━━━━━
```

用户只问某个领域时，只展示该领域，不展开其他领域。数据来源：`list`（全局计数）+ `get <领域>`（概念与薄弱点）。

## 初始化与错误处理

| 情况 | 行为 |
| --- | --- |
| `progress.json` 不存在 | 只读命令返回模板骨架且**不落盘**；首次写命令时自动创建 |
| 文件内容损坏 | 备份为 `progress.json.bak`，重建空结构并提示 |
| 目录只读 | 读取正常；写入被拒并提示放开目录权限 |
| 概念名写错 | 自动提示相似概念；`update` 会新建并在 stderr 警告 |

## 相关文件

| 文件 | 作用 | 是否入库 |
| --- | --- | --- |
| `references/progress.json` | 学习进度权威源 | ❌ 本地数据 |
| `references/milestones.md` | 里程碑自动生成视图 | ❌ 本地数据 |
| `references/local.md` | 课表/校历路径、个人目标 | ❌ 本地数据 |
| `references/*.example.*` | 以上三者的模板 | ✅ |
| `scripts/tutor_progress.py` | 读写 CLI | ✅ |
