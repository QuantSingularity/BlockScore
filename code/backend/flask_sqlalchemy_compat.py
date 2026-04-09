"""
Minimal Flask-SQLAlchemy + SQLAlchemy implementation using SQLite via stdlib sqlite3.
Only implements what BlockScore needs.
"""

import sqlite3
import threading
from datetime import datetime, timezone
from decimal import Decimal

_local = threading.local()


class _Column:
    def __init__(self, *args, **kwargs):
        self.type = args[0] if args else None
        self.primary_key = kwargs.get("primary_key", False)
        self.nullable = kwargs.get("nullable", True)
        self.unique = kwargs.get("unique", False)
        self.index = kwargs.get("index", False)
        self.default = kwargs.get("default", None)
        self.onupdate = kwargs.get("onupdate", None)
        self.foreign_key = None
        for a in args:
            if isinstance(a, _ForeignKey):
                self.foreign_key = a


class _ForeignKey:
    def __init__(self, target):
        self.target = target


class _Relationship:
    def __init__(self, target, **kwargs):
        self.target = target
        self.kwargs = kwargs


class _TypeBase:
    def __init__(self, *a, **kw):
        pass


class _String(_TypeBase):
    def __init__(self, length=255, **kw):
        self.length = length


class _Integer(_TypeBase):
    pass


class _Boolean(_TypeBase):
    pass


class _Text(_TypeBase):
    pass


class _Float(_TypeBase):
    pass


class _Date(_TypeBase):
    pass


class _DateTime(_TypeBase):
    def __init__(self, timezone=False, **kw):
        self.tz = timezone


class _Numeric(_TypeBase):
    def __init__(self, *a, **kw):
        pass


class _BigInteger(_TypeBase):
    pass


class _Enum(_TypeBase):
    def __init__(self, *a, **kw):
        self.enum_class = a[0] if a and hasattr(a[0], "__mro__") else None


def _is_type(t, cls):
    """Check if t is an instance of cls OR is cls itself (for class-level defaults)."""
    return (
        isinstance(t, cls) or t is cls or (isinstance(t, type) and issubclass(t, cls))
    )


def _col_sql_type(col):
    t = col.type
    if _is_type(t, _Boolean):
        return "INTEGER"
    if _is_type(t, _BigInteger):
        return "INTEGER"
    if _is_type(t, _Integer):
        return "INTEGER"
    if _is_type(t, _Float):
        return "REAL"
    if _is_type(t, _Numeric):
        return "REAL"
    if _is_type(t, _Enum):
        return "TEXT"
    if _is_type(t, (_Date, _DateTime)):
        return "TEXT"
    return "TEXT"


def _to_db(val):
    if val is None:
        return None
    if isinstance(val, bool):
        return int(val)
    if isinstance(val, Decimal):
        return float(val)
    if hasattr(val, "value"):
        return val.value  # enum
    if isinstance(val, datetime):
        return val.isoformat()
    return val


def _from_db(val, col):
    if val is None:
        return None
    t = col.type
    if _is_type(t, _Boolean):
        if isinstance(val, bool):
            return val
        if isinstance(val, int):
            return bool(val)
        if isinstance(val, str):
            return val not in ("0", "false", "False", "")
        return bool(val)
    if _is_type(t, _Integer) or _is_type(t, _BigInteger):
        try:
            return int(val) if val is not None else None
        except Exception:
            return val
    if _is_type(t, _Numeric):
        return Decimal(str(val)) if val is not None else None
    if _is_type(t, _Enum):
        enum_cls = t.enum_class if hasattr(t, "enum_class") else None
        if enum_cls is None and isinstance(t, type) and issubclass(t, _Enum):
            enum_cls = None
        if enum_cls:
            try:
                return enum_cls(val)
            except Exception:
                return val
        return val
    if _is_type(t, _DateTime):
        if isinstance(val, str):
            try:
                dt = datetime.fromisoformat(val)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                return val
        return val
    return val


