from trackify.db.classes import (
    APIAccessToken,
    Album,
    Image,
    Pause,
    Play,
    Resume,
    SpotifyAccessToken,
    Track,
)
from trackify.utils import current_time


def mk_image(width):
    return Image(f'img{width}', f'http://example.com/{width}', width, width)


def mk_album(widths):
    return Album('album1', 'album', [], [], [mk_image(w) for w in widths],
                 'album', '2020-01-01', 'day')


def mk_play(time_started, time_ended, pauses=None, resumes=None):
    track = Track('track1', 'track', None, [], 200000, 50, None, 1, False)
    return Play('play1', time_started, time_ended, pauses or [], resumes or [],
                [], None, track, None, 100)


class TestAlbumImages:
    def test_size_selection(self):
        album = mk_album([300, 64, 640])
        assert album.smallest_image().width == 64
        assert album.biggest_image().width == 640
        assert mk_album([64, 300, 640]).mid_sized_image().width == 300

    def test_add_image_keeps_ascending_order(self):
        album = mk_album([64, 640])
        album.add_image(mk_image(300))
        assert [image.width for image in album.images] == [64, 300, 640]


class TestPlayListenedMs:
    def test_full_play(self):
        play = mk_play(1000, 61000)
        assert play.listened_ms() == 60000

    def test_unfinished_play_counts_as_zero(self):
        play = mk_play(1000, -1)
        assert play.listened_ms() == 0

    def test_pause_and_resume_subtracted(self):
        play = mk_play(0, 60000)
        play.pauses.append(Pause('p1', None, 10000))
        play.resumes.append(Resume('r1', None, 20000))
        assert play.listened_ms() == 50000

    def test_trailing_pause_subtracted(self):
        play = mk_play(0, 60000, pauses=[Pause('p1', None, 40000)])
        assert play.listened_ms() == 40000

    def test_window_clamped_to_play_bounds(self):
        play = mk_play(10000, 20000)
        assert play.listened_ms(from_time=0, to_time=100000) == 10000

    def test_window_outside_play_counts_as_zero(self):
        play = mk_play(10000, 20000)
        assert play.listened_ms(from_time=30000, to_time=40000) == 0
        assert play.listened_ms(from_time=0, to_time=5000) == 0

    def test_partial_window(self):
        play = mk_play(0, 60000)
        assert play.listened_ms(from_time=30000, to_time=45000) == 15000


class TestTokens:
    def test_spotify_access_token_expiry(self):
        assert not SpotifyAccessToken('t1', 'tok', None, current_time()).expired()
        old = current_time() - 3600 * 1000
        assert SpotifyAccessToken('t2', 'tok', None, old).expired()

    def test_api_access_token_expiry(self):
        fresh = APIAccessToken('t1', None, current_time())
        assert not fresh.expired()
        assert fresh.expiry_time() == fresh.time_created + 3600 * 1000
        old = APIAccessToken('t2', None, current_time() - 2 * 3600 * 1000)
        assert old.expired()
