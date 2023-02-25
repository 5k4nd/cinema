import locale
from os import getuid
from pathlib import Path
from pwd import getpwuid

locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")

TEMPLATES = Path("templates")
OUT_PATH = Path("html")
OUT_USER = getpwuid(getuid()).pw_name  # you can overdrive ex. with "bat"
OUT_GROUP = OUT_USER  # ex. "www-data"

SOURCE_PATH = "cinemas.csv"
MAIN_CITY = "Besançon"
COMPRESS_PIC = True
