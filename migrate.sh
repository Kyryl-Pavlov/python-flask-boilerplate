#!/bin/bash

set -e

# Discover services that have a Python package (services/<name>/app/)
services=()
for dir in services/*/; do
    name="${dir%/}"
    name="${name#services/}"
    if [ -d "services/$name/app" ]; then
        services+=("$name")
    fi
done

if [ ${#services[@]} -eq 0 ]; then
    echo "No services found under services/*/app/"
    exit 1
fi

if [ ${#services[@]} -eq 1 ]; then
    service="${services[0]}"
    echo "Service: $service"
else
    echo "Available services:"
    for i in "${!services[@]}"; do
        echo "  $((i+1))) ${services[$i]}"
    done
    read -p "Select service [1]: " selection
    selection="${selection:-1}"
    service="${services[$((selection-1))]}"
fi

service_dir="services/$service"
migrations_dir="$service_dir/migrations"

export FLASK_APP=app
export PYTHONPATH="$service_dir"

read -p "Migration message: " migration_message

if [ ! -d "$migrations_dir" ]; then
    (cd "$service_dir" && flask db init)
fi

(cd "$service_dir" && flask db migrate -m "$migration_message")

read -p "Migration created. Run upgrade? [y/N] " confirm
[[ "$confirm" == [yY] ]] && (cd "$service_dir" && flask db upgrade)
