#!/bin/bash
# ingest.sh — Wiki LLM — Mode 3 : ingestion vault complet
# Lit vault_path depuis config.yml et lance ingestwiki.py sans argument.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="$SCRIPT_DIR/config.yml"

if [ ! -f "$CONFIG" ]; then
    echo "Erreur : config.yml introuvable ($CONFIG)" >&2
    echo "  cp config.yml.example config.yml  # puis adapter vault_path" >&2
    exit 1
fi

exec "$SCRIPT_DIR/ingestwiki.py"
