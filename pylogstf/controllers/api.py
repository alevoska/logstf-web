import binascii
import json
import os

from flask import Blueprint, Response, abort, g, jsonify, request
from flask import current_app as app
from flask_cors import cross_origin

from pylogstf.models import APIKey, Log, LogPlayer, db, like_string
from pylogstf.steamid import to_steam64
from pylogstf.extensions import cache, login_required, require_token

from sqlalchemy import cast, BigInteger, func, text
from sqlalchemy.dialects.postgresql import ARRAY

web_api = Blueprint('web_api', __name__)
json_api = Blueprint('json_api', __name__)


@json_api.errorhandler(500)
def api_internal_error(error):
    return jsonify(success=False, error='Internal server error'), 500


@json_api.route('/json/<int:log_id>')
@json_api.route('/api/v1/log/<int:log_id>')
@cross_origin()
def get_json(log_id: int) -> Response:
    log = Log.query.get(log_id)
    if not log:
        return jsonify(success=False, error="Log not found."), 404

    try:
        data = json.loads(log.logdata)
        data['success'] = True
        data['info']['title'] = log.logname
        data['info']['map'] = log.tf2map
        data['info']['date'] = log.date
        data['info']['uploader'] = {
            "id": str(log.uploader_id),
            "name": log.uploader_name,
            "info": log.uploader_desc,
        }
    except KeyError:
        data = {
            "success": False,
            "error": "Internal JSON error"
        }
        app.logger.error(f'Invalid JSON in Log {log.id}')

    return Response(json.dumps(data), mimetype="application/json")


@json_api.route('/api/experimental/players')
@cross_origin()
def search_players() -> Response:
    playerid_string = request.args.get('players')
    try:
        players = [int(x.strip()) for x in playerid_string.split(",")]
    except Exception:
        return jsonify(
            success=False,
            error="Invalid format. Use comma-separated numerical player ids."
        ), 400

    if len(players) < 2:
        return jsonify(
            success=False,
            error="Minimum amount of players is 2."
        ), 400
    if len(players) > 18:
        return jsonify(
            success=False,
            error="Maximum amount of players is 18."
        ), 400

    query = db.session.query(LogPlayer.log_id)
    for p in players:
        query = query.intersect(
            db.session.query(LogPlayer.log_id).filter(LogPlayer.player_id == p)
        )

    result = query.order_by(LogPlayer.log_id.desc()).all()

    logs = [r[0] for r in result]
    return jsonify(success=True, count=len(logs), logs=logs)


@json_api.route('/json_search')
@json_api.route('/api/v1/log')
@cross_origin()
def search_json() -> Response:
    playerid_string = request.args.get('player')
    uploaderid_string = request.args.get('uploader')
    log_string = request.args.get('title')
    map_string = request.args.get('map')
    format_string = request.args.get('format')
    limit_string = request.args.get('limit')
    offset_string = request.args.get('offset')

    if log_string and len(log_string) < 3:
        return jsonify(
            success=False,
            error='Title should be longer than 2 characters'
        ), 400

    if log_string:
        log_string = like_string(log_string)
        log_search_string = '%' + log_string + '%'

    if map_string and len(map_string) < 3:
        return jsonify(
            success=False,
            error='Map name should be longer than 2 characters'
        ), 400

    players = []
    try:
        if playerid_string:
            players = [int(x.strip()) for x in playerid_string.split(",")]
    except Exception:
        return jsonify(
            success=False,
            error='Invalid format. Use comma-separated numerical player ids.'
        ), 400

    if len(players) > 18:
        return jsonify(
            success=False,
            error="Maximum amount of players is 18."
        ), 400

    uploader_id = None
    if uploaderid_string:
        uploader_id = to_steam64(uploaderid_string)
        if uploader_id == 0:
            try:
                uploader_id = int(uploaderid_string)
            except ValueError:
                return jsonify(
                    success=False,
                    error='Uploader id is invalid'
                ), 400


    logs = Log.query
    if len(players) > 0:
        logs = logs.filter(Log.player_cache.op('@>')(cast(players, ARRAY(BigInteger))))
    if uploader_id:
        logs = logs.filter(Log.uploader_id == uploader_id)
    if log_string:
        logs = logs.filter(Log.logname.ilike(log_search_string, escape=None))
    if map_string:
        logs = logs.filter(Log.tf2map.like(f'{like_string(map_string)}%'))

    if format_string == "highlander":
        logs = logs.filter(Log.player_count > 17)
    elif format_string == "6v6":
        logs = logs.filter((Log.player_count < 18) & (Log.player_count > 10))
    elif format_string == "4v4":
        logs = logs.filter((Log.player_count < 11) & (Log.player_count > 7))
    elif format_string == "2v2":
        logs = logs.filter((Log.player_count < 8) & (Log.player_count > 3))
    elif format_string == "1v1":
        logs = logs.filter(Log.player_count < 4)

    logs = logs.order_by(Log.id.desc())

    limit = 1000
    if limit_string:
        try:
            limit = int(limit_string)
        except ValueError:
            pass

    offset = 0
    if offset_string:
        try:
            offset = int(offset_string)
        except ValueError:
            pass

    limit = max(0, limit)
    limit = min(10000, limit)
    offset = max(0, offset)
    offset = min(100000000, offset)

    logs_count = logs.count()

    logs_query = logs.limit(limit).offset(offset).all()

    logs = [{
        'id': log.id,
        'title': log.logname,
        'map': log.tf2map,
        'date': log.date,
        'views': log.views,
        'players': log.player_count,
    } for log in logs_query]

    parameters = {
        "player": playerid_string,
        "uploader": uploaderid_string,
        "title": log_string,
        "map": map_string,
        "limit": limit,
        "offset": offset,
    }

    data = {
        "success": True,
        "results": len(logs),
        "total": logs_count,
        "parameters": parameters,
        "logs": logs,
    }

    return Response(json.dumps(data, indent=4), mimetype='application/json')


