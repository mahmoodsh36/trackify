# three long-running units:
# - trackify-web     : gunicorn wsgi app, reverse-proxied by caddy
# - trackify-tracker : polls the spotify api and records plays
# - trackify-cache   : warms the redis cache the /top_users page reads from
# backed by a local mariadb + redis.

{ src }:

{ config, pkgs, lib, ... }:

let
  cfg = config.services.trackify;

  env = import ./env.nix { inherit lib; } cfg;

  commonServiceConfig = {
    Type = "simple";
    DynamicUser = true;
    Restart = "always";
    RestartSec = "5s";
  };

  redisUnit = "redis-${cfg.redis.serverName}.service";
  dbInitUnit = "trackify-db-init.service";

  mkUnit = { description, exec, needsRedis ? false }: {
    inherit description;
    after = [ "network.target" ]
      ++ lib.optional cfg.database.provision dbInitUnit
      ++ lib.optional (needsRedis && cfg.redis.provision) redisUnit;
    requires = lib.optional cfg.database.provision dbInitUnit
      ++ lib.optional (needsRedis && cfg.redis.provision) redisUnit;
    wantedBy = [ "multi-user.target" ];
    environment = env;
    serviceConfig = commonServiceConfig // {
      ExecStart = "${cfg.package}/bin/${exec}";
    };
  };
