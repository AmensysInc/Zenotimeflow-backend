#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zeno_time.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        # Try to use the Python that has Django installed
        django_python = r"D:\Django\python.exe"
        if os.path.exists(django_python):
            print(f"\n  Django not found in current Python interpreter.")
            print(f" Using: {django_python}")
            print(f" Run: {django_python} manage.py {' '.join(sys.argv[1:])}\n")
            # Re-execute with the correct Python
            os.execv(django_python, [django_python] + sys.argv)
        else:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?\n\n"
                f"Current Python: {sys.executable}\n"
                f"Expected Django Python: {django_python}\n"
                "Please install Django: pip install -r requirements.txt"
            ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()