@json_api.route('/api/v1/player_search')
@cross_origin()
def search_player() -> Response:
    max_player_names = 3
    max_player_results = 10

    search_str = request.args.get('name')

    if len(search_str) < 3:
        return jsonify(
            success=False
        ), 400

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
                'id': str(player.player_id),
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
    final_list = []
    for player in sorted_players:
        player[1]['names'] = sorted(
            player[1]['names'].items(),
            key=lambda x: x[1],
            reverse=True
        )
        player[1]['names'] = player[1]['names'][:max_player_names]
        final_list.append(player[1])
    final_list = final_list[:max_player_results]
    """for player in final_list:
        player[1]['avatar'] = None
        profile = Profile.query.filter(Profile.id == player[0]).first()
        if profile:
            player[1]['avatar'] = profile.steamprofile['avatar']"""


    return jsonify(
        success=True,
        players=final_list
    )


@json_api.route('/api/<path:path>')
def api_404(path: str):
    return jsonify(success=False, error="Invalid endpoint."), 404



@web_api.route('/<int:log_id>/update')
@login_required
@require_token
def edit_log(log_id: int) -> Response:
    title = request.args.get('title')
    tf2map = request.args.get('tf2map')
    title = title[:40]
    tf2map = tf2map[:24]
    if (len(title) < 4):
        return jsonify(
            success=False,
            error="Name must be over 4 characters"
        ), 400

    log = Log.query.get_or_404(log_id)
    if str(log.uploader_id) == g.user['id'] or g.user['id'] in app.config['ADMINS']:
        log.logname = title
        log.tf2map = tf2map
        db.session.commit()
        cache.delete(f'log:{log_id}')
        cache.delete(f'log:title:{log_id}')
        cache.delete(f'log:desc:{log_id}')
        cache.delete('front_page')
        return jsonify(
            success=True,
            log_id=log_id,
            title=title,
            tf2map=tf2map
        )
    return abort(403)


@web_api.route('/<int:log_id>/delete')
@login_required
@require_token
def delete_log(log_id: int) -> Response:
    log = Log.query.get_or_404(log_id)
    if str(log.uploader_id) == g.user['id'] or g.user['id'] in app.config['ADMINS']:
        db.session.delete(log)
        db.session.commit()
        filepath = os.path.join(
            app.config['LOG_FOLDER'], f'log_{log_id}.log.zip'
        )
        try:
            os.remove(filepath)
        except Exception:
            app.logger.error(f'Could not delete log file: {filepath}')
        cache.delete(f'log:{log_id}')
        cache.delete(f'log:title:{log_id}')
        cache.delete(f'log:desc:{log_id}')
        cache.delete('front_page')
        return jsonify(success=True, log_id=log_id)
    return jsonify(success=False), 403


@web_api.route('/<int:log_id>/resetviews')
@login_required
@require_token
def resetviews_log(log_id: int) -> Response:
    log = Log.query.get_or_404(log_id)
    if g.user['id'] in app.config['ADMINS']:
        log.views = 0
        db.session.commit()
        return jsonify(success=True, log_id=log_id)
    return jsonify(success=False, error='Not authorized.'), 403


@web_api.route('/createkey')
@login_required
@require_token
def create_apikey() -> str:
    random_str = binascii.b2a_hex(os.urandom(8)).decode()
    new_key = f'{g.user["id"]}#{random_str}'
    apikey = APIKey.query.filter(APIKey.id == g.user['id']).first()

    if not apikey:
        apikey = APIKey(
            id=g.user['id'],
            name=g.user['nick'],
            key=new_key,
        )
        db.session.add(apikey)
    else:
        apikey.name = g.user['nick']
        apikey.key = new_key

    db.session.commit()
    return new_key
