import os


def _bool(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


CONFIG = {
    'database': os.environ.get('TRACKIFY_DB_NAME', 'trackify'),
    'database_user': os.environ.get('TRACKIFY_DB_USER', 'trackify'),
    'database_password': os.environ.get('TRACKIFY_DB_PASSWORD', 'trackify'),
    'database_host': os.environ.get('TRACKIFY_DB_HOST', '127.0.0.1'),
    'secret_key': os.environ.get('TRACKIFY_SECRET_KEY', ''),
    'client_id': os.environ.get('TRACKIFY_SPOTIFY_CLIENT_ID', ''),
    'client_secret': os.environ.get('TRACKIFY_SPOTIFY_CLIENT_SECRET', ''),
    'scope': os.environ.get(
        'TRACKIFY_SPOTIFY_SCOPE',
        'user-library-read playlist-read-private user-read-playback-state user-read-currently-playing user-modify-playback-state',
    ),
    'redirect_uri': os.environ.get(
        'TRACKIFY_REDIRECT_URI', 'http://localhost:8091/spotify/callback'
    ),
    'permanent_session': _bool('TRACKIFY_PERMANENT_SESSION', True),
    'discogs_api_key': os.environ.get('TRACKIFY_DISCOGS_API_KEY', ''),
    'discogs_api_secret': os.environ.get('TRACKIFY_DISCOGS_API_SECRET', ''),
}

CONFIG_UPPERCASE = {key.upper(): value for key, value in CONFIG.items()}
