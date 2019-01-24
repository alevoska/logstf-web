from flask import Blueprint, g, render_template, Response

from pylogstf.models import APIKey
from pylogstf.extensions import login_required

pages = Blueprint('pages', __name__)


@pages.route('/about')
def about_page() -> Response:
    return render_template('about.html', title="About")


@pages.route('/privacy')
def privacy_page() -> Response:
    return render_template('privacy.html', title="Privacy Policy")


@pages.route('/uploader')
@login_required
def uploader() -> Response:
    apikey = APIKey.query.filter(APIKey.id == g.user['id']).first()

    try:
        key = apikey.key
    except (ValueError, AttributeError):
        key = None

    return render_template(
        'uploader.html',
        apikey=key,
        showapikey=True,
        title="Upload"
    )