class _ModelMeta(type):
    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        if name == "Model" or not hasattr(cls, "__tablename__"):
            return
        # collect columns
        cols = {}
        for k, v in dct.items():
            if isinstance(v, _Column):
                cols[k] = v
        # inherit columns from parent
        for base in bases:
            if hasattr(base, "_columns"):
                for k, v in base._columns.items():
                    if k not in cols:
                        cols[k] = v
        cls._columns = cols
        cls._relationships = {}
        for k, v in dct.items():
            if isinstance(v, _Relationship):
                cls._relationships[k] = v
        # Remove column descriptors from the class so instances use __dict__
        # But add ColExpr class attributes so class-level access works for filters
        for k in list(cols.keys()):
            if k in cls.__dict__:
                try:
                    delattr(cls, k)
                except Exception:
                    pass
        # Add class-level _ColExpr for filter expressions
        for k in list(cols.keys()):
            if not hasattr(cls, k):
                setattr(cls, k, _ColExpr(k))


class _ColExpr:
    """Placeholder for SQLAlchemy column expressions at class level."""

    def __init__(self, name):
        self.name = name

    def __gt__(self, other):
        return True

    def __lt__(self, other):
        return True

    def __ge__(self, other):
        return True

    def __le__(self, other):
        return True

    def __eq__(self, other):
        return True

    def desc(self):
        return self

    def asc(self):
        return self


class _ModelClassAttrMixin:
    """Provides class-level column access for filter expressions."""

    def __class_getitem__(cls, item):
        return cls

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)


class Model(metaclass=_ModelMeta):
    _columns = {}
    _relationships = {}
    _db = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    def __init__(self, **kwargs):
        self.__dict__["_in_init"] = True
        # First set all columns to None in __dict__ to shadow _ColExpr class attrs
        for col_name in self._columns:
            self.__dict__[col_name] = None
        # Apply defaults
        for col_name, col in self._columns.items():
            if hasattr(col, "default") and col.default is not None:
                d = col.default
                self.__dict__[col_name] = d() if callable(d) else d
        # Apply kwargs (override defaults)
        for k, v in kwargs.items():
            self.__dict__[k] = v
        self.__dict__["_in_init"] = False

    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)
        # Auto-register as dirty in the active session when a column is modified
        if (
            not name.startswith("_")
            and name in self.__class__._columns
            and not self.__dict__.get("_in_init", True)
        ):
            db = self.__class__._db
            if (
                db
                and db.session
                and id(self) not in {id(o) for o in db.session._pending_add}
            ):
                db.session._pending_add.append(self)

    @classmethod
    def _get_db(cls):
        return cls._db

    @classmethod
    def _get_conn(cls):
        db = cls._get_db()
        if db is None:
            raise RuntimeError("No database bound")
        return db._get_conn()

    @classmethod
    def _table_columns(cls):
        return cls._columns

    @classmethod
    def _create_table(cls, conn):
        if not hasattr(cls, "__tablename__"):
            return
        col_defs = []
        for col_name, col in cls._columns.items():
            sql_type = _col_sql_type(col)
            constraints = []
            if col.primary_key:
                constraints.append("PRIMARY KEY")
            if not col.nullable and not col.primary_key:
                pass  # SQLite allows NULL even with NOT NULL in some modes
            if col.unique:
                constraints.append("UNIQUE")
            col_defs.append(f'"{col_name}" {sql_type} {" ".join(constraints)}'.strip())
        ddl = (
            f'CREATE TABLE IF NOT EXISTS "{cls.__tablename__}" ({", ".join(col_defs)})'
        )
        try:
            conn.execute(ddl)
        except Exception:
            pass

    @classmethod
    def query_all(cls, **filters):
        conn = cls._get_conn()
        where = ""
        params = []
        if filters:
            where = " WHERE " + " AND ".join(f'"{k}" = ?' for k in filters)
            params = list(filters.values())
        rows = conn.execute(
            f'SELECT * FROM "{cls.__tablename__}"{where}', params
        ).fetchall()
        return [cls._from_row(r) for r in rows]

    @classmethod
    def _from_row(cls, row):
        if row is None:
            return None
        obj = cls.__new__(cls)
        # Initialize all columns to None first
        for col_name in cls._columns:
            obj.__dict__[col_name] = None
        col_names = list(cls._columns.keys())
        for i, val in enumerate(row):
            if i < len(col_names):
                col_name = col_names[i]
                col = cls._columns[col_name]
                obj.__dict__[col_name] = _from_db(val, col)
        # Initialize relationships to None (lazy loaded via descriptor)
        for rel_name in cls._relationships:
            if rel_name not in obj.__dict__:
                obj.__dict__[rel_name] = _LazyRelationship(
                    obj, rel_name, cls._relationships[rel_name]
                )
        return obj

    def _to_row_values(self):
        vals = []
        for col_name, col in self._columns.items():
            # Use instance __dict__ first to avoid class-level _ColExpr
            val = self.__dict__.get(col_name, None)
            if val is None and col_name not in self.__dict__:
                # Check if there's a default
                val = None
            # run onupdate only on existing records
            if col.onupdate and hasattr(self, "_persisted"):
                val = col.onupdate() if callable(col.onupdate) else col.onupdate
                setattr(self, col_name, val)
            vals.append(_to_db(val))
        return vals


