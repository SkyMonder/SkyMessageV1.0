from passlib.hash import bcrypt
from flask_jwt_extended import create_access_token
from datetime import timedelta

def hash_password(password: str) -> str:
    return bcrypt.hash(password)

def verify_password(password: str, hash_: str) -> bool:
    return bcrypt.verify(password, hash_)

def create_jwt(identity: str):
    return create_access_token(identity=identity, expires_delta=timedelta(days=7))