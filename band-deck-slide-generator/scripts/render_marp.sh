#!/usr/bin/env bash
set -euo pipefail

# render_marp.sh
# A small helper script for rendering Marp slide markdown into HTML or PDF.
#
# Usage:
#   ./render_marp.sh INPUT.marp.md [html|pdf] [OUTPUT]
#
# INPUT:
#   Path to a Marp-flavored Markdown slide source file.
#
# FORMAT:
#   html  - render to HTML (default)
#   pdf   - render to PDF
#
# OUTPUT:
#   Optional path for the generated file. If omitted, the script will
#   replace the input extension with .html or .pdf.
#
# Requirements:
#   - Marp CLI must be installed and available on PATH.
usage() {
  printf 'Usage: %s INPUT.marp.md [html|pdf] [OUTPUT]\n' "$0" >&2
}

if [[ $# -lt 1 || $# -gt 3 ]]; then
  usage
  exit 2
fi

input=$1
format=${2:-html}

if [[ ! -f "$input" ]]; then
  printf 'error: input file not found: %s\n' "$input" >&2
  exit 2
fi

case "$format" in
  html|pdf)
    ;;
  *)
    printf 'error: unsupported format: %s\n' "$format" >&2
    usage
    exit 2
    ;;
esac

base=${input%.marp.md}
base=${base%.md}
output=${3:-"${base}.${format}"}

case "$format" in
  html)
    marp --html "$input" -o "$output"
    ;;
  pdf)
    marp --pdf "$input" -o "$output"
    ;;
esac

printf 'wrote: %s\n' "$output"
