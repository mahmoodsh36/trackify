CREATE TABLE IF NOT EXISTS users (
  id VARCHAR(36) NOT NULL PRIMARY KEY,
  username VARCHAR(30) NOT NULL,
  password VARCHAR(255) NOT NULL,
  email VARCHAR(255),
  time_added BIGINT NOT NULL
);

CREATE TABLE IF Not EXISTS settings (
  id INT NOT NULL PRIMARY KEY,
  description VARCHAR(100) NOT NULL,
  setting_name VARCHAR(40) NOT NULL,
  value_type VARCHAR(10) NOT NULL,
  default_value VARCHAR(10) NOT NULL
);

INSERT INTO settings (id, description, setting_name, value_type, default_value) VALUES
(1, 'show me on top users list', 'show_on_top_users', 'bool', 'True'),
(2, 'show my favorite track on the top users list', 'show_favorite_track_on_top_users',
 'bool', 'False');
-- (3, 'show my last played track on the top users list', 'show_last_played_on_top_users',
--  'bool', 'False');

CREATE TABLE IF NOT EXISTS user_settings (
  id INT PRIMARY KEY AUTO_INCREMENT,
  setting_value VARCHAR(10) NOT NULL,
  setting_id INT NOT NULL,
  user_id VARCHAR(36) NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users (id),
  FOREIGN KEY (setting_id) REFERENCES settings (id)
);

CREATE TABLE IF NOT EXISTS requests (
  id VARCHAR(36) PRIMARY KEY,
  time_added BIGINT NOT NULL,
  ip TEXT NOT NULL,
  url TEXT NOT NULL,
  headers TEXT NOT NULL,
  request_data TEXT,
  form TEXT,
  referrer TEXT,
  access_route TEXT,
  user_id VARCHAR(36),
  FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS spotify_auth_codes (
  id VARCHAR(36) PRIMARY KEY,
  time_added BIGINT NOT NULL,
  code TEXT NOT NULL,
  user_id VARCHAR(36) NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS spotify_access_tokens (
  id VARCHAR(36) PRIMARY KEY,
  time_added BIGINT NOT NULL,
  token VARCHAR(310) NOT NULL, -- access token length is 303, gotta be safe
  user_id VARCHAR(36) NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS spotify_refresh_tokens (
  id VARCHAR(36) PRIMARY KEY,
  time_added BIGINT NOT NULL,
  token VARCHAR(140) NOT NULL, -- refresh token length is 131 chars but gotta be safe
  user_id VARCHAR(36) NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS albums (
  id VARCHAR(25) PRIMARY KEY, -- album ids are 22 chars
  album_name TEXT NOT NULL,
  album_type VARCHAR(10) NOT NULL, -- think values for this are album/single, gotta be safe
  release_date VARCHAR(13), -- max length is 10
  release_date_precision VARCHAR(10) -- max length AFAIK is 4
);

CREATE TABLE IF NOT EXISTS album_images (
  id VARCHAR(36) PRIMARY KEY,
  height INT NOT NULL,
  width INT NOT NULL,
  url VARCHAR(70) NOT NULL, -- the url is actually 64 chars long but whatever
  album_id VARCHAR(25) NOT NULL,
  FOREIGN KEY (album_id) REFERENCES albums (id)
);

CREATE TABLE IF NOT EXISTS tracks (
  id VARCHAR(25) PRIMARY KEY, -- track ids are 22 chars
  track_name TEXT NOT NULL,
  duration_ms INT NOT NULL,
  popularity INT NOT NULL,
  preview_url TEXT,
  track_number INT NOT NULL,
  explicit BOOL NOT NULL,
  album_id VARCHAR(25) NOT NULL,
  FOREIGN KEY (album_id) REFERENCES albums (id)
);

CREATE TABLE IF NOT EXISTS artists (
  id VARCHAR(25) PRIMARY KEY, -- artist ids are 22 chars
  artist_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS album_artists (
  id VARCHAR(36) PRIMARY KEY,
  artist_id VARCHAR(25) NOT NULL,
  album_id VARCHAR(25) NOT NULL,
  FOREIGN KEY (artist_id) REFERENCES artists (id),
  FOREIGN KEY (album_id) REFERENCES albums (id)
);

CREATE TABLE IF NOT EXISTS track_artists (
  id VARCHAR(36) PRIMARY KEY,
  artist_id VARCHAR(25) NOT NULL,
  track_id VARCHAR(25) NOT NULL,
  FOREIGN KEY (artist_id) REFERENCES artists (id),
  FOREIGN KEY (track_id) REFERENCES tracks (id)
);

CREATE TABLE IF NOT EXISTS devices (
  id VARCHAR(45) PRIMARY KEY, -- devices ids are 40 chars long
  device_name TEXT NOT NULL,
  device_type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contexts (
  uri VARCHAR(100) PRIMARY KEY,
  context_type VARCHAR(10) NOT NULL -- i think possible values are album/playlist
);

CREATE TABLE IF NOT EXISTS plays (
  id VARCHAR(36) PRIMARY KEY,
  time_started BIGINT NOT NULL,
  time_ended BIGINT NOT NULL,
  user_id VARCHAR(36) NOT NULL,
  track_id VARCHAR(25) NOT NULL,
  device_id VARCHAR(45) NOT NULL,
  context_uri VARCHAR(100),
  volume_percent INT NOT NULL,
  FOREIGN KEY (track_id) REFERENCES tracks (id),
  FOREIGN KEY (user_id) REFERENCES users (id),
  FOREIGN KEY (context_uri) REFERENCES contexts (uri),
  FOREIGN KEY (device_id) REFERENCES devices (id)
);

CREATE TABLE IF NOT EXISTS pauses (
  id VARCHAR(36) PRIMARY KEY,
  time_added BIGINT NOT NULL,
  play_id VARCHAR(36) NOT NULL,
  FOREIGN KEY (play_id) REFERENCES plays (id)
);

CREATE TABLE IF NOT EXISTS resumes (
  id VARCHAR(36) PRIMARY KEY,
  time_added BIGINT NOT NULL,
  play_id VARCHAR(36) NOT NULL,
  FOREIGN KEY (play_id) REFERENCES plays (id)
);

CREATE TABLE IF NOT EXISTS seeks (
  id VARCHAR(36) PRIMARY KEY,
  time_added BIGINT NOT NULL,
  position INT NOT NULL,
  play_id VARCHAR(36) NOT NULL,
  FOREIGN KEY (play_id) REFERENCES plays (id)
);

CREATE TABLE IF NOT EXISTS api_refresh_tokens (
  id VARCHAR(36) PRIMARY KEY,
  time_added BIGINT NOT NULL,
  user_id VARCHAR(36) NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS api_access_tokens (
  id VARCHAR(36) PRIMARY KEY,
  time_added BIGINT NOT NULL,
  refresh_token_id VARCHAR(36) NOT NULL,
  FOREIGN KEY (refresh_token_id) REFERENCES api_refresh_tokens (id)
);

CREATE INDEX time_started_index ON plays(time_started);
CREATE INDEX time_ended_index ON plays(time_ended);
