# 学习里程碑（格式说明）

> 这个 `.example.md` 只是给你看格式。真正在用的 `milestones.md` 由脚本**自动生成**，不需要你手写，也不用从本文件复制。

## 生成方式

```bash
python3 scripts/tutor_progress.py milestone <领域> <概念> <掌握程度> [备注]
```

命令会把条目追加进 `references/progress.json` 的 `milestones` 数组（权威源），然后重新渲染 `references/milestones.md`。也可以用 `render` 命令单独重生成视图。

## 视图格式

每行一条，按日期排序：

```
- 日期 · 知识点 → 掌握程度 · 说明
```

例如：

```
- 2026-04-30 · v-for 列表渲染 → 能独立使用 · 完成 2 个练习
- 2026-05-20 · JOIN 多表连接 → 能独立使用 · 完成 3 道 JOIN 练习
```

## 注意

- **不要手改 `milestones.md`**：它是生成物，下次渲染会覆盖
- 只记学习里程碑；课表、竞赛报名等非学习进度数据放 `local.md`
- 早期版本写在 `progress.json` 里的里程碑（用 `lang` + `note` 字段）会被自动识别并渲染，无需迁移
