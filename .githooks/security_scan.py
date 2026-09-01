#!/usr/bin/env python3
"""确定性静态安全扫描：由 pre-commit 钩子在 git commit 前自动调用，无需大模型。

仅覆盖可确定性判断的规则（与 security-engineer 的语义审查互补）：
  高危 HIGH（阻断提交）：真实密钥/私钥硬编码、密钥文件被提交、SQL 拼接注入、命令注入
  中危 MED（仅告警）   ：弱默认密码/占位密钥、弱哈希、debug 开启、CORS 过宽

结果输出到 stderr；退出码：0 = 放行（可含中危告警），1 = 存在高危，阻断提交。
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

CODE_EXTS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".vue", ".java", ".go", ".rb",
    ".php", ".sh", ".yml", ".yaml", ".json", ".toml", ".ini", ".cfg", ".sql",
}

# 无需密钥词、一眼即可判定的密钥格式（值形 -> 高危）
FORMAT_SECRETS = [
    ("私钥字段", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("AWS AccessKey", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub PAT", re.compile(r"\bghp_[A-Za-z0-9]{36}\b")),
    ("OpenAI 风格密钥", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("Slack Token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
]

SECRET_KEYWORD_RE = re.compile(
    r"api[_-]?key|access[_-]?key|secret[_-]?key|secret|password|passwd|token|private[_-]?key",
    re.IGNORECASE,
)
LONG_LITERAL_RE = re.compile(r"['\"]([A-Za-z0-9+/_\-]{16,})['\"]")

SQL_FSTRING_RE = re.compile(r"f['\"].*\b(select|insert|update|delete|where)\b.*\{", re.IGNORECASE)
CMD_INJECT_RE = re.compile(r"os\.(system|popen)\s*\([^)]*[+{]")

WEAK_LITERAL_RE = re.compile(
    r"['\"](1234567890|123456789|12345678|123456|admin123|password123|password|"
    r"root|qwerty|change-?me|changeme|your[-_][^'\"]*|example|placeholder|xxxx+|xxx+)['\"]",
    re.IGNORECASE,
)
WEAK_HASH_RE = re.compile(r"\b(md5|sha1)\s*\(", re.IGNORECASE)
DEBUG_RE = re.compile(r"\bdebug\s*=\s*(True|1)\b", re.IGNORECASE)
CORS_OPEN_RE = re.compile(r"allow_origins\s*=\s*\[\s*['\"]\*['\"]\s*\]")

PLACEHOLDER_TOKENS = (
    "changeme", "change-me", "change_me", "your", "example", "placeholder",
    "xxxx", "xxx", "replace", "dummy", "<",
)


def _looks_placeholder(v: str) -> bool:
    return any(t in v.lower() for t in PLACEHOLDER_TOKENS)


# 代码标识符特征：驼峰（handleChangePassword）、下划线（handle_pwd）、全大写常量（TITLE_MAX_LEN）
CAMEL_IDENT_RE = re.compile(r"^[a-z]+([A-Z][a-z0-9]*)+$|[A-Za-z]+(_[A-Za-z0-9]+)+$|^[A-Z][A-Z0-9_]+$")


def _looks_identifier(v: str) -> bool:
    """排除代码标识符误报：密钥通常含数字或符号（sk-xxx、base64 等）。"""
    return bool(CAMEL_IDENT_RE.fullmatch(v))


def _is_secret_filename(rel: str) -> bool:
    name = os.path.basename(rel).lower()
    if name == ".env":
        return True
    if name.startswith(".env."):
        return name not in (".env.example", ".env.sample", ".env.template")
    if os.path.splitext(name)[1].lower() in (".pem", ".p12", ".pfx", ".key"):
        return True
    if name in ("id_rsa", "id_ed25519", "id_ecdsa", "credentials.json"):
        return True
    if name in ("secrets.yml", "secrets.yaml", "secrets.json"):
        return True
    return False


def _snippet(line: str, n: int = 120) -> str:
    s = " ".join(line.split())
    return s if len(s) <= n else s[:n] + "..."


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def _check_line(findings: list, rel: str, lineno: int, line: str) -> None:
    for name, rx in FORMAT_SECRETS:
        if rx.search(line):
            findings.append((1, rel, lineno, f"硬编码{name}", ""))
            return
    if SQL_FSTRING_RE.search(line):
        findings.append((1, rel, lineno, "SQL 字符串拼接疑似注入", _snippet(line)))
        return
    if CMD_INJECT_RE.search(line):
        findings.append((1, rel, lineno, "命令拼接疑似注入", _snippet(line)))
        return
    if SECRET_KEYWORD_RE.search(line):
        m = LONG_LITERAL_RE.search(line)
        if m:
            val = m.group(1)
            if _looks_identifier(val):
                return  # 代码标识符（函数名/常量名）误报，跳过
            if _looks_placeholder(val):
                findings.append((0, rel, lineno, "疑似占位密钥（待确认）", ""))
            else:
                findings.append((1, rel, lineno, "硬编码密钥字面量", ""))
            return
        if WEAK_LITERAL_RE.search(line):
            findings.append((0, rel, lineno, "弱默认密码/占位密钥", ""))
    if WEAK_HASH_RE.search(line):
        findings.append((0, rel, lineno, "弱哈希（MD5/SHA1）", _snippet(line)))
    if DEBUG_RE.search(line):
        findings.append((0, rel, lineno, "debug 开启", _snippet(line)))
    if CORS_OPEN_RE.search(line):
        findings.append((0, rel, lineno, "CORS 过宽", _snippet(line)))


def main() -> int:
    try:
        root = _git("rev-parse", "--show-toplevel").strip()
        staged_raw = _git("diff", "--cached", "--name-only", "--diff-filter=ACMR")
    except subprocess.CalledProcessError:
        print("[security-scan] 无法读取 git 信息，跳过扫描（放行）", file=sys.stderr)
        return 0

    findings: list = []
    for rel in staged_raw.splitlines():
        rel = rel.strip()
        if not rel:
            continue
        if _is_secret_filename(rel):
            findings.append((1, rel, 0, "密钥文件被提交", ""))
        full = os.path.join(root, rel)
        if os.path.splitext(rel)[1].lower() not in CODE_EXTS or not os.path.isfile(full):
            continue
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as fh:
                for i, line in enumerate(fh, 1):
                    _check_line(findings, rel, i, line.rstrip("\n"))
        except OSError:
            continue

    highs = [f for f in findings if f[0] == 1]
    meds = [f for f in findings if f[0] == 0]

    if highs:
        print("[security-scan] 发现高危问题，阻断提交：", file=sys.stderr)
        for _, f, ln, rule, show in highs:
            loc = f if ln == 0 else f"{f}:{ln}"
            tail = f" -> {show}" if show else ""
            print(f"  - {loc} [{rule}]{tail}", file=sys.stderr)
    if meds:
        print("[security-scan] 中危告警（不阻断）：", file=sys.stderr)
        for _, f, ln, rule, show in meds:
            loc = f if ln == 0 else f"{f}:{ln}"
            tail = f" -> {show}" if show else ""
            print(f"  - {loc} [{rule}]{tail}", file=sys.stderr)
    if not findings:
        print("[security-scan] 未发现问题。", file=sys.stderr)

    return 1 if highs else 0


if __name__ == "__main__":
    raise SystemExit(main())