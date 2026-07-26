{
  description = "trackify - track and visualize your spotify activity";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      inherit (nixpkgs) lib;

      # x86_64-darwin is deprecated in nixpkgs (26.11) and evaluating it errors
      systems = [ "x86_64-linux" "aarch64-linux" "aarch64-darwin" ];

      # per-system attrs, built once and reused by packages/apps/devShells
      each = lib.genAttrs systems (system:
        let
          pkgs = import nixpkgs { inherit system; };
          trackify = pkgs.callPackage ./nix/package.nix { src = self; };
          dev = pkgs.callPackage ./nix/dev.nix { inherit trackify; };
          devPackages = lib.filterAttrs (_: lib.isDerivation) dev;
        in
        {
          inherit pkgs trackify dev devPackages;
          packages = devPackages // { inherit trackify; default = dev.stack; };
        });

      forAllSystems = f: lib.mapAttrs (_: f) each;
    in
    {
      nixosModules.trackify = import ./nix/module.nix { src = self; };
      nixosModules.default = self.nixosModules.trackify;

      overlays.default = final: _: {
        trackify = final.callPackage ./nix/package.nix { src = self; };
      };

      packages = forAllSystems (it: it.packages);

      apps = forAllSystems (it:
        lib.mapAttrs (_: pkg: {
          type = "app";
          program = lib.getExe pkg;
        }) it.packages);

      devShells = forAllSystems ({ pkgs, trackify, devPackages, ... }: {
        default = pkgs.mkShell {
          packages = [
            trackify.passthru.pythonEnv
            pkgs.mariadb
            pkgs.redis
            pkgs.process-compose
          ] ++ lib.attrValues devPackages;

          # the scripts are on PATH here, so name the binaries, not `nix run`
          shellHook = ''
            echo "trackify dev env, state lives in ./.data"
            ${lib.concatMapStringsSep "\n"
              (pkg: ''echo "  ${baseNameOf (lib.getExe pkg)}"'')
              (lib.attrValues devPackages)}
            echo
          '';
        };
      });
    };
}
