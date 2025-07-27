{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    python3
  ] ++ (with pkgs.python3Packages;[
    pytelegrambotapi
    requests
    phonenumbers
  ]);
}
