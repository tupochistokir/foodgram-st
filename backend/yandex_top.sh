#!/bin/sh
set -e

# 1) миграции
python manage.py makemigrations --noinput
python manage.py migrate --noinput

# 2) «засев» ингредиентов
python manage.py load_ingredients ../data/ingredients.csv

# 3) запуск Gunicorn
exec gunicorn KirillGram.wsgi:application \
     --bind 0.0.0.0:8000 \
     --workers 3