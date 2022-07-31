#!/usr/bin/env python3

from csv import reader
from datetime import date, timedelta, datetime
from os import chmod
from shutil import chown, copytree
from string import Template
from typing import Tuple
from urllib.parse import quote_plus

import requests
from dateutil.parser import parse

from settings import OUT_PATH, TEMPLATES, SOURCE_PATH, OUT_GROUP, OUT_USER

allocine_url = "http://www.allocine.fr"


def set_permissions():
    chmod(OUT_PATH, 0o755)
    chown(OUT_PATH, OUT_USER, OUT_GROUP)

    for path in sorted(OUT_PATH.rglob("*")):
        chmod(path, 0o755)
        chown(path, OUT_USER, OUT_GROUP)


def load_theaters() -> dict:
    with open(SOURCE_PATH) as f:
        cvs_reader = reader(f)
        raw_theaters = {}
        for row, (t_name, t_code) in enumerate(cvs_reader):
            if row == 0:
                # skip header
                continue
            else:
                raw_theaters[t_code] = t_name
    return raw_theaters


def fetch_theaters_shows() -> dict:
    """Fetch shows from Allociné for one week, from today."""

    one_week_shows = [[] for i in range(7)]
    for c_code, cinema_name in theaters.items():
        for day_from_today in range(0, 7):
            print(f"Fetching {cinema_name} shows day today+{day_from_today}...")
            res = requests.get(f"{allocine_url}/_/showtimes/theater-{c_code}/d-{day_from_today}/")
            if not res.status_code == 200:
                print(res.content.decode())

            res_json = res.json()

            for movie in res_json["results"]:
                movie_meta = movie["movie"]
                release_date = ""
                for release in movie_meta["releases"][::-1]:
                    # explore releases from oldest (last ones) to newest
                    if release.get("releaseDate"):
                        release_date = parse(release["releaseDate"]["date"])
                        current_year = date.today().year
                        # we only want month and day for current year movies
                        release_date = (
                            datetime.strftime(release_date, "%d/%m")
                            if release_date.year == current_year
                            else release_date.year
                        )
                        break

                showtimes = []
                for showtime in movie["showtimes"][
                    "local"
                    if movie["showtimes"]["local"]
                    else "multiple"
                    if movie["showtimes"]["multiple"]
                    else "original"
                ]:
                    lang = showtime["tags"][0].replace("Localization.Language.", "")
                    lang = "VF" if lang == "French" else "VO"
                    showtimes.append(f"{showtime['startsAt'][11:16]} ({lang})")

                movie_title = movie["movie"]["title"]
                allocine_movie_url = f"/film/fichefilm_gen_cfilm={movie['movie']['internalId']}.html"
                yt_url = f"https://www.youtube.com/results?search_query={quote_plus(f'trailer {movie_title} {release_date}')}"
                tags = [tag["name"].split('/')[0].split('-')[0].strip() for tag in movie_meta["relatedTags"]]

                one_week_shows[day_from_today] += [
                    {
                        "film": movie_title + f"<br>({release_date})",
                        "cinema": cinema_name,
                        "filmUrl": allocine_movie_url,
                        "ytUrl": yt_url,
                        # "langs": ', '.join(movie_meta["languages"]),
                        "synopsis": movie_meta["synopsisFull"],
                        "tags": " / ".join(tags),
                        "cinemaUrl": f"{allocine_url}/seance/salle_gen_csalle={c_code}.html",
                        "posterUrl": movie_meta["poster"]["url"],
                        "seance": "<br>".join(showtimes) + f'<br><br>{movie_meta["runtime"]}',
                    }
                ]
        print("... done!")

    result = {idx: s for idx, s in enumerate(one_week_shows) if s}
    return result


def load_templates_files() -> Tuple[Template, Template, Template]:
    html_templates_path = TEMPLATES / "html"
    with open(html_templates_path / "row.html") as template_file:
        seance_template = Template(template_file.read())

    with open(html_templates_path / "table.html") as template_file:
        daily_template = Template(template_file.read())

    with open(html_templates_path / "index.html") as template_file:
        index_template = Template(template_file.read())

    return seance_template, daily_template, index_template


def write_html_files(ordered_shows: dict):
    seance_template, daily_template, index_template = load_templates_files()

    tab_html = ""
    for index, showtime_of_day in ordered_shows.items():
        daily_html = ""
        for seance in showtime_of_day:
            daily_html += seance_template.substitute(seance)
        tab_html += daily_template.substitute(
            DayNumber=index,
            Value=daily_html,
            Day=(date.today() + timedelta(days=index)).strftime("%A %d/%m"),
            Checked=("Checked" if index == 0 else ""),
            Hidden=(index != 0),
            Selected=(index == 0),
        )

    OUT_PATH.mkdir(parents=True, exist_ok=True)
    if "css" not in [d.name for d in OUT_PATH.iterdir()]:
        copytree(TEMPLATES / "css", OUT_PATH / "css")
    with open(OUT_PATH / "index.html", "w+") as html_file:
        html_file.write(index_template.substitute(Value=tab_html))


if __name__ == "__main__":
    theaters = load_theaters()
    one_week_seances = fetch_theaters_shows()
    write_html_files(one_week_seances)
    set_permissions()
