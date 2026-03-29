{
  description = "Ansel";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-25.11";
    nixpkgs-rolling.url = "github:nixos/nixpkgs?ref=nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      nixpkgs-rolling,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        pkgs-rolling = nixpkgs-rolling.legacyPackages.${system};
        pyproject = builtins.fromTOML (builtins.readFile ./pyproject.toml);
        metadata = pyproject.tool.poetry;
        pythonVersion = "python313";
        python = pkgs.${pythonVersion};

        deps =
          ps: with ps; [
            click
            jinja2
            gitpython
            ruamel-yaml
            tomlkit
            pydantic
            pydantic-settings
          ];

        all-deps =
          ps:
          (deps ps)
          ++ (with ps; [
            pytest
            pytest-cov
          ]);

        pythonWithDeps = python.withPackages all-deps;
      in
      {
        formatter = pkgs.nixpkgs-fmt;

        packages = {
          ansel = pkgs.python3Packages.buildPythonApplication {
            pname = metadata.name;
            version = metadata.version;
            src = ./.;
            format = "pyproject";
            nativeBuildInputs = [ pkgs.python3Packages.poetry-core ];
            propagatedBuildInputs = deps pkgs.python3Packages;
            meta = {
              mainProgram = "ansel";
            };
          };
          default = self.packages.${system}.ansel;
        };

        devShells.default = pkgs.mkShell {
          inputsFrom = [ self.packages.${system}.ansel ];
          packages =
            with pkgs;
            [
              just
              poetry
              pre-commit
              ruff
              pythonWithDeps
            ]
            ++ [
              pkgs-rolling.gemini-cli
            ];
          PYTHONDONTWRITEBYTECODE = 1;
          POETRY_VIRTUALENVS_IN_PROJECT = true;
        };
      }
    );
}
