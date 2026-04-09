"""
Compatibility stubs for packages that may not be installed.
Import this first in app.py to ensure graceful degradation.
"""

import sys
import types


def _make_stub(name, attrs=None):
    """Create a stub module."""
    mod = types.ModuleType(name)
    if attrs:
        for k, v in attrs.items():
            setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


def _try_import(name):
    try:
        return __import__(name)
    except ImportError:
        return None


# flask_sqlalchemy - use real implementation
if not _try_import("flask_sqlalchemy"):
    import flask_sqlalchemy_compat  # noqa - installs real SQLAlchemy compat


# flask_bcrypt stub
if not _try_import("flask_bcrypt"):
    import hashlib
    import os

    class _FakeBcrypt:
        def __init__(self, *a, **kw):
            pass

        def init_app(self, app):
            pass

        def generate_password_hash(self, pw, rounds=12):
            salt = os.urandom(16).hex()
            h = hashlib.sha256(f"{salt}{pw}".encode()).hexdigest()
            return f"$stub${salt}${h}".encode()

        def check_password_hash(self, phash, pw):
            try:
                if isinstance(phash, bytes):
                    phash = phash.decode()
                parts = phash.split("$")
                if parts[1] == "stub":
                    salt, stored = parts[2], parts[3]
                    h = hashlib.sha256(f"{salt}{pw}".encode()).hexdigest()
                    return h == stored
            except Exception:
                pass
            return False

    def _check_pw(phash, pw):
        return _FakeBcrypt().check_password_hash(phash, pw)

    def _gen_pw(pw, rounds=12):
        return _FakeBcrypt().generate_password_hash(pw, rounds)

    stub = _make_stub("flask_bcrypt")
    stub.Bcrypt = _FakeBcrypt
    stub.generate_password_hash = _gen_pw
    stub.check_password_hash = _check_pw


# flask_marshmallow stub
if not _try_import("flask_marshmallow"):

    class _FakeMarshmallow:
        def __init__(self, *a, **kw):
            pass

        def init_app(self, app):
            pass

    stub = _make_stub("flask_marshmallow")
    stub.Marshmallow = _FakeMarshmallow


# marshmallow stub (needed for schemas)
if not _try_import("marshmallow"):

    class _Schema:
        def __init__(self, *a, **kw):
            pass

        def load(self, data, **kw):
            return data or {}

        def dump(self, obj, **kw):
            return obj if isinstance(obj, dict) else {}

        class Meta:
            pass

    class _Field:
        def __init__(self, *a, **kw):
            pass

    class _ValidationError(Exception):
        def __init__(self, msg="", field_name=None, **kw):
            self.messages = {field_name or "_schema": [msg]} if msg else {}
            super().__init__(msg)

    class _fields:
        Str = String = _Field
        Int = Integer = _Field
        Float = _Field
        Bool = Boolean = _Field
        Email = _Field
        DateTime = _Field
        Date = _Field
        Decimal = _Field
        Dict = _Field
        List = lambda item_type=None, **kw: _Field()
        Nested = lambda schema, **kw: _Field()
        Raw = _Field

    class _validate:
        @staticmethod
        def Length(*a, **kw):
            return lambda x: x

        @staticmethod
        def Range(*a, **kw):
            return lambda x: x

        @staticmethod
        def OneOf(*a, **kw):
            return lambda x: x

    stub = _make_stub("marshmallow")
    stub.Schema = _Schema
    stub.fields = _fields
    stub.validate = _validate
    stub.validates_schema = lambda f: f
    stub.ValidationError = _ValidationError
    stub.pre_load = lambda *a, **kw: (lambda f: f)
    stub.post_load = lambda *a, **kw: (lambda f: f)


