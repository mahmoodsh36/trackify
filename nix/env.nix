# single source of truth for the TRACKIFY_* vars that config.py reads.
# both the nixos module and the dev stack build their environment from here.
# a null value means "leave unset", so it falls back to config.py's default or
# to whatever is already in the caller's environment.

{ lib }:

settings:

lib.mapAttrs (_: toString) (lib.filterAttrs (_: v: v != null) {
  TRACKIFY_DB_NAME = settings.database.name;
  TRACKIFY_DB_USER = settings.database.user;
  TRACKIFY_DB_PASSWORD = settings.database.password;
  TRACKIFY_DB_HOST = settings.database.host;
  TRACKIFY_DB_PORT = settings.database.port or null;
  TRACKIFY_BIND = "127.0.0.1:${toString settings.port}";
  TRACKIFY_WORKERS = settings.workers;
  TRACKIFY_REDIRECT_URI = settings.redirectUri;
  TRACKIFY_SECRET_KEY = settings.secretKey;
  TRACKIFY_SPOTIFY_CLIENT_ID = settings.spotify.clientId;
  TRACKIFY_SPOTIFY_CLIENT_SECRET = settings.spotify.clientSecret;
  TRACKIFY_SPOTIFY_SCOPE = settings.spotify.scope;
  TRACKIFY_DISCOGS_API_KEY = settings.discogs.apiKey;
  TRACKIFY_DISCOGS_API_SECRET = settings.discogs.apiSecret;
})
