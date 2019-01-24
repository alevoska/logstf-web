import urllib
from datetime import datetime
from typing import Union

from pylogstf.weapons import WEAPONS


def datetime_filter(string: Union[int, str]) -> str:
    """Converts unix timestamp into 'dd-mm-yyyy HH:MM:SS' format."""
    return datetime.utcfromtimestamp(string).strftime('%d-%b-%Y %H:%M:%S')


def number_format(value: str) -> str:
    return "{:,}".format(value)


def mmss_filter(seconds: Union[int, str]) -> str:
    """Converts seconds into MM:SS format."""
    try:
        m, s = divmod(int(seconds), 60)
        return '%02d:%02d' % (m, s)
    except ValueError:
        return '00:00'


def urlencode_filter(string: str) -> str:
    return urllib.parse.quote_plus(string)


def weapon_filter(weapon_name: str) -> str:    
    """Returns a human-readable name for weapons."""
    if weapon_name in WEAPONS:
        return WEAPONS[weapon_name]
    return weapon_name.title().replace('_', ' ')


def weaponsort(weapons: str) -> list:
    """Sorts weapons based on most kills."""
    return sorted(weapons.items(), key=lambda w: w[1]['kills'], reverse=True)