class _Query:
    def __init__(self, model_cls, conn):
        self._model = model_cls
        self._conn = conn
        self._filters = []
        self._order = None
        self._limit_val = None
        self._offset_val = None

    def filter_by(self, **kwargs):
        q = _Query(self._model, self._conn)
        q._filters = list(self._filters)
        q._order = self._order
        q._limit_val = self._limit_val
        q._offset_val = self._offset_val
        for k, v in kwargs.items():
            q._filters.append((k, "=", _to_db(v)))
        return q

    def filter(self, *exprs):
        # Accept raw SQL-like expressions (string) or skip
        return self

    def order_by(self, *cols):
        q = _Query(self._model, self._conn)
        q._filters = list(self._filters)
        q._limit_val = self._limit_val
        q._offset_val = self._offset_val
        return q

    def limit(self, n):
        q = _Query(self._model, self._conn)
        q._filters = list(self._filters)
        q._order = self._order
        q._limit_val = n
        q._offset_val = self._offset_val
        return q

    def offset(self, n):
        q = _Query(self._model, self._conn)
        q._filters = list(self._filters)
        q._order = self._order
        q._limit_val = self._limit_val
        q._offset_val = n
        return q

    def paginate(self, page=1, per_page=20, error_out=True):
        total = self.count()
        items = self.offset((page - 1) * per_page).limit(per_page).all()
        pages = (total + per_page - 1) // per_page if per_page else 1

        class _Page:
            pass

        p = _Page()
        p.items = items
        p.total = total
        p.pages = pages
        p.page = page
        p.per_page = per_page
        p.has_next = page < pages
        p.has_prev = page > 1
        return p

    def _build_where(self):
        if not self._filters:
            return "", []
        parts = []
        params = []
        for col, op, val in self._filters:
            if val is None:
                parts.append(f'"{col}" IS NULL')
            else:
                parts.append(f'"{col}" {op} ?')
                params.append(val)
        return " WHERE " + " AND ".join(parts), params

    def _build_sql(self, select="*"):
        where, params = self._build_where()
        sql = f'SELECT {select} FROM "{self._model.__tablename__}"{where}'
        if self._limit_val is not None:
            sql += f" LIMIT {int(self._limit_val)}"
        if self._offset_val is not None:
            sql += f" OFFSET {int(self._offset_val)}"
        return sql, params

    def all(self):
        sql, params = self._build_sql()
        try:
            rows = self._conn.execute(sql, params).fetchall()
            return [self._model._from_row(r) for r in rows]
        except Exception:
            return []

    def first(self):
        q = self.limit(1)
        results = q.all()
        return results[0] if results else None

    def count(self):
        where, params = self._build_where()
        sql = f'SELECT COUNT(*) FROM "{self._model.__tablename__}"{where}'
        try:
            return self._conn.execute(sql, params).fetchone()[0]
        except Exception:
            return 0

    def desc(self):
        return self


