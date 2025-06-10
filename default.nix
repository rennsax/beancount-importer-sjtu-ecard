let
  beancount-importer-sjtu-ecard =
    {
      python3,
    }:
    with python3.pkgs;
    buildPythonPackage {
      pname = "beancount-importer-sjtu-ecard";
      version = "0.0.1";
      pyproject = true;
      src = ./.;
      build-system = [
        hatchling
      ];
      dependencies = [
        beancount_2
        beautifulsoup4
      ];
    };
in
{
  pkgs ? import <nixpkgs> { },
}:
pkgs.callPackage beancount-importer-sjtu-ecard { }
