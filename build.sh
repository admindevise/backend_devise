#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

python manage.py migrate

# Initialize audit actions
python manage.py init_audit_actions

# Load initial data cities
#python manage.py cities_light --force-all

# Import DRUO Data
#python manage.py import_druo_data --all

# First Superuser Creation
#DJANGO_SUPERUSER_USERNAME=admin \
#DJANGO_SUPERUSER_EMAIL=admin@admin.com \
#DJANGO_SUPERUSER_PASSWORD=admin \
#DJANGO_SUPERUSER_PHONE=3227177889 \
#python manage.py createsuperuser --noinput || true