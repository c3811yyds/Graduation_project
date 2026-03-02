import os
import secrets
from datetime import datetime, timedelta
from app import create_app
from extensions import db
from models import TeacherInviteCode

app = create_app()

def generate_code(days_valid=7):
    with app.app_context():
        code = f"TCH-{secrets.token_hex(4).upper()}"
        expires = datetime.utcnow() + timedelta(days=days_valid)
        ic = TeacherInviteCode(code=code, expires_at=expires)
        db.session.add(ic)
        db.session.commit()
        print(f"=====================================")
        print(f"成功生成教师专属邀请码: {code}")
        print(f"该验证码将在 {days_valid} 天后过期")
        print(f"=====================================")

if __name__ == "__main__":
    import sys
    days = 7
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            pass
    generate_code(days) 
