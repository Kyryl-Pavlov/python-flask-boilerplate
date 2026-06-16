from datetime import datetime, timezone
from app.extensions import db
import bcrypt
from uuid import uuid4

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Uuid, primary_key=True, default=uuid4)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password: str):
        # using rounds=13 will make password hashing ~600ms long. default is 12 ~300ms long
        self.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=13)).decode()

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode(), self.password_hash.encode())
    

