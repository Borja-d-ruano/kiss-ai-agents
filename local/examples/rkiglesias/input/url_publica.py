"""
Helpers locales alineados con las reglas de MaRK en prompt.md.
El runner KISS no ejecuta este fichero: se inyecta como texto en el contexto
y, si usas Anthropic con bash, puedes ejecutarlo con:
  python3 input/url_publica.py --help
desde la carpeta del agente (cwd por defecto = carpeta del agente).
"""
from __future__ import annotations

import argparse
import re
import sys


def normalizar_telefono(raw: str) -> str:
    """Solo dígitos; quita +, espacios, guiones y letras."""
    return re.sub(r"\D", "", (raw or "").strip())


def corregir_url_propiedad(url: str) -> str:
    """Sustituye /properties/ por /propiedades/ en URLs públicas."""
    if not url:
        return url
    return url.replace("/properties/", "/propiedades/")


def _main() -> int:
    p = argparse.ArgumentParser(description="Utilidades MaRK (teléfono, URL pública)")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_phone = sub.add_parser("phone", help="Normaliza teléfono a dígitos")
    p_phone.add_argument("texto", nargs="?", default="", help="Ej. +34 611 222 333")

    p_url = sub.add_parser("url", help="Corrige segmento /properties/ en URL")
    p_url.add_argument("href", help="URL completa")

    args = p.parse_args()
    if args.cmd == "phone":
        print(normalizar_telefono(args.texto))
    elif args.cmd == "url":
        print(corregir_url_propiedad(args.href))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
