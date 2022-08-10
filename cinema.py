#!/usr/bin/env python3

from csv import reader
from datetime import date, datetime, timedelta
from hashlib import md5
from itertools import chain
from os import chmod
from pathlib import Path
from shutil import chown, copyfile, copytree
from string import Template
from typing import Tuple
from urllib.parse import quote_plus

import requests
from dateutil.parser import parse as dateutil_parse
from unidecode import unidecode

from settings import MAIN_CITY, OUT_GROUP, OUT_PATH, OUT_USER, SOURCE_PATH, TEMPLATES


allocine_url = "http://www.allocine.fr"
HTML_TEMPLATES_PATH = TEMPLATES / "html"


def set_permissions():
    chmod(OUT_PATH, 0o755)
    chown(OUT_PATH, OUT_USER, OUT_GROUP)

    for path in sorted(OUT_PATH.rglob("*")):
        chmod(path, 0o755)
        chown(path, OUT_USER, OUT_GROUP)


def load_theaters_config() -> dict:
    with open(SOURCE_PATH) as f:
        cvs_reader = reader(f, delimiter=";")
        raw_theaters = {}
        for row, (t_name, t_code, t_city) in enumerate(cvs_reader):
            if row == 0:
                # skip header
                continue
            else:
                if not raw_theaters.get(t_city):
                    raw_theaters[t_city] = {}
                raw_theaters[t_city][t_code] = t_name
    return raw_theaters


def fetch_shows() -> dict:
    """Fetch shows from Allociné for one week, from today."""
    shows = {}
    for city_name, city_theaters in theaters.items():
        for c_code, cinema_name in city_theaters.items():
            for day_from_today in range(0, 7):
                print(f"Fetching {cinema_name} shows day today+{day_from_today}...")
                res = requests.get(f"{allocine_url}/_/showtimes/theater-{c_code}/d-{day_from_today}/")
                if res.status_code != 200:
                    print(res.content.decode())

                res_json = res.json()

                for movie in res_json["results"]:
                    movie_meta = movie["movie"]
                    release_date = ""
                    for release in movie_meta["releases"][::-1]:
                        # explore releases from oldest (last ones) to newest
                        if release.get("releaseDate"):
                            release_date = dateutil_parse(release["releaseDate"]["date"])
                            current_year = date.today().year
                            # we only want month and day for current year movies
                            release_date = (
                                datetime.strftime(release_date, "%d/%m")
                                if release_date.year == current_year
                                else release_date.year
                            )
                            break

                    showtimes = set()  # set prevents duplicates
                    # shows are divided across dubbed, original, local, etc.,so we need to merge them before anything
                    showtime_list = chain.from_iterable(movie["showtimes"].values())
                    for showtime in showtime_list:
                        lang = showtime["tags"][0].replace("Localization.Language.", "")
                        lang = "VF" if lang == "French" else "VO"
                        show_date = dateutil_parse(showtime["startsAt"])
                        showtimes.add(f"{show_date.hour}:{str(show_date.minute).zfill(2)} ({lang})")

                    movie_title = movie["movie"]["title"]
                    allocine_movie_url = f"/film/fichefilm_gen_cfilm={movie['movie']['internalId']}.html"
                    tags = [tag["name"].split("/")[0].split("-")[0].strip() for tag in movie_meta["relatedTags"]]
                    search_engines_query = quote_plus(f"{movie_title} {release_date}")

                    director_name = ""
                    for person in movie_meta["credits"]:
                        if person.get("position", {}).get("name") == "DIRECTOR":
                            # firstname = person['person'].get('firstName')
                            # firstname = f"{firstname[0]}." if firstname else ''
                            director_name = person["person"].get("lastName", "")

                    if not shows.get(city_name):
                        shows[city_name] = [[] for _ in range(7)]
                    shows[city_name][day_from_today] += [
                        {
                            "film": movie_title + f"<br>({release_date})<br>{director_name}",
                            "cinema": cinema_name,
                            "allocineUrl": allocine_url + allocine_movie_url,
                            "ytUrl": f"https://www.youtube.com/results?search_query=trailer+{search_engines_query}",
                            "scUrl": f"https://www.senscritique.com/search?query={search_engines_query}",
                            # "langs": ', '.join(movie_meta["languages"]),
                            "synopsis": movie_meta["synopsisFull"],
                            "tags": " / ".join(tags),
                            "allocineTheaterUrl": f"{allocine_url}/seance/salle_gen_csalle={c_code}.html",
                            "posterUrl": movie_meta["poster"]["url"],
                            "seance": "<br>".join(sorted(showtimes)) + f'<br><br>{movie_meta["runtime"]}',
                        }
                    ]

            print("... done!")

        # remove days with no shows for the current city
        if shows.get(city_name):
            shows[city_name] = {idx: day_shows for idx, day_shows in enumerate(shows[city_name]) if day_shows}

    return shows


