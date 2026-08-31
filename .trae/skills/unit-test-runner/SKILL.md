---
name: "unit-test-runner"
description: "为 Python 代码编写并执行 pytest 单元测试，并输出检测报告。当用户要求写单元测试、跑测试、或生成测试报告时调用。"
---

# 单元测试生成与执行

## 用途
为项目后端 Python 代码编写单元测试、执行测试，并输出检测报告。

## 环境约定
- 后端 Python 虚拟环境：`C:\Users\24866\.workbuddy\binaries\python\envs\default\Scripts\python.exe`（下文用 `<PY>` 表示）
- 测试框架：pytest + pytest-cov（用于覆盖率）
- 后端工作目录：`backend/`，所有测试命令必须在 `backend/` 目录下执行，确保能 `import app`
- 测试文件统一放在 `backend/tests/` 目录，命名为 `test_*.py`
- 若 `backend/tests/` 缺少 `conftest.py`，按需创建

## 执行步骤
1. 检查 pytest 是否已安装：`<PY> -m pytest --version`；若失败，先执行
   `<PY> -m pip install pytest pytest-cov`
2. 阅读目标代码，找出可测试的纯逻辑函数，优先覆盖无外部依赖的模块，例如：
   - `app/core/security.py`：密码哈希 / 校验、JWT 生成与解析
   - `app/core/rate_limit.py`：滑动窗口限流判断
   - `app/core/config.py`：配置读取
   - 其它含可提取逻辑的纯函数
3. 在 `backend/tests/` 下创建对应的测试文件，用 pytest 风格编写（`def test_xxx():` + `assert`）
4. 对「外部依赖」一律用 `unittest.mock`（`patch`/`MagicMock`）或 pytest 的 `monkeypatch` 隔离，**禁止发起真实请求**，包括：LLM、Embedding、Rerank、Milvus、HTTP 网络、真实 SQLite/数据库写入
5. 运行测试并在需要时附加覆盖率：
   `<PY> -m pytest tests/ -v`
   需要覆盖率时：`<PY> -m pytest tests/ --cov=app --cov-report=term-missing`
6. 根据 pytest 输出整理检测报告

## 检测报告格式（用中文输出给用户）
- 总览：通过 x 条 / 失败 y 条 / 跳过 z 条，覆盖率（如有）
- 逐条列出失败的用例名 + 报错关键信息
- 对每个失败给出简短修复建议
- 若全部通过，明确说明「全部通过」，并列出覆盖到的功能点

## 注意事项
- 测试不读写真实数据库、不碰真实 Milvus 文件、不调用外部 API，一律 mock
- 不要打印或写入 `.env` 中的密钥、token 等敏感信息
- 每个测试函数只验证一个行为，命名要能看出验证意图