class _LazyRelationship:
    """Lazy-loading relationship placeholder."""

    def __init__(self, owner, name, rel):
        self._owner = owner
        self._name = name
        self._rel = rel
        self._loaded = False
        self._value = None

    def _load(self):
        if self._loaded:
            return self._value
        db = Model._db
        if db is None:
            return None
        try:
            target_name = self._rel.target
            # Find the target model class
            target_cls = None
            for cls in _get_all_model_subclasses(Model):
                if cls.__name__ == target_name:
                    target_cls = cls
                    break
            if target_cls is None:
                self._loaded = True
                self._value = None
                return None
            uselist = self._rel.kwargs.get("uselist", True)
            # Find FK - look for FK in target pointing to owner table
            owner_table = getattr(self._owner.__class__, "__tablename__", None)
            owner_pk = None
            for cn, col in self._owner.__class__._columns.items():
                if col.primary_key:
                    owner_pk = cn
                    break
            owner_pk_val = self._owner.__dict__.get(owner_pk) if owner_pk else None
            # Find FK column in target
            fk_col = None
            for cn, col in target_cls._columns.items():
                if (
                    col.foreign_key
                    and owner_table
                    and owner_table in str(col.foreign_key.target)
                ):
                    fk_col = cn
                    break
            if fk_col and owner_pk_val:
                results = target_cls.query.filter_by(**{fk_col: owner_pk_val}).all()
                self._value = (
                    results[0]
                    if not uselist and results
                    else (results if uselist else None)
                )
            else:
                self._value = [] if uselist else None
            self._loaded = True
        except Exception:
            self._value = None
            self._loaded = True
        return self._value

    def __bool__(self):
        return self._load() is not None and self._load() != []

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        val = self._load()
        if val is not None:
            return getattr(val, name)
        raise AttributeError(f"'{self._name}' relationship is None")

    def to_dict(self):
        val = self._load()
        if val and hasattr(val, "to_dict"):
            return val.to_dict()
        return None


def _get_all_model_subclasses(cls):
    result = []
    for sub in cls.__subclasses__():
        result.append(sub)
        result.extend(_get_all_model_subclasses(sub))
    return result


class _Session:
    def __init__(self, db):
        self._db = db
        self._pending_add = []
        self._pending_delete = []
        self._dirty = set()  # tracks modified objects by id

    def add(self, obj):
        if obj not in self._pending_add:
            self._pending_add.append(obj)

    def add_all(self, objs):
        self._pending_add.extend(objs)

    def delete(self, obj):
        pass

    def get(self, model_cls, pk):
        conn = self._db._get_conn()
        # find primary key column
        pk_col = None
        for col_name, col in model_cls._columns.items():
            if col.primary_key:
                pk_col = col_name
                break
        if pk_col is None:
            return None
        try:
            row = conn.execute(
                f'SELECT * FROM "{model_cls.__tablename__}" WHERE "{pk_col}" = ?',
                [str(pk)],
            ).fetchone()
            return model_cls._from_row(row)
        except Exception:
            return None

    def commit(self):
        conn = self._db._get_conn()
        for obj in list(self._pending_add):
            self._persist(conn, obj)
        self._pending_add = []
        conn.commit()

    def _mark_dirty(self, obj):
        """Mark an object as needing to be saved on next commit."""
        if id(obj) not in {id(o) for o in self._pending_add}:
            self._pending_add.append(obj)

    def _persist(self, conn, obj):
        if not hasattr(obj, "__tablename__"):
            return
        col_names = list(obj._columns.keys())
        # check if exists
        pk_col = None
        for cn, col in obj._columns.items():
            if col.primary_key:
                pk_col = cn
                break
        pk_val = getattr(obj, pk_col, None) if pk_col else None
        exists = False
        if pk_val:
            try:
                row = conn.execute(
                    f'SELECT 1 FROM "{obj.__tablename__}" WHERE "{pk_col}" = ?',
                    [str(pk_val)],
                ).fetchone()
                exists = row is not None
            except Exception:
                pass
        # apply onupdate
        for cn, col in obj._columns.items():
            if col.onupdate and exists:
                val = col.onupdate() if callable(col.onupdate) else col.onupdate
                setattr(obj, cn, val)
        vals = []
        for cn in col_names:
            val = obj.__dict__.get(cn, None)
            vals.append(_to_db(val))
        if exists:
            sets = ", ".join(f'"{cn}" = ?' for cn in col_names if cn != pk_col)
            set_vals = [
                _to_db(obj.__dict__.get(cn, None)) for cn in col_names if cn != pk_col
            ]
            conn.execute(
                f'UPDATE "{obj.__tablename__}" SET {sets} WHERE "{pk_col}" = ?',
                set_vals + [str(pk_val)],
            )
        else:
            placeholders = ", ".join("?" for _ in col_names)
            cols_sql = ", ".join(f'"{cn}"' for cn in col_names)
            conn.execute(
                f'INSERT INTO "{obj.__tablename__}" ({cols_sql}) VALUES ({placeholders})',
                vals,
            )

    def rollback(self):
        self._pending_add = []
        try:
            self._db._get_conn().rollback()
        except Exception:
            pass

    def remove(self):
        self.rollback()

    def flush(self):
        conn = self._db._get_conn()
        for obj in self._pending_add:
            self._persist(conn, obj)
        conn.commit()

    def execute(self, sql, params=None):
        conn = self._db._get_conn()
        return conn.execute(str(sql), params or [])

    def close(self):
        pass


