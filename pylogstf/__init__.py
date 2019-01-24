from gevent.monkey import patch_all
from psycogreen.gevent import patch_psycopg
patch_all()
patch_psycopg()

import binascii
import logging
from raven.contrib.flask import Sentry
import os
import urllib
from datetime import datetime

from celery import Celery
from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug.contrib.fixers import ProxyFix

import pylogstf.template as template
from pylogstf.controllers.api import json_api, web_api
from pylogstf.controllers.auth import auth
from pylogstf.controllers.lists import lists
from pylogstf.controllers.pages import pages
from pylogstf.controllers.search import search
from pylogstf.controllers.upload import upload
from pylogstf.controllers.view import view
from pylogstf.extensions import celery
from pylogstf.models import db
from pylogstf.RedisSession import RedisSessionInterface
from pylogstf.steamid import to_steam3, to_steam64
from pylogstf.weapons import WEAPONS


def create_app() -> Flask:
    app = Flask(__name__, static_folder='assets')
    app.config.from_pyfile('config.py')
    app.session_interface = RedisSessionInterface()
    app.wsgi_app = ProxyFix(app.wsgi_app)

    db.init_app(app)
    init_celery(app, celery)

    if app.config['SENTRY_DSN']:
        sentry = Sentry(app, dsn=app.config['SENTRY_DSN'])

    setup_templating(app)
    register_blueprints(app)


    @app.before_first_request
    def setup_logging():
        if not app.debug:
            app.logger.addHandler(logging.StreamHandler())
            app.logger.setLevel(logging.WARNING)


    @app.before_first_request
    def setup_db():
        db.engine.pool._use_threadlocal = True


    @app.before_request
    def get_user_data():
        try:
            g.user = {"id": session['steamid'],	"nick": session['nick']}
        except KeyError:
            g.user = None

    @app.before_request
    def set_default_page_number():
        try:
            g.page = int(request.args.get('p', 1))
        except ValueError:
            g.page = 1

    @app.before_request
    def generate_csrf_token():
        if '_csrf_token' not in session:
            session['_csrf_token'] = binascii.b2a_hex(os.urandom(16)).decode()
        g.token = session['_csrf_token']


    @app.context_processor
    def classes():
        """Convenience function to return a list of TF2 classes."""
        return {
            "classes": [
                'scout',
                'soldier',
                'pyro',
                'demoman',
                'heavyweapons',
                'engineer',
                'medic',
                'sniper',
                'spy'
            ]
        }

    @app.errorhandler(404)
    def page_not_found(e):
        """404 Page not found"""
        return redirect('/')

    @app.errorhandler(500)
    def server_error(e):
        """500 Internal server error"""
        return render_template('errors/500.html'), 500


    return app


def register_blueprints(app):
    app.register_blueprint(pages)
    app.register_blueprint(json_api)
    app.register_blueprint(web_api)
    app.register_blueprint(upload)
    app.register_blueprint(search)
    app.register_blueprint(lists)
    app.register_blueprint(auth)
    app.register_blueprint(view)


def setup_templating(app):
    app.jinja_env.trim_blocks = True
    app.jinja_env.autoescape = True
    app.jinja_env.auto_reload = True if app.debug else False

    app.add_template_filter(template.datetime_filter, name='datetime')
    app.add_template_filter(template.number_format, name='number_format')
    app.add_template_filter(template.mmss_filter, name='mmss')
    app.add_template_filter(template.urlencode_filter, name='urlencode')
    app.add_template_filter(template.weapon_filter, name='weapon')
    app.add_template_filter(template.weaponsort, name='weaponsort')
    app.add_template_filter(to_steam64, name='community_id')
    app.add_template_filter(to_steam3, name='steamid')    


def init_celery(app: Flask, celery_instance: Celery):
    celery_instance.conf.update(app.config)
    TaskBase = celery_instance.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery_instance.Task = ContextTask
