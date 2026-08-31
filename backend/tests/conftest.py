"""pytest 全局配置：确保测试内能 import app 模块（无需真实连接数据库/外部服务）。"""
import sys
from pathlib import Path

# backend 目录加入 sys.path，使 `from app.core.xxx import ...` 可用
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))