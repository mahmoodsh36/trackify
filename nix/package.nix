# three wrapper scripts (web/tracker/cache) around the app source, configured
# through the TRACKIFY_* env vars config.py reads.
#
# the app does a bare `import config`, so the source root has to be the cwd and
# on sys.path.

{ lib
, src
, python3
, writeShellScriptBin
, symlinkJoin
}:

let
  pythonEnv = python3.withPackages (ps: with ps; [
    flask
    requests
    redis
    gunicorn
    mysql-connector
  ]);

  # an existing $PYTHONPATH stays in front so a caller can shadow config.py.
  mkRunner = name: command: writeShellScriptBin name ''
    export PYTHONPATH="''${PYTHONPATH:+$PYTHONPATH:}${src}"
    cd ${src}
    ${command}
  '';

  runners = [
    (mkRunner "trackify-web" ''
      exec ${pythonEnv}/bin/gunicorn \
        --workers "''${TRACKIFY_WORKERS:-2}" \
        --bind "''${TRACKIFY_BIND:-127.0.0.1:8091}" \
        trackify.webapp:web_application "$@"
    '')
    (mkRunner "trackify-tracker" ''
      exec ${pythonEnv}/bin/python -m trackify.spotify.tracker "$@"
    '')
    (mkRunner "trackify-cache" ''
      exec ${pythonEnv}/bin/python -m trackify.cache.daemon "$@"
    '')
  ];
in
symlinkJoin {
  name = "trackify";
  paths = runners;

  postBuild = ''
    mkdir -p $out/share/trackify
    cp ${src}/trackify/db/schema.sql $out/share/trackify/schema.sql
  '';

  passthru = { inherit pythonEnv src; };

  meta = {
    description = "track and visualize your spotify activity";
    homepage = "https://github.com/mahmoodsheikh36/trackify";
    mainProgram = "trackify-web";
    platforms = lib.platforms.unix;
  };
}
