---
name: "gitcommit-agent"
description: "提交前可选 AI 深度审查：并行执行单元测试复核（unit-test-runner）与综合质量审查（security-engineer），通过后调用 git-save 提交。git commit 已由 pre-commit 钩子自动跑确定性闸门（pytest + 静态安全扫描），本技能用于需要大模型语义审查时手动触发。"
---

# gitcommit-agent —— 提交前 AI 深度审查（可选）

`git commit` 本身已由 `.githooks/pre-commit` 自动执行确定性闸门（单元测试 + 静态安全扫描），无需手动调用即可拦截明显问题。

本技能用于在需要「大模型语义审查」时，额外做一次深度体检后再提交。

## 执行步骤
1. 并行执行两个审查技能（务必同时进行，而非串行等待）：
   - `unit-test-runner`：复核 / 补充单元测试并跑通。
   - `security-engineer`：综合质量审查（安全、注释、规范、性能等）。
   - 并行可借助两个并行的子代理（general_purpose_task）分别执行上述两个技能实现。
2. 汇总两个审查结论：若均无阻断级问题 → 进入提交；否则报告问题、停止。
3. 调用 `git-save` 提交（`git commit` 会再次触发 pre-commit 的确定性闸门做最后把关）。

## 约定
- 两个审查必须并行启动，不得串行。
- 本技能是可选增强，不替代 pre-commit 的自动闸门。