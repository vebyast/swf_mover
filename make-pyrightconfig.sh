#!/usr/bin/env bash

VENV_FULLPATH=$(poetry env info -p)
VENV_PATH=$(dirname "${VENV_FULLPATH}")
VENV_NAME=$(basename "${VENV_FULLPATH}")

echo "{ \"venv\": \"${VENV_NAME}\", \"venvPath\": \"${VENV_PATH}\" }" | jq >pyrightconfig.json
