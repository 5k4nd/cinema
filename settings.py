import locale
from os import getuid
from pathlib import Path
from pwd import getpwuid

locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")

CODE_DIR = Path(".")  # use absolute path if using systemd service
OUT_PATH = Path("html")    # use absolute path if using systemd service
OUT_USER = getpwuid(getuid()).pw_name # you can overdrive ex. with "foo"
OUT_GROUP = OUT_USER # ex. "www-data" or "staff" on local OSX dev

TEMPLATES = CODE_DIR / "templates"
SOURCE_PATH = CODE_DIR / "cinemas.csv"  # todo: rename to THEATERS_SOURCE_FILE
MAIN_CITY = "Besançon"
COMPRESS_PIC = True
