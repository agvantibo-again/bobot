{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    python3
    black
  ] ++ (with pkgs.python3Packages;[
    pytelegrambotapi
    requests
    phonenumbers
  ]);
}
