import json
import time
from urllib.request import URLError, urlopen

from flask import (Blueprint, Response, abort, current_app, flash, redirect,
                   session, url_for)

from pylogstf.extensions import oid, require_token
from pylogstf.models import Profile, db

auth = Blueprint('auth', __name__)


@auth.route('/auth')
@oid.loginhandler
def steam_auth() -> Response:
    return oid.try_login('http://steamcommunity.com/openid')


@auth.route('/logout')
@require_token
def logout() -> Response:
    session.pop('steamid', None)
    session.pop('nick', None)
    flash('Signed out successfully.')
    return redirect(url_for('lists.front_page'))


@oid.after_login
def login(resp) -> Response:
    steamid = resp.identity_url[37:]

    try:
        steamid64 = int(steamid)
    except ValueError:
        current_app.logger.error(f'AUTH: Incorrect steamid response: {steamid}')
        abort(500)

    # Get personaname from Steam API
    steam_api_key = current_app.config['STEAM_KEY']
    steam_url = ('http://api.steampowered.com/ISteamUser'
                 f'/GetPlayerSummaries/v0002/?key={steam_api_key}'
                 f'&steamids={steamid}')

    try:
        steamjson = urlopen(steam_url)
    except URLError:
        current_app.logger.error('AUTH: Could not connect to Steam API')
        abort(500)

    try:
        user = json.loads(steamjson.read().decode())
        steamprofile = user['response']['players'][0]
        nick = steamprofile['personaname']
    except (ValueError, KeyError):
        current_app.logger.error('AUTH: Invalid JSON response from Steam API')
        abort(500)

    # Set session
    session.permanent = True
    session['steamid'] = steamid
    session['nick'] = nick
    flash(f'Logged in as {nick}.')

    # Update user
    profile = Profile.query.filter(Profile.id == steamid64).first()
    current_time = time.time()
    if not profile:
        profile = Profile(
            id=steamid64,
            steamprofile=steamprofile,
            last_login=current_time,
        )
        db.session.add(profile)
    else:
        profile.steamprofile = steamprofile
        profile.last_login = current_time
    db.session.commit()

    return redirect(url_for('lists.front_page'))
