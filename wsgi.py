# Этот файл является точкой входа для WSGI-сервера PythonAnywhere.

import sys
import os

# Добавляем директорию проекта в пути Python
path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.insert(0, path)

# Импортируем Flask-приложение из нашего основного файла
# `flask_app` - это имя переменной, которой мы присвоили `Flask(__name__)` в `main.py`
from main import flask_app as application