def load_templates_files() -> Tuple[Template, Template, Template]:
    with open(HTML_TEMPLATES_PATH / "row_one_movie.html") as template_file:
        seance_template = Template(template_file.read())

    with open(HTML_TEMPLATES_PATH / "table_one_day.html") as template_file:
        daily_template = Template(template_file.read())

    with open(HTML_TEMPLATES_PATH / "index.html") as template_file:
        index_template = Template(template_file.read())

    return index_template, daily_template, seance_template


def write_html_files_for_city(city: str, current_city_one_week_shows: dict):
    index_template, daily_template, movie_row_template = load_templates_files()
    out_path = OUT_PATH / normalize(city)
    out_path.mkdir(parents=True, exist_ok=True)

    table_html = ""
    for index, movies_of_the_day in current_city_one_week_shows.items():
        int_index = int(index)
        daily_html = ""
        for movie in movies_of_the_day:
            daily_html += movie_row_template.substitute(movie)
        table_html += daily_template.substitute(
            DayNumber=int_index,
            DayContent=daily_html,
            Day=(date.today() + timedelta(days=int_index)).strftime("%A %d/%m"),
            Checked=("Checked" if int_index == 0 else ""),
            Hidden=(int_index != 0),
            Selected=(int_index == 0),
        )

    with open(out_path / "index.html", "w+") as html_file:
        html_file.write(index_template.substitute(TableContent=table_html, TabOtherCities=tab_other_cities))


def build_tab_other_cities(theaters: dict) -> str:
    with open(HTML_TEMPLATES_PATH / "row_one_city.html") as template_file:
        city_template = Template(template_file.read())
    tab = ""
    for city_name, city_theaters in theaters.items():
        tab += city_template.substitute(
            NormalizedCity=normalize(city_name), City=city_name, Theaters=", ".join(city_theaters.values())
        )
    return tab


def normalize(city_name: str) -> str:
    return unidecode(city_name).lower()


def download_posters(shows: dict) -> dict:
    print("Downloading missing posters...")
    pic_path = OUT_PATH / "pic"
    pic_path.mkdir(parents=True, exist_ok=True)
    for city_name, city_shows in shows.items():
        for day_idx, day in city_shows.items():
            for show_idx, show in enumerate(day):
                url = show["posterUrl"]
                file_ext = Path(url).suffix
                url_hash = md5(url.encode()).hexdigest()
                filename = f"{url_hash}{file_ext}"
                local_file_path = pic_path / filename
                if not local_file_path.is_file():  # if the file does not exist already
                    res = requests.get(url)
                    if not (200 <= res.status_code < 300):
                        print(f"Exception downloading {url}.")
                        continue
                    else:
                        pic_bytes = res.content
                        with open(local_file_path, "wb") as f:
                            f.write(pic_bytes)

                # change url from remote to local
                shows[city_name][day_idx][show_idx]["posterUrl"] = ".." / Path("pic") / filename

    print("Done!")
    return shows


def write_static_files_if_needed():
    for ico_filename in ("allocine.ico", "sc.ico", "yt.ico"):
        ico_path = Path("pic") / ico_filename
        if not (OUT_PATH / ico_path).is_file():
            copyfile((TEMPLATES / ico_path), (OUT_PATH / ico_path))

    if "css" not in [d.name for d in OUT_PATH.iterdir()]:
        copytree(TEMPLATES / "css", OUT_PATH / "css")


def write_root_index_file():
    """Write a root index which redirects to the MAIN_CITY index page."""
    with open(OUT_PATH / "index.html", "w+") as html_file:
        with open(TEMPLATES / "html" / "root_index.html") as template_file:
            root_index_template = Template(template_file.read())
        html_file.write(root_index_template.substitute(mainCity=normalize(MAIN_CITY)))


if __name__ == "__main__":
    theaters = load_theaters_config()
    one_week_shows = fetch_shows()
    one_week_shows = download_posters(one_week_shows)

    for city, current_city_one_week_shows in one_week_shows.items():
        tab_other_cities = build_tab_other_cities(theaters)
        write_html_files_for_city(city, current_city_one_week_shows)

    write_root_index_file()
    write_static_files_if_needed()
    set_permissions()
