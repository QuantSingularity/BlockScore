import os
from datetime import timedelta
from typing import Type

from dotenv import load_dotenv

load_dotenv()


class Config:

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///blockscore.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 300}
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-key-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 900))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        seconds=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES", 604800))
    )
    JWT_ALGORITHM = "HS256"
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ["access", "refresh"]
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    BLOCKCHAIN_PROVIDER = os.getenv("BLOCKCHAIN_PROVIDER", "http://localhost:8545")
    BLOCKCHAIN_PROVIDER_URL = os.getenv(
        "BLOCKCHAIN_PROVIDER_URL", "http://localhost:8545"
    )
    BLOCKCHAIN_NETWORK_ID = int(os.getenv("BLOCKCHAIN_NETWORK_ID", 1337))
    BLOCKCHAIN_NETWORK_NAME = os.getenv("BLOCKCHAIN_NETWORK_NAME", "development")
    BLOCKCHAIN_FROM_ADDRESS = os.getenv("BLOCKCHAIN_FROM_ADDRESS", "")
    BLOCKCHAIN_PRIVATE_KEY = os.getenv("BLOCKCHAIN_PRIVATE_KEY", "")
    CREDIT_SCORE_CONTRACT_ADDRESS = os.getenv("CREDIT_SCORE_CONTRACT_ADDRESS", "")
    LOAN_AGREEMENT_CONTRACT_ADDRESS = os.getenv("LOAN_AGREEMENT_CONTRACT_ADDRESS", "")
    GOVERNANCE_CONTRACT_ADDRESS = os.getenv("GOVERNANCE_CONTRACT_ADDRESS", "")
    CONTRACT_ARTIFACTS_PATH = os.getenv("CONTRACT_ARTIFACTS_PATH", "")
    IDENTITY_REGISTRY_CONTRACT_ADDRESS = os.getenv(
        "IDENTITY_REGISTRY_CONTRACT_ADDRESS", ""
    )
    PAYMENT_PROCESSOR_CONTRACT_ADDRESS = os.getenv(
        "PAYMENT_PROCESSOR_CONTRACT_ADDRESS", ""
    )
    CONTRACT_ADDRESS = os.getenv(
        "CONTRACT_ADDRESS", "0x0000000000000000000000000000000000000000"
    )
    PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
    BCRYPT_LOG_ROUNDS = int(os.getenv("BCRYPT_LOG_ROUNDS", 12))
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_NUMBERS = True
    PASSWORD_REQUIRE_SPECIAL = True
    RATELIMIT_STORAGE_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    RATELIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "100 per hour")
    RATELIMIT_LOGIN = os.getenv("RATE_LIMIT_LOGIN", "5 per minute")
    AI_MODEL_URL = os.getenv("AI_MODEL_URL", "http://localhost:5001")
    AI_MODEL_TIMEOUT = float(os.getenv("AI_MODEL_TIMEOUT", "5"))
    AI_MODEL_API_KEY = os.getenv("AI_MODEL_API_KEY", "")
    AI_MODEL_RETRIES = int(os.getenv("AI_MODEL_RETRIES", "2"))
    AI_MODEL_FAILURE_THRESHOLD = int(os.getenv("AI_MODEL_FAILURE_THRESHOLD", "3"))
    AI_MODEL_COOLDOWN_SECONDS = float(os.getenv("AI_MODEL_COOLDOWN_SECONDS", "30"))
    CREDIT_BUREAU_API_KEY = os.getenv("CREDIT_BUREAU_API_KEY", "")
    IDENTITY_VERIFICATION_API_KEY = os.getenv("IDENTITY_VERIFICATION_API_KEY", "")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND = os.getenv(
        "CELERY_RESULT_BACKEND", "redis://localhost:6379/2"
    )
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    UPLOAD_FOLDER = "uploads"
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "gif"}
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    MIN_CREDIT_SCORE = 300
    MAX_CREDIT_SCORE = 850
    DEFAULT_CREDIT_SCORE = 300
    DATA_RETENTION_DAYS = 2555
    AUDIT_LOG_RETENTION_DAYS = 3650


class DevelopmentConfig(Config):

    DEBUG = True
    TESTING = False


class ProductionConfig(Config):

    DEBUG = False
    TESTING = False
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "")
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    FORCE_HTTPS = True


class TestingConfig(Config):

    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    RATELIMIT_ENABLED = False
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=60)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(seconds=120)


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}


def get_config() -> Type[Config]:
    env = os.getenv("FLASK_ENV", "development")
    return config.get(env, config["default"])
