#!/usr/bin/env python3
"""
生成Flask兼容的密码哈希
"""
from werkzeug.security import generate_password_hash

def generate_hash(password):
    """生成密码哈希"""
    return generate_password_hash(password, method='sha256')

if __name__ == "__main__":
    print("=== Flask密码哈希生成器 ===")
    print("请输入你想要的管理员信息：")
    
    username = input("管理员用户名: ").strip()
    password = input("管理员密码: ").strip()
    
    if username and password:
        password_hash = generate_hash(password)
        print(f"\n=== 生成的SQL语句 ===")
        print(f"USE axspa;")
        print(f"DELETE FROM users WHERE username = '{username}';")
        print(f"INSERT INTO users (username, password_hash, is_admin) VALUES ('{username}', '{password_hash}', TRUE);")
        print(f"SELECT id, username, is_admin FROM users WHERE username = '{username}';")
    else:
        print("用户名和密码不能为空！") 