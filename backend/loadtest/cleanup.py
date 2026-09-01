# -*- coding: utf-8 -*-
"""压测数据清理：删除所有 loadtest_ 账号及其会话/消息（在 prepare.py 逆向操作）。"""
import sqlite3

DB = r"F:\langchainRAG项目\backend\data\app.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

# 找出压测账号 id
rows = cur.execute("SELECT id FROM users WHERE username LIKE 'loadtest_%'").fetchall()
ids = [r[0] for r in rows]
print(f"待清理压测账号: {len(ids)} 个")

if ids:
    convs = cur.executemany("SELECT id FROM conversations WHERE user_id = ?", [(i,) for i in ids]).fetchall()
    conv_ids = [c[0] for c in convs]
    if conv_ids:
        m = cur.executemany("DELETE FROM messages WHERE conversation_id = ?", [(i,) for i in conv_ids]).rowcount
        c = cur.executemany("DELETE FROM conversations WHERE id = ?", [(i,) for i in conv_ids]).rowcount
        print(f"已删除会话: {c}, 消息: {m}")
    u = cur.executemany("DELETE FROM users WHERE id = ?", [(i,) for i in ids]).rowcount
    print(f"已删除账号: {u}")

conn.commit()
conn.close()
print("清理完成")
