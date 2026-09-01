---
name: "git-save"
description: "提交存档：暂存改动并执行 git commit。pre-commit 钩子会自动运行单元测试与静态安全扫描，通过才放行。当用户要求提交、存档、commit 时调用。"
---

# git-save —— 提交存档

把当前工作区改动暂存并提交。是否放行由 pre-commit 钩子（`.githooks/pre-commit`）自动把关，本技能不重复实现校验逻辑。

## 前置
- 已安装 pre-commit 钩子：`git config core.hooksPath .githooks`（若未设置，先执行一次）。

## 执行步骤
1. 确认钩子已安装：`git config --get core.hooksPath`，输出应为 `.githooks`；否则执行 `git config core.hooksPath .githooks`。
2. 获取提交信息：优先使用用户提供的 commit message（形如「<message>」）；若未提供，则用 `AskUserQuestion` 向用户询问。
3. 暂存全部改动：`git add -A`。
4. 提交：`git commit -m "<message>"`。
   - 提交时 pre-commit 会自动运行「单元测试 + 静态安全扫描」：
     - 全部通过 → 自动放行并提交，向用户报告提交消息与改动范围。
     - 任一失败（单测未通过 / 扫描发现高危）→ 提交被拒绝；把错误信息如实告知用户，不要重试、不要跳过钩子。

## 约定
- 禁止跳过钩子（禁止 `--no-verify`）。
- 仅提交用户明确要求提交的改动。
- 无需手动生成任何标记文件：单元测试与静态安全扫描由钩子自动执行。