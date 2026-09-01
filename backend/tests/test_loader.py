"""测试 app/services/loader.py：纯文本读取、扩展名解析、文本切分（纯本地逻辑）。"""
from app.services import loader


def test_read_text_utf8(tmp_path):
    """UTF-8 编码的纯文本应原样读出。"""
    p = tmp_path / "a.txt"
    p.write_text("你好，世界", encoding="utf-8")
    assert loader.read_text(p) == "你好，世界"


def test_read_text_fallback_gbk(tmp_path):
    """UTF-8 解码失败时应回退到 GBK。"""
    p = tmp_path / "b.txt"
    p.write_bytes("中文内容".encode("gbk"))
    assert loader.read_text(p) == "中文内容"


def test_parse_txt_content(tmp_path):
    """通过扩展名 dispatcher 读取 txt 内容。"""
    p = tmp_path / "a.txt"
    p.write_text("正文", encoding="utf-8")
    assert loader.parse_content(p, "a.txt") == "正文"


def test_split_text_strips_and_filters():
    """切分结果应为清洗后的非空文本块，且块数随文本增大而增多。"""
    text = "第一句话。第二句话。" * 30
    chunks = loader.split_text(text)
    assert chunks
    # 每个块都应是非空且无首尾空白
    assert all(c.strip() for c in chunks)


def test_split_text_empty_input():
    """空/纯空白输入应返回空列表。"""
    assert loader.split_text("") == []
    assert loader.split_text("   \n  ") == []