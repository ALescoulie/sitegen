{
  description = "My personal website";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    nixpkgs-pandoc.url = "github:nixos/nixpkgs/nixos-23.05";
    flake-utils.url = "github:numtide/flake-utils";
    poetry2nix.url = "github:nix-community/poetry2nix";
  };

  outputs = { self, nixpkgs, nixpkgs-pandoc, flake-utils, poetry2nix }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        lib = nixpkgs.lib;
        pkgs = nixpkgs.legacyPackages.${system};
        p2nix = poetry2nix.lib.mkPoetry2Nix { inherit pkgs; };

        customOverrides = final: prev: {
          pandoc = prev.pandoc.overrideAttrs (oldAttrs: {
            buildInputs = [ prev.setuptools ];
            runtimeInputs = [ prev.setuptools ];
          });
        };

        pandoc = nixpkgs-pandoc.legacyPackages.${system}.pandoc;

        app = p2nix.mkPoetryApplication {
          projectDir = ./.;
          overrides =
            [ p2nix.defaultPoetryOverrides customOverrides ];
          postFixup = ''
            wrapProgram $out/bin/sitegen \
              --set PATH ${lib.makeBinPath [
                pandoc
              ]}
          '';

        };
        # DON'T FORGET TO PUT YOUR PACKAGE NAME HERE, REMOVING `throw`
        packageName = "sitegen";

      in {
        packages.${packageName} = app;
        packages.default = self.packages.${system}.${packageName};

        devShells.default = pkgs.mkShell {
          buildInputs = [ pkgs.poetry pandoc ];
          inputsFrom = builtins.attrValues self.packages.${system};
        };
      });
}