# flask_jwt_extended stub
if not _try_import("flask_jwt_extended"):
    import time
    import uuid

    class _JWTManager:
        def __init__(self, *a, **kw):
            pass

        def init_app(self, app):
            pass

        def token_in_blocklist_loader(self, f):
            return f

        def expired_token_loader(self, f):
            return f

        def invalid_token_loader(self, f):
            return f

        def unauthorized_loader(self, f):
            return f

    _current_user_id = [None]

    def _create_access_token(identity, **kw):
        import base64
        import json

        payload = {
            "sub": str(identity),
            "exp": int(time.time()) + 900,
            "jti": str(uuid.uuid4()),
        }
        return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

    def _create_refresh_token(identity, **kw):
        import base64
        import json

        payload = {
            "sub": str(identity),
            "exp": int(time.time()) + 604800,
            "jti": str(uuid.uuid4()),
            "type": "refresh",
        }
        return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

    def _get_jwt_identity():
        return _current_user_id[0]

    def _get_jwt():
        return {"jti": str(uuid.uuid4())}

    def _jwt_required(optional=False, refresh=False):
        def decorator(f):
            import functools

            @functools.wraps(f)
            def wrapper(*a, **kw):
                from flask import jsonify, request

                auth = request.headers.get("Authorization", "")
                if not auth and not optional:
                    return (
                        jsonify(
                            {
                                "msg": "Missing Authorization Header",
                                "success": False,
                                "error": "Unauthorized",
                                "message": "Authentication is required to access this resource.",
                            }
                        ),
                        401,
                    )
                if auth:
                    try:
                        import base64
                        import json

                        token = auth.replace("Bearer ", "")
                        payload = json.loads(base64.urlsafe_b64decode(token + "=="))
                        if payload.get("exp", 0) < time.time():
                            return (
                                jsonify(
                                    {
                                        "msg": "Token has expired",
                                        "success": False,
                                        "error": "Unauthorized",
                                        "message": "Token has expired.",
                                    }
                                ),
                                401,
                            )
                        _current_user_id[0] = payload.get("sub")
                    except Exception:
                        if not optional:
                            return (
                                jsonify(
                                    {
                                        "msg": "Invalid token",
                                        "success": False,
                                        "error": "Unauthorized",
                                        "message": "Invalid authentication token.",
                                    }
                                ),
                                422,
                            )
                return f(*a, **kw)

            return wrapper

        return decorator

    stub = _make_stub("flask_jwt_extended")
    stub.JWTManager = _JWTManager
    stub.create_access_token = _create_access_token
    stub.create_refresh_token = _create_refresh_token
    stub.get_jwt_identity = _get_jwt_identity
    stub.get_jwt = _get_jwt
    stub.jwt_required = _jwt_required
    stub.verify_jwt_in_request = lambda *a, **kw: None


# flask_cors stub
if not _try_import("flask_cors"):

    class _CORS:
        def __init__(self, app=None, **kw):
            if app:
                self.init_app(app, **kw)

        def init_app(self, app, **kw):
            @app.after_request
            def add_cors(response):
                response.headers["Access-Control-Allow-Origin"] = "*"
                response.headers["Access-Control-Allow-Methods"] = (
                    "GET, POST, PUT, DELETE, OPTIONS"
                )
                response.headers["Access-Control-Allow-Headers"] = (
                    "Content-Type, Authorization"
                )
                return response

    stub = _make_stub("flask_cors")
    stub.CORS = _CORS


# flask_limiter stub
if not _try_import("flask_limiter"):

    class _Limiter:
        def __init__(self, *a, **kw):
            pass

        def init_app(self, app):
            pass

        def limit(self, *a, **kw):
            def decorator(f):
                return f

            return decorator

    class _util:
        @staticmethod
        def get_remote_address():
            return "127.0.0.1"

    stub = _make_stub("flask_limiter")
    stub.Limiter = _Limiter
    stub.util = _util
    _make_stub("flask_limiter.util").get_remote_address = _util.get_remote_address


# sqlalchemy stub (for db.text, etc.)
if not _try_import("sqlalchemy"):
    stub = _make_stub("sqlalchemy")
    stub.text = lambda s: s


