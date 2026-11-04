"""
관리자 계정 만들기. 관리자는 회원가입 화면이 아니라 이 명령으로만 만든다 (레퍼런스 10장 권한).

실행 (backend/ 폴더에서):
    python -m app.scripts.create_admin --email admin@example.com --nickname 관리자

비밀번호는 화면에 보이지 않게 입력받는다. 자동화할 때는 ADMIN_PASSWORD 환경 변수를 쓴다.
이미 가입한 이메일이면 그 계정을 관리자로 바꾼다.
"""

import argparse
import getpass
import os
import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import User


def main() -> None:
    parser = argparse.ArgumentParser(description="페어픽 관리자 계정 만들기")
    parser.add_argument("--email", required=True)
    parser.add_argument("--nickname", default="관리자")
    args = parser.parse_args()
    email = args.email.strip().lower()

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is not None:
            user.role = "admin"
            db.commit()
            print(f"기존 계정을 관리자로 바꿨어요: {email}")
            return

        password = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("비밀번호(8자 이상): ")
        if len(password) < 8:
            sys.exit("비밀번호는 8자 이상이어야 해요")
        db.add(User(email=email, password_hash=hash_password(password), nickname=args.nickname, role="admin"))
        db.commit()
        print(f"관리자 계정을 만들었어요: {email}")


if __name__ == "__main__":
    main()
