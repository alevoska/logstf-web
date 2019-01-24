from flask import (Blueprint, flash, g, redirect, render_template,
                   request, url_for, Response)
from sqlalchemy import func, text

from pylogstf.tasks import update_profile
from pylogstf.models import Log, LogPlayer, db, like_string, Profile
from pylogstf.steamid import to_steam64

search = Blueprint('search', __name__)


@search.route('/search_log')
@search.route('/search/log')
def search_log() -> Response:
    search_str = request.args.get('s') or ''
    search_str = search_str[:60]
    if len(search_str) < 2:
        flash('Log title should be over 2 characters long.')
        return redirect(url_for('lists.front_page'))

    db_search_str = f'%{like_string(search_str)}%'
    logs = Log.query \
        .filter(Log.logname.ilike(db_search_str, escape=None)) \
        .paginate(g.page, 25)
    title = f'Log search results for "{search_str}"'
    listing = render_template(
        'listing.html',
        pagination=logs,
        search=search_str,
        title=title
    )
    return render_template('block.html', content=listing, title=title)


@search.route('/search_player')
@search.route('/search/player')
def search_player() -> Response:
    max_player_names = 3
    max_player_results = 25

    search_str = request.args.get('s') or ''
    if len(search_str) < 2:
        flash('Player name should be over 2 characters long.')
        return redirect(url_for('lists.front_page'))

    steamid = to_steam64(search_str)
    if steamid:
        return redirect(url_for('lists.steamid_matches', steamid64=steamid))

    if search_str.isdigit() and search_str.startswith('7656119'):
        return redirect(url_for('lists.steamid_matches', steamid64=int(search_str)))

    db_search_str = f'%{like_string(search_str)}%'
    players = db.session.query(
        LogPlayer.player_id,
        LogPlayer.name,
        func.count(LogPlayer.player_id)
        .label('total')
    ) \
        .filter(LogPlayer.name.ilike(db_search_str, escape=None)) \
        .group_by(LogPlayer.player_id, LogPlayer.name) \
        .order_by(text('total DESC')) \
        .all()

    ids = {}
    for player in players:
        if player.player_id not in ids:
            ids[player.player_id] = {
                'count': player.total,
                'names': {}
            }
        else:
            ids[player.player_id]['count'] += player.total
        ids[player.player_id]['names'][player.name] = player.total

    # Create final grouped & sorted list
    # Maybe some refactoring?
    sorted_players = sorted(
        ids.items(),
        key=lambda x: x[1]['count'],
        reverse=True
    )
    # player[0] is steamid
    # player[1] has names & avatars
    for player in sorted_players:
        player[1]['names'] = sorted(
            player[1]['names'].items(),
            key=lambda x: x[1],
            reverse=True
        )
        player[1]['names'] = player[1]['names'][:max_player_names]
    final_list = sorted_players[:max_player_results]
    for player in final_list:
        player[1]['avatar'] = None
        profile = Profile.query.filter(Profile.id == player[0]).first()
        if profile:
            player[1]['avatar'] = profile.steamprofile['avatar']

    # Update profiles (not really essential)
    steamids = [player[0] for player in final_list]
    # update_profile.delay(steamids)

    title = f'Player search results for {search_str}'
    return render_template(
        'players.html',
        players=final_list,
        title=title,
        search=search_str,
    )
