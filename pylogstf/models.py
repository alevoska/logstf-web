from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.ext.hybrid import hybrid_property

db = SQLAlchemy()


class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uploader_id = db.Column(db.BigInteger, index=True)
    uploader_name = db.Column(db.String(80))
    uploader_desc = db.Column(db.String(40))
    logname = db.Column(db.String(40))
    logdata = db.deferred(db.Column(db.UnicodeText))
    views = db.Column(db.Integer, default=0, index=True)
    date = db.Column(db.BigInteger, index=True)
    tf2map = db.Column(db.String(24))
    player_count = db.Column(db.Integer)
    player_cache = db.Column(ARRAY(db.BigInteger))
    players = db.relationship(
        'LogPlayer',
        cascade='all, delete, delete-orphan',
        lazy='dynamic'
    )
    is_updated = db.Column(db.Boolean, default=False)
    hash = db.Column(db.String(40), index=True)
    __mapper_args__ = {'order_by': date.desc()}

class LogPlayer(db.Model):
    player_id = db.Column(
        db.BigInteger,
        index=True,
        primary_key=True,
        autoincrement=False
    )
    log_id = db.Column(
        db.Integer,
        db.ForeignKey('log.id'),
        primary_key=True,
        autoincrement=False
    )
    name = db.Column(db.String(80), index=True)
    # POSTGRESQL: Create pg_trgm index on name to boost search performance


class APIKey(db.Model):
    id = db.Column(db.BigInteger, primary_key=True)
    key = db.Column(db.String(80))
    name = db.Column(db.String(80))


class Profile(db.Model):
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=False)
    steamprofile = db.Column(JSONB)
    last_login = db.Column(db.BigInteger)
    ban_upload = db.Column(db.BigInteger)


def like_string(s: str, max_length=40) -> str:
    return s.strip() \
            .replace('%', '\\%') \
            .replace('_', '\\_')[:max_length]
