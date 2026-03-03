from passlib.context import CryptContext

# Try bcrypt first, fall back to sha256_crypt if bcrypt C extension unavailable
try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    pwd_context.hash("test")  # verify it actually works
except Exception:
    pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
