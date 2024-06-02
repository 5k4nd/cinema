from _csv import reader
from dataclasses import dataclass
from typing import Dict, List

from settings import THEATERS_SOURCE_FILE


@dataclass
class Cinema:
    name: str
    code: str
    city: str
    type: str


def load_cinemas() -> Dict[str, List[Cinema]]:
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


@dataclass
class FilmShow:
    label: str
    cinema: str
    allocine_url: str
    yt_url: str
    sc_url: str
    rotten_tomatos_url: str
    synopsis: str
    tags: str
    url: str
    poster_url: str
    seances: str
