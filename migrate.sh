#!/bin/bash

set -e

read -p "Migration message: " migration_message

if [ ! -d "migrations" ]; then
    flask db init
fi

flask db migrate -m "$migration_message"

read -p "Migration created. Run upgrade? [y/N] " confirm
[[ "$confirm" == [yY] ]] && flask db upgrade
