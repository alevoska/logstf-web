import time

from flask import Blueprint, Response, abort, current_app, g, render_template

from pylogstf.extensions import cache
from pylogstf.models import Log, LogPlayer, Profile
from pylogstf.steamid import to_steam3

from sqlalchemy import cast, BigInteger
from sqlalchemy.dialects.postgresql import ARRAY

lists = Blueprint('lists', __name__)


@lists.route('/')
def front_page() -> Response:
    is_first_page = False
    welcome_text = False
    cached = False

    if not g.page or g.page == 1:
        is_first_page = True
        cached = cache.get('front_page')

    player_count = cache.get('player_count') or 0

    if not cached:
        logs = Log.query.paginate(g.page, 25)
        listing = render_template(
            'listing.html',
            pagination=logs,
            recent=True,
            controls=True,
            front_page=is_first_page,
            welcome=welcome_text,
            player_count=player_count
        )
        if is_first_page:
            cache.set(
                'front_page',
                listing,
                timeout=current_app.config['FRONTPAGE_CACHE_TIMEOUT_IN_SECONDS']
            )
    else:
        listing = cached

    return render_template(
        'block.html',
        content=listing,
        title='Team Fortress 2 Stats'
    )

@lists.route('/dev')
def dev_front_page() -> Response:
    return render_template(
        'feed.html',
        title='Dev',
    )


@lists.route('/popular')
@lists.route('/popular/<period>')
def popular(period: str = 'week') -> Response:
    logs = Log.query

    time_now = int(time.time())
    if period == 'month':
        logs = logs.filter(Log.date > time_now - 86400 * 30)
        desc = 'in the past 30 days'
    elif period == 'week':
        logs = logs.filter(Log.date > time_now - 86400 * 7)
        desc = 'in the past 7 days'
    elif period == '3days':
        logs = logs.filter(Log.date > time_now - 86400 * 3)
        desc = 'in the past 3 days'
    elif period == '3months':
        logs = logs.filter(Log.date > time_now - 86400 * 90)
        desc = 'in the past 3 months'
    else:
        period = 'all'
        desc = 'of all time'

    title = f'Most viewed logs {desc}'

    logs = logs.order_by(Log.views.desc()).paginate(g.page, 25)
    listing = render_template(
        'listing.html',
        pagination=logs,
        popular=True,
        period=period,
        controls=True,
        title=title
    )
    return render_template(
        'block.html',
        content=listing,
        title=title
    )


@lists.route('/profile/<int:steamid64>')
def steamid_matches(steamid64: int) -> Response:
    player = LogPlayer.query \
                      .filter(LogPlayer.player_id == steamid64) \
                      .order_by(LogPlayer.log_id.desc()) \
                      .first()
    profile = Profile.query.filter(Profile.id == steamid64).first()

    avatar = None
    if profile:
        avatar = profile.steamprofile['avatarmedium']
    if player:
        title = player.name
    else:
        title = to_steam3(steamid64)

    logs = Log.query \
              .filter(Log.player_cache.op('@>')(cast([steamid64], ARRAY(BigInteger)))) \
              .order_by(Log.id.desc()) \
              .paginate(g.page, 25)

    listing = render_template(
        'listing.html',
        pagination=logs,
        matches=True,
        player_id=steamid64,
        title=title,
        avatar=avatar
    )
    return render_template('block.html', content=listing, title=title)


@lists.route('/uploads/<int:steamid64>')
@lists.route('/profile/<int:steamid64>/uploads')
def steamid_uploads(steamid64: int) -> Response:
    if not steamid64:
        abort(404)

    edit = False
    admin = False
    if g.user and str(steamid64) == g.user['id']:
        edit = True

    if g.user and g.user['id'] in current_app.config['ADMINS']:
        edit = True
        admin = True

    logs = Log.query \
              .filter(Log.uploader_id == steamid64) \
              .paginate(g.page, 25)

    title = f'Uploads for SteamID {to_steam3(steamid64)}'
    listing = render_template(
        'listing.html',
        pagination=logs,
        uploads=True,
        player_id=steamid64,
        edit=edit, admin=admin,
        title=title
    )

    return render_template(
        'upload_page.html',
        content=listing,
        title=title
    )
