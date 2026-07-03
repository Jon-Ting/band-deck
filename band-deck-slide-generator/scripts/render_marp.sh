#!/usr/bin/env bash
set -euo pipefail

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
