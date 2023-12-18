{
  description = "My personal website";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    nixpkgs-pandoc.url = "github:nixos/nixpkgs/nixos-23.05";
    flake-utils.url = "github:numtide/flake-utils";
    blog-posts = {
      url = "github:ALescoulie/blog_posts";
      flake = false;
    };
    poetry2nix.url = "github:nix-community/poetry2nix";
  };

  outputs = { self, nixpkgs, nixpkgs-pandoc, flake-utils, blog-posts, poetry2nix }:
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
        packageName = "alialescoulie-com";

        makeSite = content: pkgs.runCommand "site" {} ''
          cp -r ${content} blog_posts
          ${app}/bin/sitegen
          cp -r site_out $out
        '';
      in {
        packages.${packageName} = app;
        packages.site = makeSite blog-posts;
        packages.default = self.packages.${system}.site;

        devShells.default = pkgs.mkShell {
          buildInputs = [ pkgs.poetry pandoc ];
          inputsFrom = builtins.attrValues self.packages.${system};
        };
      });
}
