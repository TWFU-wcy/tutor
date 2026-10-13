# 开发工具链教学指南

## 工具清单

| 工具 | 教学内容 |
|------|---------|
| Git | init/add/commit/push/pull/branch/merge/rebase/log/diff/stash/cherry-pick |
| GitHub / Gitee | 仓库管理、Issue、PR/MR、Fork、Code Review、Actions/CI、Pages |
| 终端 | 常用命令、包管理器（npm/pip/cargo）、环境变量、SSH 配置 |
| IDE | VS Code 插件生态、Remix、Hardhat/Foundry 脚手架、调试器 |
| 包管理 | npm/yarn/pnpm、pip/poetry、Solidity 版本管理（solc） |
| 区块链工具 | MetaMask 钱包、Remix IDE、Hardhat、Foundry、Etherscan、测试网水龙头 |

## 教学策略

以任务驱动，每个命令先说"它做什么"，再说"为什么要用它"，最后动手执行。

---

## 开发工具链教学流程

**适用场景**：用户学 Git、GitHub、Gitee、终端、IDE 等开发工具（"怎么用 Git"、"怎么把代码传到 GitHub"、"Gitee 怎么 fork"）。

### 教学节奏

1. 用户说想做什么 → 告诉他用什么命令
2. 解释命令的作用和参数含义
3. 让用户执行，观察输出
4. 如果出错 → 分析错误信息，教排查方法
5. 完成后回顾整个流程，帮用户建立"命令 → 目的"的映射

### 常见任务模板

| 用户想做什么 | 教学路径 |
|------------|---------|
| 把代码上传到 GitHub | git init → add → commit → remote add → push |
| 同步别人的项目 | fork → clone → pull request |
| 多人协作 | branch → commit → push → pull request → code review → merge |
| 修复 bug 不影响主线 | branch → fix → merge back → delete branch |
| 代码改乱了想回退 | git log → git diff → git reset / git stash |

### Git 常见坑的教学

- merge 冲突怎么解决
- commit 了但还没 push，想撤回怎么办
- 不小心把大文件提交了怎么清理
- .gitignore 怎么用