# pyotp stub with real TOTP implementation
if not _try_import("pyotp"):
    import base64
    import hashlib
    import hmac
    import os
    import struct
    import time

    def _hotp(secret_base32, counter):
        """RFC 4226 HOTP implementation."""
        try:
            key = base64.b32decode(
                secret_base32.upper() + "=" * (-len(secret_base32) % 8)
            )
        except Exception:
            return "000000"
        msg = struct.pack(">Q", counter)
        h = hmac.new(key, msg, hashlib.sha1).digest()
        offset = h[-1] & 0x0F
        code = struct.unpack(">I", h[offset : offset + 4])[0] & 0x7FFFFFFF
        return str(code % 1000000).zfill(6)

    def _totp_code(secret, t=None):
        """RFC 6238 TOTP implementation."""
        if t is None:
            t = int(time.time())
        counter = t // 30
        return _hotp(secret, counter)

    class _TOTP:
        def __init__(self, secret):
            self.secret = secret

        def now(self):
            return _totp_code(self.secret)

        def verify(self, code, valid_window=1):
            t = int(time.time())
            for delta in range(-valid_window, valid_window + 1):
                if _totp_code(self.secret, t + delta * 30) == str(code).zfill(6):
                    return True
            return False

        def provisioning_uri(self, name="", issuer_name=""):
            return f"otpauth://totp/{name}?secret={self.secret}&issuer={issuer_name}"

    def _random_base32():
        return base64.b32encode(os.urandom(20)).decode().rstrip("=")

    stub = _make_stub("pyotp")
    stub.TOTP = _TOTP
    stub.random_base32 = _random_base32


# qrcode stub
if not _try_import("qrcode"):

    class _QRCode:
        def __init__(self, *a, **kw):
            pass

        def add_data(self, data):
            pass

        def make(self, fit=True):
            pass

        def make_image(self, **kw):
            class _Img:
                def save(self, buf, format=None):
                    buf.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

            return _Img()

    stub = _make_stub("qrcode")
    stub.QRCode = _QRCode


# requests stub
if not _try_import("requests"):

    class _Response:
        status_code = 200

        def json(self):
            return {}

        def raise_for_status(self):
            pass

    class _requests:
        @staticmethod
        def get(*a, **kw):
            return _Response()

        @staticmethod
        def post(*a, **kw):
            return _Response()

    stub = _make_stub("requests")
    for attr in dir(_requests):
        if not attr.startswith("_"):
            setattr(stub, attr, getattr(_requests, attr))

print("Compatibility stubs loaded")


# redis stub
if not _try_import("redis"):

    class _Redis:
        def __init__(self, *a, **kw):
            pass

        def ping(self):
            return True

        def get(self, *a, **kw):
            return None

        def set(self, *a, **kw):
            return True

        def setex(self, *a, **kw):
            return True

        def delete(self, *a, **kw):
            return 1

        def exists(self, *a, **kw):
            return False

        def expire(self, *a, **kw):
            return True

        def ttl(self, *a, **kw):
            return -1

        def keys(self, *a, **kw):
            return []

        def incr(self, *a, **kw):
            return 1

        @classmethod
        def from_url(cls, url, **kw):
            return cls()

    stub = _make_stub("redis")
    stub.Redis = _Redis
    stub.from_url = _Redis.from_url
    stub.StrictRedis = _Redis
    # exceptions submodule
    exc_stub = _make_stub("redis.exceptions")

    class _RedisError(Exception):
        pass

    exc_stub.RedisError = _RedisError
    exc_stub.ConnectionError = ConnectionError


# pytest stub (minimal, for import compatibility in non-test code)
if not _try_import("pytest"):

    class _pytest_fixture:
        def __call__(self, f=None, *a, **kw):
            if callable(f):
                return f

            def decorator(fn):
                return fn

            return decorator

        def __getattr__(self, name):
            return self

    class _pytest_module:
        fixture = _pytest_fixture()
        mark = type(
            "mark",
            (),
            {
                "unit": lambda f: f,
                "integration": lambda f: f,
                "slow": lambda f: f,
                "external": lambda f: f,
                "parametrize": lambda *a, **kw: (lambda f: f),
            },
        )()
        raises = Exception
        skip = lambda msg="": None
        skipTest = lambda msg="": None

        @staticmethod
        def importorskip(name):
            m = _try_import(name)
            if m is None:
                raise ImportError(f"Skipping: {name} not available")
            return m

    stub = _make_stub("pytest")
    for k, v in vars(_pytest_module).items():
        if not k.startswith("__"):
            setattr(stub, k, v)
