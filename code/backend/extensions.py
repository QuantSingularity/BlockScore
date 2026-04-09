import compat_stubs  # noqa: F401

"""
Shared Flask extensions — imported by models to avoid circular imports.
"""

from flask_bcrypt import Bcrypt
from flask_marshmallow import Marshmallow
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
ma = Marshmallow()
bcrypt = Bcrypt()
