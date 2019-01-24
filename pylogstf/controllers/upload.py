import binascii
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import zipfile

from flask import current_app, Blueprint, g, jsonify, request, url_for, Response

from pylogstf.extensions import cache
from pylogstf.models import db, APIKey, Log, LogPlayer
from pylogstf.steamid import to_steam64
from pylogstf.tasks import after_upload, update_profile

upload = Blueprint('upload', __name__)


@upload.route('/upload', methods=['POST'])
def upload_log() -> Response:
    key = request.args.get('key') or request.form.get('key')
    ip = request.remote_addr

    if not key and not g.user:
        return jsonify(success=False, error='Missing authentication'), 400

    # Get uploader user info
    if key:
        q = APIKey.query.filter(APIKey.key == key).first()
        if not q:
            current_app.logger.error(f'Invalid API key from {ip}')
            return jsonify(success=False, error='Invalid API key'), 400
        uploader_id = q.id
        uploader_name = q.name
    else:
        uploader_id = g.user['id']
        uploader_name = g.user['nick']

    # Get form data
    log_file = request.files.get('logfile')
    log_title = request.args.get('title') or request.form.get('title')
    log_tf2map = request.args.get('map') or request.form.get('map') or ''
    log_uploader = request.form.get('uploader') or request.args.get('uploader')

    # Check if updating existing log
    log_id_to_update_str = request.form.get('updatelog')
    log_id_to_update = False
    if log_id_to_update_str:
        try:
            log_id_to_update = int(log_id_to_update_str)
        except ValueError:
            current_app.logger.error(f'Log update: Log ID should be an integer ({log_id_to_update_str}) from {ip}')
            return jsonify(success=False, error='Log update failed: Log ID should be an integer'), 400
        log_to_update = Log.query.get(log_id_to_update)
        if not log_to_update:
            current_app.logger.error(f'Log update: Log ID not found ({log_id_to_update_str}) from {ip}')
            return jsonify(success=False, error='Log update failed: Log ID not found'), 400
        if log_to_update.uploader_id != uploader_id:
            current_app.logger.error(f'Log update: User ({uploader_id}) not owner of log ({log_id_to_update_str}) from {ip}')
            return jsonify(success=False, error='Log update failed: User not owner of log'), 400
        current_time = time.time()
        if (current_time - log_to_update.date) > 60*60*5:
            return jsonify(success=False, error='Log update failed: 5 hour time limit for update'), 400
        if (current_time - log_to_update.date) < 10:
            return jsonify(success=False, error='Log update failed: Updated too quickly (10sec limit)'), 400

    # Form data validation
    if not log_title or len(log_title) < 4:
        log_title = log_file.filename if len(log_file.filename) > 4 else 'Log'
    if not log_file:
        current_app.logger.error('No file from {ip}')
        return jsonify(success=False, error='No file'), 400
    log_title = log_title[:40]
    tf2map = log_tf2map[:24]
    if log_uploader:
        log_uploader = log_uploader[:40]

    # Save log file to temporary storage
    temp_log_file_name = binascii.b2a_hex(os.urandom(16)).decode() + '.log'
    temp_log_file_path = os.path.join(
        current_app.config['UPLOAD_FOLDER'], temp_log_file_name
    )
    log_file.save(temp_log_file_path)

    # Remove bad stuff from the log file
    # Blocking, but fast execution
    secure_log(temp_log_file_path, [
        ': ".+" = ".+"',
        'rcon from ',
        'server_cvar:',
        'connect .+\\..+'
    ])

    # Send log to log parser
    try:
        json_string = subprocess.check_output(
            ['node', current_app.config['PARSER'], temp_log_file_path],
            cwd=current_app.config['PARSER_FOLDER'],
            stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        err = 'Invalid log file'
        # If parser throws error, get the error message (hacky!)
        pattern = re.compile(r"throw '(.+)'")
        match = pattern.search(str(e.output))
        if match:
            err = match.group(1)
        current_app.logger.error(f'Parser failed from {ip} file {temp_log_file_name} reason: {err}')
        return jsonify(success=False, error=err), 500
    # except Exception:
    #     current_app.logger.error(f'Exception {sys.exc_info()[0]} from {ip} file {temp_log_file_name}')
    #     return jsonify(success=False, error='Invalid log file'), 500

    # Parse log parser's JSON output
    try:
        parsed_log = json.loads(json_string.decode())
    except json.JSONDecodeError:
        current_app.logger.error(f'Invalid parser JSON output from {ip} file {temp_log_file_name}')
        return jsonify(success=False, error='Guru Meditation'), 500

    # Get detected map name if not provided
    if not tf2map and parsed_log['info']['map']:
        tf2map = parsed_log['info']['map'][:24]

    # Generate hash to check for duplicate logs
    log_hash: str = hashlib.md5(json_string).hexdigest()
    collision: Log = Log.query.filter(Log.hash == log_hash).first()
    if collision:
        return jsonify(
            success=False,
            error=f'Log already exists ({collision.id})',
            log_id=collision.id
        ), 400


    player_steamids = []
    for player_id in parsed_log['names']:
        player_steamid = to_steam64(player_id)
        if player_steamid > 0:
            player_steamids.append(player_steamid)


    # Add to database
    if not log_id_to_update:
        log = Log(
            logname=log_title,
            logdata=json_string.decode('utf-8'),
            uploader_id=uploader_id,
            uploader_name=uploader_name,
            uploader_desc=log_uploader,
            tf2map=tf2map,
            date=int(time.time()),
            hash=log_hash,
            player_cache=player_steamids,
            player_count=len(player_steamids),
        )
        db.session.add(log)
    else:
        log_to_update.logname = log_title
        log_to_update.logdata = json_string.decode('utf-8')
        log_to_update.tf2map = tf2map
        log_to_update.date = time.time()
        log_to_update.is_updated = True
        log_to_update.hash = log_hash
        log_to_update.player_cache = player_steamids
        log_to_update.player_count = len(player_steamids)
    db.session.commit()

    # UPDATE ONLY: Clean old steamids
    if log_id_to_update:
        LogPlayer.query \
            .filter(LogPlayer.log_id == log_id_to_update) \
            .delete(synchronize_session=False)
        db.session.commit()

    if log_id_to_update:
        log_id = int(log_id_to_update)
    else:
        log_id = int(log.id)

    # Save steamids associated with the log
    player_steamids = []
    for player_id in parsed_log['names']:
        player_steamid = to_steam64(player_id)
        if player_steamid > 0:
            new_player = LogPlayer(
                log_id=log_id,
                player_id=player_steamid,
                name=parsed_log['names'][player_id]
            )
            db.session.add(new_player)
    db.session.commit()

    # Invalidate caches
    cache.delete('front_page')
    cache.delete(f'log:{log_id}')
    cache.delete(f'log:title:{log_id}')
    cache.delete(f'log:desc:{log_id}')

    # Move away from temporary location
    new_log_filename = f'log_{log_id}.log'
    new_log_path = os.path.join(current_app.config['LOG_FOLDER'], new_log_filename)
    shutil.move(temp_log_file_path, new_log_path)

    # Compress log to zip
    zip_filename = f'log_{log_id}.log.zip'
    zip_path = os.path.join(current_app.config['LOG_FOLDER'], zip_filename)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as logzip:
        logzip.write(new_log_path, new_log_filename)
    os.remove(new_log_path)

    #after_upload.delay(log_id, temp_log_file_path)
    #update_profile.delay(player_steamids)

    current_app.logger.info(f'Added log {log_id}: '
                            f'{log_title} @ {log_tf2map} [{uploader_id}] from {ip}')

    return jsonify(
        success=True,
        log_id=int(log_id),
        url=url_for('view.view_log', log_id=log_id),
    ), 200


def secure_log(file, filters):
    """Cleans up sensitive data from a log file."""
    ifile = open(file, 'r', errors='replace')
    lines = ifile.readlines()
    ifile.close()

    ofile = open(file, 'w', errors='replace')
    for line in lines:
        for log_filter in filters:
            if re.search(log_filter, line):
                break
        else:
            # Rewrite IPs to 0.0.0.0
            line = re.sub(r'[0-9]+(\.[0-9]+){3}', '0.0.0.0', line)
            ofile.write(line)
    ofile.close()
