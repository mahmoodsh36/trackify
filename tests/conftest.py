# the app does a bare `import config` and expects the repo root on sys.path,
# regardless of where pytest was invoked from
import os
import shutil
import socket
import subprocess
import sys
import time

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

SCHEMA = os.path.join(REPO_ROOT, 'trackify', 'db', 'schema.sql')
DB_NAME = 'trackify_test'
DB_USER = 'trackify'
DB_PASS = 'trackify'


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


DATADIR = os.path.join(os.getcwd(), '.data-test', 'mysql')


@pytest.fixture(scope='session')
def mariadb():
    """a throwaway mariadbd for the whole test session, wiped afterwards"""
    if not shutil.which('mariadbd'):
        pytest.skip('mariadb is not on PATH, run tests via nix (nix run .#tests)')

    shutil.rmtree(DATADIR, ignore_errors=True)
    os.makedirs(DATADIR)
    datadir = DATADIR
    sock = os.path.join(datadir, 'm.sock')
    port = free_port()

    subprocess.run(
        ['mariadb-install-db', f'--datadir={datadir}',
         '--auth-root-authentication-method=normal', '--skip-test-db'],
        check=True, capture_output=True)
    server = subprocess.Popen(
        ['mariadbd', f'--datadir={datadir}', f'--socket={sock}',
         '--bind-address=127.0.0.1', f'--port={port}', '--skip-name-resolve'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            ping = subprocess.run(
                ['mariadb-admin', f'--socket={sock}', '-u', 'root', 'ping'],
                capture_output=True)
            if ping.returncode == 0:
                break
            if server.poll() is not None:
                raise RuntimeError('mariadbd exited during startup')
            time.sleep(0.1)
        else:
            raise RuntimeError('mariadbd did not become ready')

        subprocess.run(
            ['mariadb', f'--socket={sock}', '-u', 'root'], check=True,
            capture_output=True, text=True, input=f"""
            CREATE USER '{DB_USER}'@'127.0.0.1' IDENTIFIED BY '{DB_PASS}';
            GRANT ALL PRIVILEGES ON *.* TO '{DB_USER}'@'127.0.0.1';
            FLUSH PRIVILEGES;
            """)
        yield {'socket': sock, 'port': port}
    finally:
        server.terminate()
        server.wait()


@pytest.fixture
def db(mariadb):
    """a DbDataProvider backed by a fresh database with the real schema loaded"""
    from trackify.db.data import DbDataProvider

    subprocess.run(
        ['mariadb', f"--socket={mariadb['socket']}", '-u', 'root'], check=True,
        capture_output=True, text=True,
        input=f'DROP DATABASE IF EXISTS {DB_NAME};'
              f'CREATE DATABASE {DB_NAME} CHARACTER SET utf8mb4;')
    with open(SCHEMA) as schema:
        subprocess.run(
            ['mariadb', f"--socket={mariadb['socket']}", '-u', 'root', DB_NAME],
            check=True, capture_output=True, stdin=schema)

    provider = DbDataProvider(user=DB_USER, passwd=DB_PASS, database=DB_NAME,
                              host='127.0.0.1', port=mariadb['port'])
    yield provider
    provider.close()