in
{
  options.services.trackify = {
    enable = lib.mkEnableOption "trackify spotify tracker + web app";

    src = lib.mkOption {
      type = lib.types.path;
      default = src;
      defaultText = lib.literalMD "the source of this module";
      description = "trackify source tree.";
    };

    package = lib.mkOption {
      type = lib.types.package;
      default = pkgs.callPackage ./package.nix { src = cfg.src; };
      defaultText = lib.literalMD "built from `src`";
      description = "package providing trackify-web/tracker/cache.";
    };

    domain = lib.mkOption {
      type = lib.types.str;
      example = "trackify.example.com";
      description = "public domain the app is served on. used for the caddy vhost and the default spotify redirect uri.";
    };

    port = lib.mkOption {
      type = lib.types.port;
      default = 8091;
      description = "gunicorn bind port, loopback only, the reverse proxy talks to it.";
    };

    workers = lib.mkOption {
      type = lib.types.int;
      default = 2;
      description = "gunicorn worker processes.";
    };

    redirectUri = lib.mkOption {
      type = lib.types.str;
      default = "https://${cfg.domain}/spotify/callback";
      defaultText = lib.literalExpression ''"https://''${cfg.domain}/spotify/callback"'';
      description = "spotify oauth redirect uri. must match the one registered in the spotify app.";
    };

    # these land in the systemd unit, ie world-readable in the nix store
    secretKey = lib.mkOption {
      type = lib.types.str;
      default = "";
      description = "flask secret key.";
    };

    spotify = {
      clientId = lib.mkOption {
        type = lib.types.str;
        default = "";
        description = "spotify api client id.";
      };
      clientSecret = lib.mkOption {
        type = lib.types.str;
        default = "";
        description = "spotify api client secret.";
      };
      scope = lib.mkOption {
        type = lib.types.str;
        default = "user-library-read playlist-read-private user-read-playback-state user-read-currently-playing user-modify-playback-state";
        description = "spotify oauth scopes requested from users.";
      };
    };

    discogs = {
      apiKey = lib.mkOption {
        type = lib.types.str;
        default = "";
        description = "discogs api key.";
      };
      apiSecret = lib.mkOption {
        type = lib.types.str;
        default = "";
        description = "discogs api secret.";
      };
    };

    database = {
      name = lib.mkOption {
        type = lib.types.str;
        default = "trackify";
        description = "mysql database name.";
      };
      user = lib.mkOption {
        type = lib.types.str;
        default = "trackify";
        description = "mysql user.";
      };
      password = lib.mkOption {
        type = lib.types.str;
        default = "trackify";
        description = ''
          mysql password. with the default local setup mariadb binds to
          127.0.0.1 only, so this guards nothing beyond the machine itself.
        '';
      };
      host = lib.mkOption {
        type = lib.types.str;
        default = "127.0.0.1";
        description = "mysql host the app connects to.";
      };
      provision = lib.mkOption {
        type = lib.types.bool;
        default = true;
        description = ''
          run a local mariadb, and create the database/user and load the schema
          on boot (idempotent). turn off to point at an existing db.
        '';
      };
    };

    redis = {
      enable = lib.mkOption {
        type = lib.types.bool;
        default = true;
        description = ''
          run the cache-warming daemon. the /top_users page and the discogs
          lookups need it; the rest of the app works without.
        '';
      };
      provision = lib.mkOption {
        type = lib.types.bool;
        default = true;
        description = "run a local redis server for the cache.";
      };
      serverName = lib.mkOption {
        type = lib.types.str;
        default = "trackify";
        description = "name of the services.redis.servers entry to create/depend on.";
      };
      port = lib.mkOption {
        type = lib.types.port;
        default = 6379;
        description = "redis port. the app hardcodes localhost:6379.";
      };
    };

    caddy.enable = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = "add a caddy vhost for `domain` reverse-proxying to gunicorn.";
    };
  };

  config = lib.mkIf cfg.enable (lib.mkMerge [
    {
      systemd.services.trackify-web = mkUnit {
        description = "trackify web app (gunicorn)";
        exec = "trackify-web";
        needsRedis = true;
      };

      systemd.services.trackify-tracker = mkUnit {
        description = "trackify spotify tracker daemon";
        exec = "trackify-tracker";
      };
    }

    (lib.mkIf cfg.redis.enable {
      systemd.services.trackify-cache = mkUnit {
        description = "trackify cache-warming daemon";
        exec = "trackify-cache";
        needsRedis = true;
      };
    })

    (lib.mkIf cfg.database.provision {
      services.mysql = {
        enable = true;
        package = pkgs.mariadb;
        settings.mysqld.bind-address = "127.0.0.1";
      };

      systemd.services.trackify-db-init = {
        description = "initialize the trackify database";
        after = [ "mysql.service" ];
        requires = [ "mysql.service" ];
        wantedBy = [ "multi-user.target" ];
        serviceConfig = {
          Type = "oneshot";
          RemainAfterExit = true;
        };
        # runs as root, can auth to mariadb's root@localhost over the unix socket
        script = ''
          ${pkgs.mariadb}/bin/mysql <<'SQL'
          CREATE DATABASE IF NOT EXISTS ${cfg.database.name} CHARACTER SET utf8mb4;
          CREATE USER IF NOT EXISTS '${cfg.database.user}'@'localhost' IDENTIFIED BY '${cfg.database.password}';
          CREATE USER IF NOT EXISTS '${cfg.database.user}'@'127.0.0.1' IDENTIFIED BY '${cfg.database.password}';
          GRANT ALL PRIVILEGES ON ${cfg.database.name}.* TO '${cfg.database.user}'@'localhost';
          GRANT ALL PRIVILEGES ON ${cfg.database.name}.* TO '${cfg.database.user}'@'127.0.0.1';
          FLUSH PRIVILEGES;
          SQL
          ${pkgs.mariadb}/bin/mysql ${cfg.database.name} < ${cfg.package}/share/trackify/schema.sql
        '';
      };
    })

    (lib.mkIf (cfg.redis.enable && cfg.redis.provision) {
      services.redis.servers.${cfg.redis.serverName} = {
        enable = true;
        bind = "127.0.0.1";
        port = cfg.redis.port;
      };
    })

    (lib.mkIf cfg.caddy.enable {
      services.caddy.virtualHosts."${cfg.domain}" = {
        extraConfig = ''
          reverse_proxy 127.0.0.1:${toString cfg.port}
        '';
      };
    })
  ]);
}
