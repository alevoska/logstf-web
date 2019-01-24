from functools import wraps
from typing import Callable
from flask import abort, redirect, request, session, flash, url_for, g
from flask_openid import OpenID
from werkzeug.contrib.cache import RedisCache
from celery import Celery


def login_required(f: Callable) -> Callable:
    """Decorator to allow only logged in users to load route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.user:
            flash('You are required to be logged in.')
            return redirect(url_for('lists.front_page'))
        return f(*args, **kwargs)
    return decorated_function


def require_token(f: Callable) -> Callable:
    """Decorator to require csrf token to load route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = session.get('_csrf_token')        
        if not token or token != request.args.get('t'):
            abort(403)    	
        return f(*args, **kwargs)
    return decorated_function


cache = RedisCache()
oid = OpenID()
celery = Celery()
