from dataclasses import asdict
from datetime import date, timedelta
from os import chmod
from pathlib import Path
from shutil import chown, copyfile, copytree
from string import Template
from typing import Tuple, Dict, List, TYPE_CHECKING

from cinema.models import FilmShow
from cinema.settings import HTML_TEMPLATES_PATH, MAIN_CITY, OUT_GROUP, OUT_PATH, OUT_USER, TEMPLATES


if TYPE_CHECKING:
    from cinema.models import Cinema


def _normalize(city_name: str) -> str:
    return city_name.lower()


def _set_permissions():
    chmod(OUT_PATH, 0o755)
    chown(OUT_PATH, OUT_USER, OUT_GROUP)

    for path in sorted(OUT_PATH.rglob("*")):
        chmod(path, 0o755)
        chown(path, OUT_USER, OUT_GROUP)


def _load_templates_files() -> Tuple[Template, Template, Template]:
    with open(HTML_TEMPLATES_PATH / "row_one_movie.html") as template_file:
        seance_template = Template(template_file.read())

    with open(HTML_TEMPLATES_PATH / "table_one_day.html") as template_file:
        daily_template = Template(template_file.read())

    with open(HTML_TEMPLATES_PATH / "index.html") as template_file:
        index_template = Template(template_file.read())

    return index_template, daily_template, seance_template


def _write_html_files_for_city(city: str, current_city_one_week_shows: List[List[FilmShow]], tab_other_cities: str):
    index_template, daily_template, movie_row_template = _load_templates_files()
    out_path = OUT_PATH / _normalize(city)
    out_path.mkdir(parents=True, exist_ok=True)

    table_html = ""
    for day_index, movies_of_the_day in enumerate(current_city_one_week_shows):
        daily_html = ""
        for movie in movies_of_the_day:
            daily_html += movie_row_template.substitute(asdict(movie))
        table_html += daily_template.substitute(
            DayNumber=day_index,
            DayContent=daily_html,
            Day=(date.today() + timedelta(days=day_index)).strftime("%A %d/%m"),
            Checked=("Checked" if day_index == 0 else ""),
            Hidden=(day_index != 0),
            Selected=(day_index == 0),
        )

    with open(out_path / "index.html", "w+") as html_file:
        html_file.write(index_template.substitute(TableContent=table_html, TabOtherCities=tab_other_cities))


def _build_tab_other_cities(cinemas: dict) -> str:
    with open(HTML_TEMPLATES_PATH / "row_one_city.html") as template_file:
        city_template = Template(template_file.read())
    tab = ""
    for city_name, city_cinemas in cinemas.items():
        tab += city_template.substitute(
            NormalizedCity=_normalize(city_name),
            City=city_name,
            Cinemas=", ".join(cinema.name for cinema in city_cinemas),
        )
    return tab


def _write_static_files_if_needed():
    for ico_filename in ("allocine", "sc", "rottent", "yt"):
        ico_path = Path("pic") / (ico_filename + ".ico")
        if not (OUT_PATH / ico_path).is_file():
            copyfile((TEMPLATES / ico_path), (OUT_PATH / ico_path))

    if "css" not in [d.name for d in OUT_PATH.iterdir()]:
        copytree(TEMPLATES / "css", OUT_PATH / "css")


def _write_root_index_file():
    """Write a root index which redirects to the MAIN_CITY index page."""
    with open(OUT_PATH / "index.html", "w+") as html_file:
        with open(TEMPLATES / "html" / "root_index.html") as template_file:
            root_index_template = Template(template_file.read())
        html_file.write(root_index_template.substitute(mainCity=_normalize(MAIN_CITY)))


def generate_html_files(cinemas: Dict[str, List["Cinema"]], one_week_shows: Dict[str, List[List[FilmShow]]]):
    for city, current_city_one_week_shows in one_week_shows.items():
        tab_other_cities = _build_tab_other_cities(cinemas)
        _write_html_files_for_city(city, current_city_one_week_shows, tab_other_cities)

    _write_root_index_file()
    _write_static_files_if_needed()
    _set_permissions()
