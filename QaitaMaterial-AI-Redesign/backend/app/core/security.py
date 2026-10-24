from datetime import datetime, timedelta, timezone
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from app.core.config import settings

hasher = PasswordHasher()
def hash_password(password: str): return hasher.hash(password)
def verify_password(password: str, hashed: str):
    try: return hasher.verify(hashed, password)
    except (VerifyMismatchError, VerificationError): return False

def issue_token(uid: int):
    s=settings()
    return jwt.encode({"sub":str(uid),"exp":datetime.now(timezone.utc)+timedelta(minutes=s.access_token_expire_minutes)},s.jwt_secret_key,algorithm=s.jwt_algorithm)

def token_uid(token: str):
    try: return int(jwt.decode(token,settings().jwt_secret_key,algorithms=[settings().jwt_algorithm])["sub"])
    except (jwt.PyJWTError, KeyError, ValueError): return None
