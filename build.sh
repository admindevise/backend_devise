#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

python manage.py migrate

# Initialize audit actions
python manage.py init_audit_actions

python manage.py import_druo_data --all