from datetime import timedelta

SECRET_KEY = 'change this'
STEAM_KEY = 'Steam API Key here'

UPLOAD_FOLDER = '/path/to/temp'
PARSER = '/logstfparser/bin/logstfparser.js'
LOG_FOLDER = '/pylogstf/logs'

MAX_CONTENT_LENGTH = 12 * 1024 * 1024
LOGS_PER_PAGE = 25
LOG_CACHE_TIMEOUT_IN_SECONDS = 15 * 60
FRONTPAGE_CACHE_TIMEOUT_IN_SECONDS = 2 * 60
ADMINS = []

SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://postgres:postgres@localhost:5432/logdb'
SQLALCHEMY_POOL_SIZE = 5
SQLALCHEMY_TRACK_MODIFICATIONS = False

SENTRY_DSN = None
PERMANENT_SESSION_LIFETIME = timedelta(days=90)

CELERY_BROKER_URL = 'redis://localhost:6379'
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
