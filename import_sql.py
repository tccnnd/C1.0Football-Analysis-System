"""
用 Python pymysql 直接导入 SQL 文件，绕过命令行 warning 干扰问题
"""
import sys
import time
import pymysql
from pathlib import Path

SQL_FILE = Path("E:/APP/ELO/foot_0408.sql")
CONN = dict(host="127.0.0.1", port=3306, user="root",
            password="Meta.123", database="foot",
            charset="utf8mb4", autocommit=True,
            max_allowed_packet=256*1024*1024)

def run():
    print(f"文件: {SQL_FILE}  ({SQL_FILE.stat().st_size/1024/1024:.0f} MB)")
    print("连接数据库...")
    conn = pymysql.connect(**CONN)
    cur = conn.cursor()

    # 读取文件，按语句分割执行
    print("读取 SQL 文件...")
    content = SQL_FILE.read_bytes()
    # 尝试 utf8，失败则 latin1
    try:
        text = content.decode("utf8")
    except Exception:
        text = content.decode("latin1")

    print("解析并执行 SQL 语句...")
    start = time.time()
    stmt = []
    ok = err = skip = 0
    in_string = False
    string_char = None
    i = 0
    buf = []

    # 简单状态机分割 SQL 语句
    lines = text.splitlines(keepends=True)
    current = []
    for line in lines:
        stripped = line.strip()
        # 跳过注释行
        if stripped.startswith("--") or stripped.startswith("#") or stripped == "":
            continue
        # 跳过 SET 语句（兼容性）
        if stripped.upper().startswith("/*!") or stripped.upper().startswith("SET "):
            continue
        current.append(line)
        if stripped.endswith(";"):
            sql = "".join(current).strip()
            current = []
            if not sql or sql == ";":
                skip += 1
                continue
            try:
                cur.execute(sql)
                ok += 1
                if ok % 10000 == 0:
                    elapsed = time.time() - start
                    print(f"  已执行 {ok:,} 条  错误 {err}  耗时 {elapsed:.0f}s")
            except Exception as e:
                err += 1
                if err <= 5:
                    print(f"  ERROR: {str(e)[:120]}")

    elapsed = time.time() - start
    print(f"\n完成: 成功 {ok:,}  错误 {err}  跳过 {skip}  耗时 {elapsed:.0f}s")

    # 验证数据量
    print("\n各表数据量:")
    tables = ["t_match_his","t_asia_his","t_euro_his","t_analy_result",
              "t_b_f_score","t_b_f_battle","t_b_f_jin","t_league","t_comp"]
    for t in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            cnt = cur.fetchone()[0]
            print(f"  {t:<25} {cnt:>10,} 行")
        except Exception as e:
            print(f"  {t:<25} ERROR: {e}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    run()
