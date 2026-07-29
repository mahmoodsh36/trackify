from flask import Blueprint, render_template, g, redirect, request, url_for, jsonify

from trackify.utils import (
    uri_encode, generate_id, current_time, get_largest_elements, mins_from_ms,
    hrs_from_ms, secs_from_ms
)
from trackify.webapp.blueprints.auth import login_required
from trackify.db.classes import SpotifyAuthCode, User, Track, Artist, Image, Album, Setting
from trackify.utils import timestamp_to_date, current_time

bp = Blueprint('spotify', __name__, url_prefix='/spotify')

@bp.route('/auth', methods=('GET',))
@login_required
def auth():
    spotify_auth_url = "https://accounts.spotify.com/authorize" +\
        "?response_type=code" +\
        '&client_id={}'.format(g.spotify_client.client_id) +\
        '&scope={}'.format(uri_encode(g.spotify_client.scope)) +\
        '&redirect_uri={}'.format(uri_encode(g.spotify_client.redirect_uri))
    return redirect(spotify_auth_url)

@bp.route('/callback', methods=('GET',))
@login_required
def callback():
    auth_code = SpotifyAuthCode(generate_id(), request.args['code'],
                            g.user, current_time())
    g.db_data_provider.add_spotify_auth_code(auth_code)
    refresh_token, access_token = g.spotify_client.fetch_refresh_token(auth_code)
    if access_token and refresh_token:
        g.db_data_provider.add_spotify_refresh_token(refresh_token)
        g.db_data_provider.add_spotify_access_token(access_token)
    return redirect(url_for('home.index'))

@bp.route('/data', methods=('GET',))
@login_required
def data():
    entry_limit = request.args.get('entry_limit')
    hrs_limit = request.args.get('time_limit')
    sort_by = request.args.get('sort_by')
    display_tracks = request.args.get('display_tracks')
    display_artists = request.args.get('display_artists')
    display_albums = request.args.get('display_albums')

    if not display_tracks and not display_artists and not display_albums:
        display_tracks, display_artists = True, True

    if not entry_limit:
        entry_limit = 50
    if not hrs_limit:
        hrs_limit = 24 * 7
    if not sort_by:
        sort_by = 'time_listened'
    elif sort_by != 'time_listened' and sort_by != 'time_added':
        return ''
    try:
        hrs_limit = int(hrs_limit)
        entry_limit = int(entry_limit)
    except:
        return ''
    if entry_limit > 500:
        entry_limit = 500
    if hrs_limit > 24 * 30:
        hrs_limit = 24 * 30

    if hrs_limit == 0:
        begin_time = 0 # the listened_ms function will handle it correctly
    else:
        begin_time = current_time() - hrs_limit * 3600 * 1000

    if sort_by == 'time_listened':
        artists, albums, tracks = g.db_data_provider.get_user_listened_ms_by_track(
            g.user, from_time=begin_time)

        for album in albums.values():
            for track in album.tracks:
                if hasattr(album, 'listened_ms'):
                    album.listened_ms += track.listened_ms
                else:
                    album.listened_ms = track.listened_ms
                if album.listened_ms > 0:
                    album.should_be_displayed = True

        for artist in artists.values():
            for album in artist.albums:
                if hasattr(album, 'listened_ms'):
                    if hasattr(artist, 'listened_ms'):
                        artist.listened_ms += album.listened_ms
                    else:
                        artist.listened_ms = album.listened_ms
                    if artist.listened_ms > 0:
                        artist.should_be_displayed = True
    elif sort_by == 'time_added':
        artists, albums, tracks, plays = g.db_data_provider.get_user_data(
            g.user, from_time=begin_time)

        for play in plays.values():
            if hasattr(play.track, 'time_added'):
                if play.track.time_added > play.time_started:
                    play.track.time_added = play.time_started
            else:
                play.track.time_added = play.time_started
            if not hrs_limit or\
                current_time() - play.track.time_added < hrs_limit * 3600 * 1000:
                play.track.should_be_displayed = True
            else:
                play.track.should_be_displayed = False

        for album in albums.values():
            for track in album.tracks:
                if hasattr(album, 'time_added'):
                    if album.time_added > track.time_added:
                        album.time_added = track.time_added
                else:
                    album.time_added = track.time_added
                if not hrs_limit or\
                   current_time() - album.time_added < hrs_limit * 3600 * 1000:
                    album.should_be_displayed = True
                else:
                    album.should_be_displayed = False

        for artist in artists.values():
            for album in artist.albums:
                if hasattr(album, 'time_added'):
                    if hasattr(artist, 'time_added'):
                        if artist.time_added > album.time_added:
                            artist.time_added = album.time_added
                    else:
                        artist.time_added = album.time_added
                    if not hrs_limit or\
                       current_time() - artist.time_added < hrs_limit * 3600 * 1000:
                        artist.should_be_displayed = True
                    else:
                        artist.should_be_displayed = False

    def compare(music_obj1, music_obj2):
        if sort_by == 'time_listened':
            if not hasattr(music_obj1, 'listened_ms'):
                return False
            if not hasattr(music_obj2, 'listened_ms'):
                return True
            return music_obj1.listened_ms > music_obj2.listened_ms
        elif sort_by == 'time_added':
            if not hasattr(music_obj1, 'time_added'):
                return False
            if not hasattr(music_obj2, 'time_added'):
                return True
            return music_obj1.time_added > music_obj2.time_added

    top_tracks = get_largest_elements(list(tracks.values()), entry_limit, compare)
    top_albums = get_largest_elements(list(albums.values()), entry_limit, compare)
    top_artists = get_largest_elements(list(artists.values()), entry_limit, compare)
    
    return render_template('data.html',
                           top_tracks=top_tracks,
                           top_albums=top_albums,
                           top_artists=top_artists,
                           mins_from_ms=mins_from_ms,
                           hrs_from_ms=hrs_from_ms,
                           secs_from_ms=secs_from_ms,
                           entry_limit=entry_limit,
                           sort_by=sort_by,
                           hrs_limit=hrs_limit,
                           hasattr=hasattr,
                           current_time=current_time,
                           display_albums=display_albums,
                           display_artists=display_artists,
                           display_tracks=display_tracks)

