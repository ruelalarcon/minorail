#!/usr/bin/env sh
set -e
ruff format .
basedpyright .
