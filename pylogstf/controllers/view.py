import json

from flask import current_app, Blueprint, abort, escape, g, render_template, request, Response

from pylogstf.extensions import cache
from pylogstf.template import mmss_filter
from pylogstf.models import Log, db

view = Blueprint('view', __name__)



@view.route('/<int:log_id>')
def view_log(log_id: int) -> Response:
    log = Log.query.get_or_404(log_id)

    # View count increment
    if not g.user or str(log.uploader_id) != g.user['id']:
        # Simple IP based view count spam avoidance
        current_ip = request.environ['REMOTE_ADDR']
        lastview_ip = cache.get(f'lastview:{log_id}')
        if lastview_ip != current_ip:
            log.views += 1
            db.session.commit()
            cache.set(f'lastview:{log_id}', current_ip, timeout=60*5)

    # Cached response
    cached_log = cache.get(f'log:{log_id}')
    if cached_log and not request.args.get('cached') == '0':
        cached_title = cache.get(f'log:title:{log_id}')
        cached_description = cache.get(f'log:desc:{log_id}')
        return render_template(
            'log_page.html',
            log=cached_log,
            title=cached_title,
            description=cached_description
        )

    try:
        data = json.loads(log.logdata)
    except json.JSONDecodeError:
        abort(500)

    # Sort healspreads by team
    data['healspread_sorted'] = []
    for healer in data['healspread']:
        if healer in data['players']:
            if data['players'][healer]['team'] == 'Blue':
                data['healspread_sorted'].insert(0, healer)
            else:
                data['healspread_sorted'].append(healer)

    description = '{title} @ {map} ({time})'.format(
        title=escape(log.logname),
        map=escape(log.tf2map),
        time=mmss_filter(data['info']['total_length'])
    )


    timeout_seconds = current_app.config['LOG_CACHE_TIMEOUT_IN_SECONDS']

    output = render_template(
        'view_log.html',
        id=log.id,
        name=log.logname,
        title=log.logname,
        tf2map=log.tf2map,
        uid=log.uploader_id,
        uploader=log.uploader_name,
        uploader_desc=log.uploader_desc,
        date=log.date,
        l=data,
    )
    cache.set(
        f'log:desc:{log_id}',
        description,
        timeout=timeout_seconds
    )
    cache.set(
        f'log:title:{log_id}',
        log.logname,
        timeout=timeout_seconds
    )
    cache.set(
        f'log:{log_id}',
        output,
        timeout=timeout_seconds
    )

    return render_template(
        'log_page.html',
        log=output,
        title=log.logname,
        description=description
    )


@view.route('/<int:log_id>/stream')
def view_log_stream(log_id: int) -> Response:
    log = Log.query.get_or_404(log_id)

    try:
        data = json.loads(log.logdata)
    except json.JSONDecodeError:
        abort(500)

    # Sort healspreads by team
    data['healspread_sorted'] = []
    for healer in data['healspread']:
        if healer in data['players']:
            if data['players'][healer]['team'] == 'Blue':
                data['healspread_sorted'].insert(0, healer)
            else:
                data['healspread_sorted'].append(healer)

    return render_template(
        'view_log_stream.html',
        id=log.id,
        name=log.logname,
        title=log.logname,
        tf2map=log.tf2map,
        uid=log.uploader_id,
        uploader=log.uploader_name,
        uploader_desc=log.uploader_desc,
        date=log.date,
        l=data
    )
