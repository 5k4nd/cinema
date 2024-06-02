import locale
from os import getuid
from pathlib import Path
from pwd import getpwuid


locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")

PROJECT_PATH = Path("cinema")  # use absolute path if using systemd service
OUT_PATH = PROJECT_PATH / "html_out"
OUT_USER = getpwuid(getuid()).pw_name  # you can overdrive ex. with "foo"
OUT_GROUP = OUT_USER  # ex. "www-data" or "staff" on local OSX dev

TEMPLATES = PROJECT_PATH / "templates"
HTML_TEMPLATES_PATH = TEMPLATES / "html"
THEATERS_SOURCE_FILE = PROJECT_PATH / "cinemas.csv"
MAIN_CITY = "Besançon"
COMPRESS_PIC = True

GECKO_DRIVER_PATH = PROJECT_PATH / "geckodriver"
