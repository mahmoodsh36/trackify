# local dev stack under a process-compose tui. state lives in ./.data
#
# spotify/discogs credentials are not set here: they pass through from the
# shell (TRACKIFY_SPOTIFY_CLIENT_ID etc), see config.py.

{ lib
, formats
, writeShellScriptBin
, symlinkJoin
, process-compose
, mariadb
, redis
, coreutils
, trackify
}:

let
  dbName = "trackify";
  dbUser = "trackify";
  dbPass = "trackify";
  webPort = 8091;
  dbPort = 3306;
  redisPort = 6379; # hardcoded in trackify/cache/data.py

  dataDir = "$PWD/.data";
  socket = "\${TMPDIR:-/tmp}/trackify-mysql.sock";

  env = import ./env.nix { inherit lib; } {
    database = { name = dbName; user = dbUser; password = dbPass; host = "127.0.0.1"; };
    port = webPort;
    workers = 2;
    redirectUri = "http://localhost:${toString webPort}/spotify/callback";
    secretKey = "dev";
    spotify = { clientId = null; clientSecret = null; scope = null; };
    discogs = { apiKey = null; apiSecret = null; };
  };

  mysql = "${mariadb}/bin/mariadb --socket=${socket} -u root";

  # process-compose mangles backslash line continuations, so every command
  # below stays on one line
  args = lib.concatStringsSep " ";

  cmd = {
    startMysql = ''
      mkdir -p ${dataDir}
      if [ ! -d ${dataDir}/mysql/mysql ]; then
        ${args [ "${mariadb}/bin/mariadb-install-db" "--datadir=${dataDir}/mysql" "--auth-root-authentication-method=normal" "--skip-test-db" ]}
      fi
      exec ${args [ "${mariadb}/bin/mariadbd" "--datadir=${dataDir}/mysql" "--socket=${socket}" "--bind-address=127.0.0.1" "--port=${toString dbPort}" ]}
    '';

    mysqlReady = "${mariadb}/bin/mariadb-admin --socket=${socket} -u root ping";

    startRedis = ''
      mkdir -p ${dataDir}/redis
      exec ${args [ "${redis}/bin/redis-server" "--port ${toString redisPort}" "--bind 127.0.0.1" "--dir ${dataDir}/redis" ]}
    '';

    redisReady = "${redis}/bin/redis-cli -p ${toString redisPort} ping";

    initDb = ''
      ${mysql} <<'SQL'
      CREATE DATABASE IF NOT EXISTS ${dbName} CHARACTER SET utf8mb4;
      CREATE USER IF NOT EXISTS '${dbUser}'@'localhost' IDENTIFIED BY '${dbPass}';
      CREATE USER IF NOT EXISTS '${dbUser}'@'127.0.0.1' IDENTIFIED BY '${dbPass}';
      GRANT ALL PRIVILEGES ON ${dbName}.* TO '${dbUser}'@'localhost';
      GRANT ALL PRIVILEGES ON ${dbName}.* TO '${dbUser}'@'127.0.0.1';
      FLUSH PRIVILEGES;
      SQL
      ${mysql} ${dbName} < ${trackify}/share/trackify/schema.sql
    '';
  };

  apps = {
    web = "trackify-web";
    tracker = "trackify-tracker";
    cache = "trackify-cache";
  };

  yaml = formats.yaml { };
  processComposeConfig = yaml.generate "process-compose.yaml" {
    version = "0.5";
    environment = lib.mapAttrsToList (k: v: "${k}=${v}") env;
    processes = {
      mysql = {
        command = cmd.startMysql;
        readiness_probe = {
          exec.command = cmd.mysqlReady;
          initial_delay_seconds = 2;
          period_seconds = 2;
        };
      };
      redis = {
        command = cmd.startRedis;
        readiness_probe = {
          exec.command = cmd.redisReady;
          initial_delay_seconds = 1;
          period_seconds = 2;
        };
      };
      init-db = {
        command = cmd.initDb;
        depends_on.mysql.condition = "process_healthy";
      };
    } // lib.mapAttrs (_: bin: {
      command = "exec ${trackify}/bin/${bin}";
      depends_on = {
        init-db.condition = "process_completed_successfully";
        redis.condition = "process_healthy";
      };
      availability = { restart = "on_failure"; max_restarts = 10; backoff_seconds = 5; };
    }) apps;
  };

  envExports = lib.concatStringsSep "\n"
    (lib.mapAttrsToList (k: v: "export ${k}='${v}'") env);

  mkScript = name: body: writeShellScriptBin "trackify-dev-${name}" ''
    export PATH="${lib.makeBinPath [ coreutils mariadb redis ]}:$PATH"
    ${envExports}
    ${body}
  '';

  bodies = {
    # -p: process-compose's own api port, 8080 by default which tends to be taken
    stack = ''
      exec ${args [
        "${process-compose}/bin/process-compose"
        "-f ${processComposeConfig}"
        "-p \${TRACKIFY_PC_PORT:-8321}"
        "up --keep-project"
        "\"$@\""
      ]}
    '';

    db = cmd.startMysql;
    redis-server = cmd.startRedis;

    init-db = ''
      if ! ${cmd.mysqlReady} >/dev/null 2>&1; then
        echo "mariadb is not running, start it with: trackify-dev-db"
        exit 1
      fi
      ${cmd.initDb}
      echo "database ${dbName} initialized"
    '';

    mysql-shell = ''exec ${mysql} ${dbName} "$@"'';

    clean = ''
      rm -rf ${dataDir}
      echo "removed .data"
    '';
  } // lib.mapAttrs (_: bin: ''exec ${trackify}/bin/${bin} "$@"'') apps;
in
lib.mapAttrs mkScript bodies // {
  inherit env;
}
