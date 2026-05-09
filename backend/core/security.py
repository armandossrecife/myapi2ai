from datetime import datetime, timedelta, timezone
from typing import Any, Union

import bcrypt
import jwt
from backend.core.config import settings

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        import sys
        print(f"VERIFY DBG: plain_password='{plain_password}' type={type(plain_password)}", file=sys.stderr)
        print(f"VERIFY DBG: hashed_password='{hashed_password}' type={type(hashed_password)}", file=sys.stderr)
        res = bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
        print(f"VERIFY DBG: result={res}", file=sys.stderr)
        return res
    except Exception as e:
        import sys
        print(f"VERIFY DBG Exception: {str(e)}", file=sys.stderr)
        return False

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt
