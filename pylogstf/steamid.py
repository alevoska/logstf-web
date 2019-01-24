import re
from typing import Union

def to_steam64(steamid_str: str) -> int:
    """Converts a SteamID3 or SteamID2 into a 64-bit SteamID."""
    # SteamID3
    steamid = re.compile(r'\[U:1:(\d{1,10})\]').match(steamid_str)
    if steamid:
        token = steamid.groups()
        return 76561197960265728 + int(token[0])

    # SteamID2
    steamid = re.compile(r'STEAM_0:([01]):(\d{1,10})').match(steamid_str)
    if steamid:
        token = steamid.groups()
        server = int(token[0])
        auth = int(token[1]) * 2
        return 76561197960265728 + auth + server

    return 0


def to_steam3(steamid64: Union[str, int]) -> str:
    """Converts a 64-bit SteamID into SteamID3."""
    try:
        auth = (int(steamid64) - 76561197960265728)
        return f'[U:1:{auth}]'
    except ValueError:
        return ''
