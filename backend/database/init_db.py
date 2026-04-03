"""
数据库初始化脚本
"""
from .models import Base, engine, init_db


def main():
    print("正在初始化数据库...")
    init_db()
    print("数据库初始化完成！")


if __name__ == "__main__":
    main()