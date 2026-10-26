#!/bin/sh
# SPDX-FileCopyrightText: 2026 Greg Pfountz
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSE for license terms and the warranty disclaimer.
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ -n "${DEPLOY_PYTHON:-}" ]; then
    PYTHON_EXECUTABLE=$DEPLOY_PYTHON
elif [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON_EXECUTABLE="$PROJECT_ROOT/.venv/bin/python"
else
    PYTHON_EXECUTABLE=python3
fi
exec "$PYTHON_EXECUTABLE" "$PROJECT_ROOT/scripts/deploy.py" "$@"
