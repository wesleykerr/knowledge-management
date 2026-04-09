#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
set -a
source "$(dirname "$0")/../.env"
set +a
exec "$@"
