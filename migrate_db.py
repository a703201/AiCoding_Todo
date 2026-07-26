#!/usr/bin/env python3
"""
数据库迁移管理脚本

用法:
    python migrate_db.py init       — 初始化迁移仓库（仅首次）
    python migrate_db.py migrate    — 生成迁移脚本
    python migrate_db.py upgrade    — 执行迁移
    python migrate_db.py downgrade  — 回滚到上一个版本
    python migrate_db.py history    — 查看历史
    python migrate_db.py current    — 查看当前版本
    python migrate_db.py stamp head — 标记当前版本
"""
import os
import sys

os.environ.setdefault("FLASK_APP", "app:app")

from flask_migrate import (
    init, migrate, upgrade, downgrade,
    history, current, stamp, heads,
)

from app import create_app, db


def main():
    app = create_app()
    command = sys.argv[1] if len(sys.argv) > 1 else "help"

    with app.app_context():
        if command == "init":
            if os.path.exists("migrations/alembic.ini"):
                print("⚠️  migrations 目录已存在，跳过初始化")
            else:
                init(directory="migrations")
                print("✓ 迁移仓库初始化完成")

        elif command == "migrate":
            msg = sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == "-m" else "自动迁移"
            migrate(directory="migrations", message=msg)
            print(f"✓ 迁移脚本已生成: {msg}")

        elif command == "upgrade":
            rev = sys.argv[2] if len(sys.argv) > 2 else "head"
            upgrade(directory="migrations", revision=rev)
            print(f"✓ 数据库已升级到: {rev}")

        elif command == "downgrade":
            rev = sys.argv[2] if len(sys.argv) > 2 else "-1"
            downgrade(directory="migrations", revision=rev)
            print(f"✓ 已回滚到: {rev}")

        elif command == "history":
            # Flask-Migrate 的 history() 输出到控制台
            history(directory="migrations")

        elif command == "current":
            current(directory="migrations")

        elif command == "stamp":
            rev = sys.argv[2] if len(sys.argv) > 2 else "head"
            stamp(directory="migrations", revision=rev)
            print(f"✓ 已标记版本为: {rev}")

        elif command == "sql":
            upgrade(directory="migrations", sql=True)

        elif command == "heads":
            heads(directory="migrations")

        else:
            print(__doc__)
            print("可用命令:")
            print("  python migrate_db.py init            → 初始化迁移仓库")
            print("  python migrate_db.py migrate -m 'msg' → 生成迁移脚本")
            print("  python migrate_db.py upgrade          → 执行全部迁移")
            print("  python migrate_db.py downgrade        → 回滚上一个版本")
            print("  python migrate_db.py history          → 查看迁移历史")
            print("  python migrate_db.py current          → 查看当前版本")
            print("  python migrate_db.py stamp head       → 标记当前为最新")
            print("  python migrate_db.py sql              → 预览 SQL 不执行")


if __name__ == "__main__":
    main()
