"""
benchmarks the app's real user-facing query paths - the DbDataProvider methods
called directly by trackify/webapp/blueprints/{spotify,api}.py, against whatever
data is currently in the database pointed to by the TRACKIFY_DB_* env vars.

run via: trackify-dev-benchmark (see nix/dev.nix)

scenarios (comma-separated via TRACKIFY_BENCH_SCENARIOS, default: all):
  history    get_user_data over the last 7 days (/api/history, /spotify/history default)
  my-data    get_user_data over the full range (/api/data default)
  top-users  get_all_users_data over the last 24h (/api/top_users default, also the
             query behind /api/top_artists and /api/top_tracks, uncached)

env:
  TRACKIFY_BENCH_USER_ID    user to query for history/my-data (default: af38a714-...)
  TRACKIFY_BENCH_SCENARIOS  comma-separated scenario names to run (default: all)
"""
import os
import time

from trackify.db.data import DbDataProvider
from trackify.utils import current_time

DEFAULT_USER_ID = 'af38a714-bcba-419e-804c-96d910d0e975'
DAY_MS = 24 * 3600 * 1000


def timed(label, fn):
    start = time.perf_counter()
    result = fn()
    elapsed = (time.perf_counter() - start) * 1000
    print(f'{label}: {elapsed:.1f} ms')
    return result


def bench_history(provider, user):
    artists, albums, tracks, plays = timed(
        'history (get_user_data, last 7d)',
        lambda: provider.get_user_data(user, current_time() - 7 * DAY_MS, current_time()))
    print(f'  {len(plays)} plays, {len(tracks)} tracks, {len(albums)} albums, {len(artists)} artists')


def bench_my_data(provider, user):
    artists, albums, tracks, plays = timed(
        'my-data (get_user_data, full range)',
        lambda: provider.get_user_data(user, 0, 9999999999999))
    print(f'  {len(plays)} plays, {len(tracks)} tracks, {len(albums)} albums, {len(artists)} artists')


def bench_top_users(provider, user):
    users, artists, albums, tracks, plays = timed(
        'top-users (get_all_users_data, last 24h, also backs top-artists/top-tracks)',
        lambda: provider.get_all_users_data(current_time() - DAY_MS, current_time()))
    print(f'  {len(users)} users, {len(plays)} plays, {len(tracks)} tracks, '
          f'{len(albums)} albums, {len(artists)} artists')


SCENARIOS = {
    'history': bench_history,
    'my-data': bench_my_data,
    'top-users': bench_top_users,
}


def main():
    user_id = os.environ.get('TRACKIFY_BENCH_USER_ID', DEFAULT_USER_ID)
    scenario_names = [
        name.strip()
        for name in os.environ.get('TRACKIFY_BENCH_SCENARIOS', ','.join(SCENARIOS)).split(',')
    ]

    provider = DbDataProvider()

    user = provider.get_user(user_id)
    if user is None:
        raise SystemExit(f'no such user: {user_id}')

    users = provider.db_provider.get_count_of_table_rows('users')['COUNT(*)']
    plays = provider.db_provider.get_count_of_table_rows('plays')['COUNT(*)']
    requests = provider.db_provider.get_count_of_table_rows('requests')['COUNT(*)']
    print(f'{users} users, {plays} plays, {requests} requests\n')

    for name in scenario_names:
        if name not in SCENARIOS:
            raise SystemExit(f'unknown scenario: {name} (choices: {", ".join(SCENARIOS)})')
        SCENARIOS[name](provider, user)
        print()


if __name__ == '__main__':
    main()
