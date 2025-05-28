#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

import dotenv


def set_settings_module():
    in_test = bool({*sys.argv[1:]} & {"pytest", "test"})
    if in_test:
        os.environ["DJANGO_SETTINGS_MODULE"] = "jao_backend.settings.test"
        return

    in_dev = "DEV" == str(os.environ.get("ENV", "")).upper()
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        "jao_backend.settings.dev" if in_dev else "jao_backend.settings.common",
    )


def main():
    dotenv.load_dotenv(dotenv.find_dotenv())
    set_settings_module()
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?",
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
