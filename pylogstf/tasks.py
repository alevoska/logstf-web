import json
import urllib

from flask import current_app as app
from pylogstf.extensions import cache, celery
from pylogstf.models import LogPlayer, Profile, db


@celery.task()
def update_profile(steamids: list):
    if not steamids:
        raise ValueError

    steamids_str = [str(steamid) for steamid in steamids]
    steamids_csv = ','.join(steamids_str)

    steam_url = (
        'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/'
        f'?key={app.config["STEAM_KEY"]}&'
        f'steamids={steamids_csv}'
    )
    try:
        steamjson = urllib.request.urlopen(steam_url)
    except urllib.error.URLError:
        app.logger.error('TASK: Could not connect to Steam API')
        return False

    try:
        user = json.loads(steamjson.read().decode())
        players = user['response']['players']
    except (json.JSONDecodeError, KeyError):
        app.logger.error('TASK: Invalid JSON response from Steam API')
        return False

    for player in players:
        with app.app_context():
            try:
                steamid64 = player['steamid']
                steamprofile = player
                profile = Profile.query.filter(Profile.id == steamid64).first()
                if not profile:
                    profile = Profile(id=steamid64, steamprofile=steamprofile)
                    db.session.add(profile)
                    db.session.commit()
                else:
                    profile.steamprofile = steamprofile
                    db.session.commit()
            except Exception:
                app.logger.error('TASK: Could not update player profile')


@celery.task()
def after_upload(log_id: int, filepath: str):
    with app.app_context():
        # Update player count cache
        player_count = db.session.query(LogPlayer.player_id.distinct()).count()
        cache.set('player_count', player_count, timeout=0)
