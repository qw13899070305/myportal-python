"""密码哈希：基于 argon2-cffi。

哈希参数取自配置（``ARGON2_*``），可通过环境变量调整强度。
"""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from backend.core.config import settings

pwd_context = PasswordHasher(
    time_cost=settings.ARGON2_TIME_COST,
    memory_cost=settings.ARGON2_MEMORY_COST,
    parallelism=settings.ARGON2_PARALLELISM,
)


def get_password_hash(password: str) -> str:
    """生成 Argon2id 哈希字符串。"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验明文密码与哈希是否匹配。

    任何格式错误都视为校验失败而不是抛异常，
    避免"哈希损坏"变成 500 错误。
    """
    if not plain_password or not hashed_password:
        return False
    try:
        return pwd_context.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed_password: str) -> bool:
    """判断已有哈希是否需要按当前参数重新生成。"""
    try:
        return pwd_context.check_needs_rehash(hashed_password)
    except InvalidHashError:
        return True
