from werkzeug.security import generate_password_hash

from trackify.db.classes import User
from trackify.utils import current_time, generate_id


def mk_user(username='alice', password='hunter2'):
    return User(generate_id(), username, generate_password_hash(password),
                f'{username}@example.com', current_time())


def test_add_and_get_user_by_username(db):
    user = mk_user()
    db.add_user(user)
    fetched = db.get_user_by_username('alice')
    assert fetched.id == user.id
    assert fetched.username == user.username
    assert fetched.password == user.password
    assert fetched.email == user.email
    assert fetched.time_added == user.time_added


def test_get_user_by_id(db):
    user = mk_user()
    db.add_user(user)
    assert db.get_user(user.id).username == 'alice'


def test_get_missing_user(db):
    assert db.get_user_by_username('nobody') is None
    assert db.get_user(generate_id()) is None


def test_get_user_by_credentials(db):
    user = mk_user(password='hunter2')
    db.add_user(user)
    assert db.get_user_by_credentials('alice', 'hunter2').id == user.id
    assert db.get_user_by_credentials('alice', 'wrong') is None
    assert db.get_user_by_credentials('nobody', 'hunter2') is None


def test_get_users(db):
    db.add_user(mk_user('alice'))
    db.add_user(mk_user('bob'))
    assert {u.username for u in db.get_users()} == {'alice', 'bob'}
