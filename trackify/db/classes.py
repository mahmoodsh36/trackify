import json
from werkzeug.security import check_password_hash

from trackify.db.db import DbProvider
from trackify.utils import current_time, generate_id, str_to_bool, get_largest_elements

class Request:
    def __init__(self, flask_request, user):
        self.id = generate_id()
        if flask_request.environ.get('HTTP_X_FORWARDED_FOR') is None:
            self.ip = flask_request.environ['REMOTE_ADDR']
        else:
            self.ip = flask_request.environ.get('HTTP_X_FORWARDED_FOR')
        self.headers = json.dumps({k:v for k, v in flask_request.headers.items()})
        self.data = flask_request.data.decode('UTF-8')
        self.form = json.dumps(flask_request.form.to_dict(flat=False), indent=2)
        self.access_route = json.dumps(flask_request.access_route, indent=2)
        self.referrer = flask_request.referrer
        self.url = flask_request.url
        self.time_added = current_time()
        self.user = user

class User:
    def __init__(self, user_id, username, password, email, time_added,
                 access_token=None, refresh_token=None, plays=None):
        self.id = user_id
        self.username = username
        self.password = password
        self.email = email
        self.time_added = time_added
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.plays = plays
        self.settings = Settings()

class Artist:
    def __init__(self, artist_id, name, albums):
        self.id = artist_id
        if not self.id:
            self.id = generate_id(24)
        self.name = name
        self.albums = albums

class Track:
    def __init__(self, track_id, name, album, artists, duration_ms, popularity,
                 preview_url, track_number, explicit):
        self.id = track_id
        if not self.id:
            self.id = generate_id()
        self.name = name
        self.album = album
        self.artists = artists
        self.duration_ms = duration_ms
        self.popularity = popularity
        self.preview_url = preview_url
        self.track_number = track_number
        self.explicit = explicit