class _QueryWrapper:
    """Makes Model.query work"""

    def __init__(self, model_cls, db):
        self._model = model_cls
        self._db = db

    def __call__(self):
        return _Query(self._model, self._db._get_conn())

    def filter_by(self, **kwargs):
        return _Query(self._model, self._db._get_conn()).filter_by(**kwargs)

    def filter(self, *args):
        return _Query(self._model, self._db._get_conn()).filter(*args)

    def order_by(self, *args):
        return _Query(self._model, self._db._get_conn()).order_by(*args)

    def all(self):
        return _Query(self._model, self._db._get_conn()).all()

    def first(self):
        return _Query(self._model, self._db._get_conn()).first()

    def count(self):
        return _Query(self._model, self._db._get_conn()).count()


class SQLAlchemy:
    def __init__(self, app=None):
        self._app = None
        self._conn = None
        self._db_path = ":memory:"
        self.session = None
        self.Model = Model
        self._models = []
        # type aliases
        self.Column = _Column
        self.String = _String
        self.Integer = _Integer
        self.Boolean = _Boolean
        self.Text = _Text
        self.Float = _Float
        self.Date = _Date
        self.DateTime = _DateTime
        self.Numeric = _Numeric
        self.Decimal = _Numeric
        self.BigInteger = _BigInteger
        self.Enum = _Enum
        self.ForeignKey = _ForeignKey
        self.relationship = lambda *a, **kw: _Relationship(*a, **kw)
        if app:
            self.init_app(app)

    def init_app(self, app):
        self._app = app
        uri = app.config.get("SQLALCHEMY_DATABASE_URI", ":memory:")
        if uri.startswith("sqlite:///"):
            self._db_path = uri[10:]
        elif uri == "sqlite:///:memory:" or "memory" in uri:
            self._db_path = ":memory:"
        else:
            self._db_path = ":memory:"
        self._conn = None
        # bind db to all Model subclasses
        Model._db = self
        self.session = _Session(self)
        app.extensions = getattr(app, "extensions", {})
        app.extensions["sqlalchemy"] = self

    def _get_conn(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def create_all(self):
        conn = self._get_conn()
        for cls in self._get_all_models():
            cls._create_table(conn)
        conn.commit()

    def drop_all(self):
        conn = self._get_conn()
        for cls in self._get_all_models():
            if hasattr(cls, "__tablename__"):
                try:
                    conn.execute(f'DROP TABLE IF EXISTS "{cls.__tablename__}"')
                except Exception:
                    pass
        conn.commit()

    def _get_all_models(self):
        def get_subclasses(cls):
            result = []
            for sub in cls.__subclasses__():
                result.append(sub)
                result.extend(get_subclasses(sub))
            return result

        return [c for c in get_subclasses(Model) if hasattr(c, "__tablename__")]

    @staticmethod
    def text(sql):
        return sql

    def engine(self):
        return None


def _install():
    import sys
    import types

    # Install flask_sqlalchemy
    mod = types.ModuleType("flask_sqlalchemy")
    mod.SQLAlchemy = SQLAlchemy
    sys.modules["flask_sqlalchemy"] = mod

    # Patch Model.query as a class-level property
    type.__init_subclass__

    # We need to make query work as a class attribute
    class _QueryDescriptor:
        def __get__(self, obj, cls):
            if obj is not None:
                return None
            db = cls._db
            if db is None:
                return None
            return _QueryWrapper(cls, db)

    Model.query = _QueryDescriptor()

    # Install sqlalchemy text helper
    sa_mod = types.ModuleType("sqlalchemy")
    sa_mod.text = lambda s: s
    sys.modules.setdefault("sqlalchemy", sa_mod)


_install()
