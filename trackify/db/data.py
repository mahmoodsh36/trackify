from trackify.db.classes import *
from trackify.utils import get_largest_elements

class DbDataProvider:
    def __init__(self, *args, **kwargs):
        self.db_provider = DbProvider(*args, **kwargs)

    def close(self):
        self.db_provider.close()

    def commit(self):
        self.db_provider.commit()

    def new_conn(self):
        self.db_provider.new_conn()

    def get_user_by_username(self, username):
        user_row = self.db_provider.get_user_by_username(username)
        if user_row:
            return User(user_row['id'], user_row['username'], user_row['password'],
                        user_row['email'], user_row['time_added'])
        return None

    def add_user(self, user):
        self.db_provider.add_user(user.id, user.username, user.password, user.email,
                                  user.time_added)
        self.commit()

    def add_request(self, request):
        user_id = None
        if request.user:
            user_id = request.user.id
        self.db_provider.add_request(request.id, request.time_added, request.ip,
                                     request.url, request.headers, request.data,
                                     request.form, request.referrer,
                                     request.access_route, user_id)
        self.commit()

    def add_spotify_auth_code(self, code):
        self.db_provider.add_spotify_auth_code(code.id, code.time_added, code.code, code.user.id)
        self.commit()

    def add_spotify_access_token(self, t):
        self.db_provider.add_spotify_access_token(t.id, t.token, t.user.id, t.time_added)
        self.commit()

    def add_spotify_refresh_token(self, t):
        self.db_provider.add_spotify_refresh_token(t.id, t.token, t.user.id, t.time_added)
        self.commit()

    def get_user(self, user_id):
        user_row = self.db_provider.get_user(user_id)
        if user_row:
            return User(user_row['id'], user_row['username'], user_row['password'],
                        user_row['email'], user_row['time_added'])
        return None

    def get_user_spotify_auth_code(self, user):
        code_row = self.db_provider.get_user_spotify_auth_code(user.id)
        if code_row:
            return SpotifyAuthCode(code_row['id'], code_row['code'], user,
                            code_row['time_added'])
        return None

    def get_user_spotify_access_token(self, user):
        token_row = self.db_provider.get_user_spotify_access_token(user.id)
        if token_row:
            return SpotifyAccessToken(token_row['id'], token_row['token'], user,
                               token_row['time_added'])
        return None

    def get_user_spotify_refresh_token(self, user):
        token_row = self.db_provider.get_user_spotify_refresh_token(user.id)
        if token_row:
            return SpotifyRefreshToken(token_row['id'], token_row['token'], user,
                                token_row['time_added'])
        return None

    def get_users(self):
        user_rows = self.db_provider.get_users()
        users = []
        for user_row in user_rows:
            user = User(user_row['id'], user_row['username'], user_row['password'],
                        user_row['email'], user_row['time_added'])
            users.append(user)
        return users

    def get_users_with_spotify_tokens(self):
        rows = self.db_provider.get_users_with_spotify_tokens()
        users = []
        for row in rows:
            user = User(row['id'], row['username'], row['password'], row['email'],
                        row['time_added'])
            user.spotify_access_token = SpotifyAccessToken(row['id'], row['token'], user,
                                            row['time_added'])
            user.spotify_refresh_token = SpotifyRefreshToken(row['id'], row['token'], user,
                                              row['time_added'])
            users.append(user)
        return users

    # fetched separately from the plays/tracks/artists/albums join: albums have
    # multiple images each, so joining them onto the play rows multiplies every
    # play by its album's image count instead of adding a handful of extra rows.
    def _attach_album_images(self, albums):
        image_rows = self.db_provider.get_images_for_albums(list(albums.keys()))
        for row in image_rows:
            image = Image(row['id'], row['url'], row['width'], row['height'])
            albums[row['album_id']].add_image(image)

    # fetched separately from the plays join for the same reason as album images:
    # a play can have several pauses and several resumes, so joining both onto the
    # play row multiplies it by pauses * resumes instead of adding a few rows.
    def _attach_pauses_and_resumes(self, plays, pause_rows, resume_rows):
        for row in pause_rows:
            play = plays[row['play_id']]
            play.pauses.append(Pause(row['id'], play, row['time_added']))

        for row in resume_rows:
            play = plays[row['play_id']]
            play.resumes.append(Resume(row['id'], play, row['time_added']))

    def get_user_data(self, user, from_time=0, to_time=9999999999999):
        db_rows = self.db_provider.get_user_data(user.id, from_time, to_time)

        tracks = {}
        albums = {}
        artists = {}
        plays = {}

        for row in db_rows:
            if row['artist_id'] in artists:
                artist = artists[row['artist_id']]
            else:
                artist = Artist(row['artist_id'], row['artist_name'], [])
                artists[artist.id] = artist

            if row['album_id'] in albums:
                album = albums[row['album_id']]
            else:
                album = Album(row['album_id'], row['album_name'], [], [artist],
                              [], None, None, None)
                albums[album.id] = album
                artist.albums.append(album)

            if row['track_id'] in tracks:
                track = tracks[row['track_id']]
            else:
                track = Track(row['track_id'], row['track_name'], album, [artist],
                              None, None, None, None, None)
                album.tracks.append(track)
                tracks[track.id] = track

            if not row['play_id'] in plays:
                play = Play(row['play_id'], row['play_time_started'],
                            row['play_time_ended'], [], [], [],
                            user, track, None, None)
                plays[play.id] = play

        self._attach_album_images(albums)
        self._attach_pauses_and_resumes(
            plays,
            self.db_provider.get_pauses_for_user(user.id, from_time, to_time),
            self.db_provider.get_resumes_for_user(user.id, from_time, to_time))

        return artists, albums, tracks, plays

    def get_all_users_data(self, from_time=0, to_time=9999999999999):
        db_rows = self.db_provider.get_all_users_data(from_time, to_time)

        tracks = {}
        albums = {}
        artists = {}
        plays = {}
        users = {}

        for row in db_rows:
            if row['user_id'] in users:
                user = users[row['user_id']]
            else:
                user = User(row['user_id'], row['user_username'], None, None,
                            row['user_time_added'], plays=[])
                user.settings.append_all([setting for setting in
                                          self.get_user_settings(user).values()])
                users[user.id] = user

            if row['artist_id'] in artists:
                artist = artists[row['artist_id']]
            else:
                artist = Artist(row['artist_id'], row['artist_name'], [])
                artists[artist.id] = artist

            if row['album_id'] in albums:
                album = albums[row['album_id']]
            else:
                album = Album(row['album_id'], row['album_name'], [], [artist], [],
                              None, None, None)
                albums[album.id] = album
                artist.albums.append(album)

            if row['track_id'] in tracks:
                track = tracks[row['track_id']]
            else:
                track = Track(row['track_id'], row['track_name'], album, [artist],
                              None, None, None, None, None)
                album.tracks.append(track)
                tracks[track.id] = track

            if not row['play_id'] in plays:
                play = Play(row['play_id'], row['play_time_started'],
                            row['play_time_ended'], [], [], [],
                            user, track, None, None)
                plays[play.id] = play
                user.plays.append(play)
            else:
                play = plays[row['play_id']]

        self._attach_album_images(albums)
        self._attach_pauses_and_resumes(
            plays,
            self.db_provider.get_pauses_in_range(from_time, to_time),
            self.db_provider.get_resumes_in_range(from_time, to_time))

        return users, artists, albums, tracks, plays

    def add_album(self, album):
        self.db_provider.add_album(album.id, album.name, album.type, album.release_date,
                                   album.release_date_precision)
        for artist in album.artists:
            if not self.db_provider.get_artist(artist.id):
                self.db_provider.add_artist(artist.id, artist.name)
            self.db_provider.add_album_artist(generate_id(), album.id, artist.id)
        for image in album.images:
            self.db_provider.add_album_image(image.id, image.url, album.id, image.width,
                                             image.height)

    def add_track(self, track):
        if not self.db_provider.get_album(track.album.id):
            self.add_album(track.album)
        self.db_provider.add_track(track.id, track.name, track.duration_ms,
                                   track.popularity, track.preview_url,
                                   track.track_number, track.explicit, track.album.id)
        for artist in track.artists:
            if not self.db_provider.get_artist(artist.id):
                self.db_provider.add_artist(artist.id, artist.name)
            self.db_provider.add_track_artist(generate_id(), track.id, artist.id)
        
    # NOTE: doesnt handle adding resumes and pauses from Play object
    def add_play(self, play):
        if not self.db_provider.get_track(play.track.id):
            self.add_track(play.track)
        if not self.db_provider.get_album(play.track.album.id):
            self.add_album(play.track.album)
        if play.context:
            if not self.db_provider.get_context(play.context.uri):
                self.db_provider.add_context(play.context.uri, play.context.type)
        if not self.db_provider.get_device(play.device.id):
            self.db_provider.add_device(play.device.id, play.device.name,
                                        play.device.type)
        self.db_provider.add_play(play.id, play.time_started, play.time_ended,
                                  play.volume_percent, play.user.id, play.track.id,
                                  play.device.id,
                                  play.context.uri if play.context else None)
        self.commit()

    def get_track(self, track_id):
        row = self.db_provider.get_track(track_id)
        if not row:
            return None
        return Track(row['id'], row['track_name'], None, [], row['duration_ms'],
                     row['popularity'], row['preview_url'], row['track_number'],
                     row['explicit'])

    def get_last_user_play(self, user):
        row = self.db_provider.get_last_user_play(user.id)
        if row:
            track = self.get_track(row['track_id'])
            return Play(row['id'], row['time_added'], row['time_ended'], None, None, None,
                        user, track, None, row['volume_percent'])
        return None

    def update_play_time_ended(self, play):
        self.db_provider.update_play_time_ended(play.id, play.time_ended)
        self.commit()

    def add_pause(self, pause):
        self.db_provider.add_pause(pause.id, pause.time_added, pause.play.id)
        self.commit()

    def add_resume(self, resume):
        self.db_provider.add_resume(resume.id, resume.time_added, resume.play.id)
        self.commit()

    def add_seek(self, seek):
        self.db_provider.add_seek(seek.id, seek.time_added, seek.position, seek.play.id)
        self.commit()

    def user_has_plays(self, user):
        return self.db_provider.user_has_plays(user.id)

    def get_user_settings(self, user):
        user_setting_rows = self.db_provider.get_user_settings(user.id)
        setting_rows = self.db_provider.get_settings()
        user_settings = {}
        for setting_row in setting_rows:
            user_setting_row = None
            for tmp_user_setting_row in user_setting_rows:
                if tmp_user_setting_row['setting_id'] == setting_row['id']:
                    user_setting_row = tmp_user_setting_row
            setting_value = setting_row['default_value']
            if user_setting_row:
                setting_value = user_setting_row['setting_value']
            if setting_row['value_type'] == 'bool':
                setting_value = str_to_bool(setting_value)
            setting = Setting(setting_row['id'], setting_row['setting_name'],
                              setting_row['description'], setting_value,
                              setting_row['value_type'])
            user_settings[setting_row['id']] = setting
        return user_settings

    def update_user_settings(self, user, settings):
        for setting_id in settings:
            setting = settings[setting_id]
            value = setting.value
            if setting.value_type == 'bool':
                value = str(value)
            if self.db_provider.get_user_setting(user.id, setting.id):
                self.db_provider.update_user_setting(setting.id, user.id, value)
            else:
                self.db_provider.add_user_setting(setting.id, user.id, value)
        self.commit()

    def get_user_track_plays(self, user, track_id, from_time=0, to_time=9999999999999):
        rows = self.db_provider.get_user_track_plays(user.id, track_id, from_time, to_time)

        # gotta use map for efficient access of a play using its id
        plays = {}

        for row in rows:
            if row['play_id'] not in plays:
                play = Play(row['play_id'], row['play_time_started'], row['play_time_ended'], [], [], None,
                            user, None, None, None)
                plays[play.id] = play

        self._attach_pauses_and_resumes(
            plays,
            self.db_provider.get_pauses_for_track(track_id, from_time, to_time),
            self.db_provider.get_resumes_for_track(track_id, from_time, to_time))

        return plays.values()

    def get_user_first_play(self, user):
        row = self.db_provider.get_user_first_play(user.id)
        return Play(row['id'], row['time_started'], row['time_ended'], [], [], None,
                    user, None, None, None)

    def get_user_by_credentials(self, username, password):
        user = self.get_user_by_username(username)
        if user and check_password_hash(user.password, password):
            return user
        return None

    def create_api_refresh_token(self, user):
        token = APIRefreshToken(generate_id(), user, current_time())
        self.db_provider.add_api_refresh_token(token.id, token.user.id, token.time_created)
        return token

    def create_api_access_token(self, refresh_token):
        token = APIAccessToken(generate_id(), refresh_token, current_time())
        self.db_provider.add_api_access_token(token.id, token.refresh_token.id, token.time_created)
        return token

    def get_api_refresh_token(self, token_id):
        row = self.db_provider.get_api_refresh_token(token_id)
        user = User(row['user_id'], None, None, None, None)
        refresh_token = APIRefreshToken(row['id'], user, row['time_added'])
        return refresh_token

    def get_api_access_token(self, token_id):
        row = self.db_provider.get_api_access_token(token_id)
        user = User(row['user_id'], None, None, None, None)
        refresh_token = APIRefreshToken(row['refresh_token_id'], user,
                                        row['refresh_token_time_added'])
        access_token = APIAccessToken(row['access_token_id'], refresh_token,
                                      row['access_token_time_added'])
        return access_token

    def get_top_artists(self, num_of_artists_to_return, from_time=0, to_time=9999999999999):
        rows = self.db_provider.get_artists_and_plays(from_time, to_time)

        artists = {}
        plays = {}

        for row in rows:
            if row['artist_id'] in artists:
                artist = artists[row['artist_id']]
            else:
                artist = Artist(row['artist_id'], row['artist_name'], [])
                artists[artist.id] = artist
                artist.plays = []

            if row['play_id'] not in plays:
                play = Play(row['play_id'], row['play_time_started'], row['play_time_ended'], [], [],
                            None, None, None, None, None)
                plays[play.id] = play
                artist.plays.append(play)

        self._attach_pauses_and_resumes(
            plays,
            self.db_provider.get_pauses_in_range(from_time, to_time),
            self.db_provider.get_resumes_in_range(from_time, to_time))

        for artist in artists.values():
            for play in artist.plays:
                listened_ms = play.listened_ms(from_time, to_time)
                if hasattr(artist, 'listened_ms'):
                    artist.listened_ms += listened_ms
                else:
                    artist.listened_ms = listened_ms

        def compare(artist1, artist2):
            if not hasattr(artist1, 'listened_ms'):
                return False
            if not hasattr(artist2, 'listened_ms'):
                return True
            return artist1.listened_ms > artist2.listened_ms
        top_artists = get_largest_elements(list(artists.values()), num_of_artists_to_return, compare)

        return top_artists

    def get_top_users(self, from_time, to_time):
        users, artists, albums, tracks, plays =\
            self.get_all_users_data(from_time, to_time)

        users_to_sort = []
        for user in users.values():
            if user.settings.get_by_name('show_on_top_users').value:
                if user.plays:
                    users_to_sort.append(user)

        for user in users_to_sort:
            for play in user.plays:
                listened_ms = play.listened_ms(from_time=from_time, to_time=to_time)
                if hasattr(play.track, 'listened_ms'):
                    if user.id in play.track.listened_ms:
                        play.track.listened_ms[user.id] += listened_ms
                    else:
                        play.track.listened_ms[user.id] = listened_ms
                else:
                    play.track.listened_ms = {user.id: listened_ms}
                if not hasattr(user, 'top_track') or\
                play.track.listened_ms[user.id] > user.top_track.listened_ms[user.id]:
                    user.top_track = play.track
                if not hasattr(user, 'listened_ms'):
                    user.listened_ms = listened_ms
                else:
                    user.listened_ms += listened_ms

        def compare(user1, user2):
            if not hasattr(user1, 'listened_ms'):
                return False
            if not hasattr(user2, 'listened_ms'):
                return True
            return user1.listened_ms > user2.listened_ms
        top_users = get_largest_elements(users_to_sort, 10, compare)

        return top_users

    def get_top_tracks(self, num_of_tracks_to_return, from_time, to_time):
        users, artists, albums, tracks, plays =\
            self.get_all_users_data(from_time, to_time)

        for play in plays.values():
            if hasattr(play.track, 'listened_ms'):
                play.track.listened_ms += play.listened_ms(from_time=from_time, to_time=to_time)
            else:
                play.track.listened_ms = play.listened_ms(from_time=from_time, to_time=to_time)

        def compare(track1, track2):
            if not hasattr(track1, 'listened_ms'):
                return False
            if not hasattr(track2, 'listened_ms'):
                return True
            return track1.listened_ms > track2.listened_ms

        return get_largest_elements(list(tracks.values()), num_of_tracks_to_return, compare)

    def get_total_plays(self):
        return self.db_provider.get_count_of_table_rows('plays')['COUNT(*)']

    def get_last_play(self):
        row = self.db_provider.get_last_play()
        artist = Artist(None, row['artist_name'], [])
        track = Track(None, row['track_name'], None, [artist], None,
                      None, None, None, None)
        user = User(None, row['username'], None, None, None)
        play = Play(row['id'], row['time_started'], row['time_ended'], [], [],
                    None, user, track, None, None)
        return play