class Album:
    def __init__(self, album_id, name, tracks, artists, images, album_type,
                 release_date, release_date_precision):
        self.id = album_id
        if not self.id:
            self.id = generate_id(24)
        self.name = name
        self.type = album_type
        self.artists = artists
        self.tracks = tracks
        self.images = images
        self.release_date = release_date
        self.release_date_precision = release_date_precision

    def smallest_image(self):
        smallest = self.images[0]
        for idx, image in enumerate(self.images[1:]):
            if image.width < smallest.width:
                smallest = image
        return smallest

    def biggest_image(self):
        biggest = self.images[0]
        for idx, image in enumerate(self.images[1:]):
            if image.width > biggest.width:
                biggest = image
        return biggest

    def add_image(self, new_image):
        if not self.images:
            self.images.append(new_image)
        else:
            found_idx = False
            for idx, image in enumerate(self.images):
                if new_image.width < image.width:
                    self.images.insert(idx, new_image)
                    found_idx = True
                    break
            if not found_idx:
                self.images.append(new_image)

    def mid_sized_image(self):
        return self.images[len(self.images) // 2]

class SpotifyAuthCode:
    def __init__(self, code_id, code, user, time_added):
        self.id = code_id
        self.code = code
        self.user = user
        self.time_added = time_added

class SpotifyRefreshToken:
    def __init__(self, token_id, token, user, time_added):
        self.id = token_id
        self.token = token
        self.time_added = time_added
        self.user = user

class SpotifyAccessToken:
    def __init__(self, token_id, token, user, time_added):
        self.id = token_id
        self.token = token
        self.time_added = time_added
        self.user = user

    def expired(self):
        # expiry time is actually 3600 not 2500 but gotta be safe
        return self.time_added < current_time() - 2500 * 1000

def play_listened_ms(time_started, time_ended, pause_times, resume_times,
                     from_time=None, to_time=None):
    if time_ended == -1:
        return 0
    if abs(len(pause_times) - len(resume_times)) > 1:
        return 0
    if from_time is None:
        from_time = time_started
    elif from_time > time_ended:
        return 0
    if to_time is None:
        to_time = time_ended
    elif to_time < time_started:
        return 0
    if from_time < time_started:
        from_time = time_started
    if to_time > time_ended:
        to_time = time_ended
    milliseconds = to_time - from_time
    for i in range(len(resume_times)):
        time_paused = pause_times[i]
        time_resumed = resume_times[i]
        if time_paused > to_time:
            continue
        if time_resumed < from_time:
            continue
        if time_paused < from_time:
            time_paused = from_time
        if time_resumed > to_time:
            time_resumed = to_time
        milliseconds -= time_resumed - time_paused
    if len(pause_times) > len(resume_times):
        time_paused = pause_times[-1]
        if time_paused < to_time:
            if time_paused < from_time:
                time_paused = from_time
            milliseconds -= to_time - time_paused
    return milliseconds

class Play:
    def __init__(self, play_id, time_started, time_ended, pauses, resumes, seeks, user,
                 track, device, volume_percent, context=None, is_playing=False,
                 progress_ms=-1):
        self.id = play_id
        self.time_started = time_started
        self.time_ended = time_ended
        self.user = user
        self.track = track

class Play:
    def __init__(self, play_id, time_started, time_ended, pauses, resumes, seeks, user,
                 track, device, volume_percent, context=None, is_playing=False,
                 progress_ms=-1):
        self.id = play_id
        self.time_started = time_started
        self.time_ended = time_ended
        self.user = user
        self.track = track
        self.device = device
        self.context = context
        self.is_playing = is_playing
        self.progress_ms = progress_ms
        self.volume_percent = volume_percent
        self.pauses = pauses
        self.resumes = resumes
        self.seeks = seeks

    def has_same_track_as(self, other_play):
        return self.track.id == other_play.track.id

    def listened_ms(self, from_time=None, to_time=None):
        return play_listened_ms(
            self.time_started, self.time_ended,
            [pause.time_added for pause in self.pauses],
            [resume.time_added for resume in self.resumes],
            from_time, to_time)

class Pause:
    def __init__(self, pause_id, play, time_added):
        self.id = pause_id
        self.play = play
        self.time_added = time_added

class Resume:
    def __init__(self, resume_id, play, time_added):
        self.id = resume_id
        self.play = play
        self.time_added = time_added

class Seek:
    def __init__(self, seek_id, play, position, time_added):
        self.id = seek_id
        self.play = play
        self.position = position
        self.time_added = time_added

class Device:
    def __init__(self, device_id, name, device_type):
        self.id = device_id
        self.name = name
        self.type = device_type

class Context:
    def __init__(self, uri, context_type):
        self.uri = uri
        self.type = context_type

class Image:
    def __init__(self, image_id, url, width, height):
        self.id = image_id
        self.url = url
        self.width = width
        self.height = height

class Setting:
    def __init__(self, setting_id, name, description, value, value_type):
        self.id = setting_id
        self.name = name
        self.description = description
        self.value = value
        self.value_type = value_type

class Settings:
    def __init__(self, settings=[]):
        self.settings = []
        self.append_all(settings)

    def append(self, setting):
        self.settings.append(setting)

    def append_all(self, settings):
        for setting in settings:
            self.append(setting)

    def get_by_name(self, setting_name):
        for setting in self.settings:
            if setting.name == setting_name:
                return setting
        return None

class APIAccessToken:
    def __init__(self, token_id, refresh_token, time_created):
        self.id = token_id
        self.refresh_token = refresh_token
        self.time_created = time_created

    def expired(self):
        return self.time_created < current_time() - 3600 * 1000 # hardcoded for now

    def expiry_time(self):
        return self.time_created + 3600 * 1000 # hardcoded for now

class APIRefreshToken:
    def __init__(self, token_id, user, time_created):
        self.id = token_id
        self.user = user
        self.time_created = time_created