@bp.route('/top_users', methods=('GET',))
def top_users():
    hrs_limit = request.args.get('time_limit')
    if not hrs_limit:
        hrs_limit = 7 * 24
    try:
        hrs_limit = int(hrs_limit)
    except:
        return ''
    if hrs_limit > 7 * 24:
        hrs_limit = 30 * 24 # past month is the limit

    if hrs_limit not in [24, 24*7, 24*30]:
        return ''

    top_users = g.cache_data_provider.get_top_users(hrs_limit)

    return render_template('top_users.html',
                           top_users=top_users,
                           mins_from_ms=mins_from_ms,
                           hrs_from_ms=hrs_from_ms,
                           secs_from_ms=secs_from_ms,
                           hrs_limit=hrs_limit)

@bp.route('/history', methods=('GET',))
@login_required
def history():
    hrs_limit = request.args.get("hrs_limit", default=24, type=int)
    if hrs_limit < 1:
        hrs_limit = 24
    if hrs_limit > 30 * 24:
        hrs_limit = 30 * 24 # past month is the limit

    artists, albums, tracks, plays =\
        g.db_data_provider.get_user_data(g.user, current_time() - hrs_limit * 3600 * 1000)
    for play in plays.values():
        play.listened_ms_cached = play.listened_ms()
        play.played_date = timestamp_to_date(play.time_started).strftime('%d/%m/%Y')
        play.played_time = timestamp_to_date(play.time_started).strftime('%H:%M:%S')

    def compare(play1, play2):
        return play1.time_started > play2.time_started
    sorted_plays = get_largest_elements(list(plays.values()), -1, compare)

    return render_template('history.html',
                           plays=sorted_plays,
                           hrs_from_ms=hrs_from_ms,
                           mins_from_ms=mins_from_ms,
                           secs_from_ms=secs_from_ms,
                           hrs_limit=hrs_limit)
