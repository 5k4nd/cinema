from dataclasses import dataclass
from typing import Dict, List

from _csv import reader

from settings import THEATERS_SOURCE_FILE
from sources import allocine
from utils.output_generator import generate_html_files


@dataclass
class Cinema:
    name: str
    code: str
    city: str
    type: str


def _load_cinemas() -> Dict[str, List[Cinema]]:
    with open(THEATERS_SOURCE_FILE) as f:
        cvs_reader = reader(f, delimiter=";")
        cinemas = {}
        for row, (t_name, t_city, t_source_type, t_code) in enumerate(cvs_reader):
            if row == 0:
                # skip header
                continue
            else:
                if not cinemas.get(t_city):
                    cinemas[t_city] = []
                cinemas[t_city].append(Cinema(name=t_name, code=t_code, city=t_city, type=t_source_type))

    return cinemas


if __name__ == "__main__":
    cinemas = _load_cinemas()

    # fetch from allocine
    one_week_shows = allocine.fetch_shows(cinemas)
    one_week_shows = allocine.download_posters(one_week_shows)

    # fetch other custom sources
    # besancon.get_shows()

    generate_html_files(cinemas, one_week_shows)
