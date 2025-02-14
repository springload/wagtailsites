#!/bin/sh -e

cd $(dirname $(echo $0))

export APP_SECRET_KEY=1111
export DJANGO_AXES_BEHIND_REVERSE_PROXY=False

python manage.py migrate
python manage.py test
