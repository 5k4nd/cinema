import subprocess
from datetime import date, datetime, timedelta
from hashlib import md5
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional
from urllib.parse import quote_plus

import requests
from dateutil.parser import parse as dateutil_parse
from requests import JSONDecodeError

from cinema.exceptions import RemoteResourceException
from cinema.models import FilmShow
from cinema.settings import COMPRESS_PIC, OUT_PATH


if TYPE_CHECKING:
    from cinema.main import Cinema

SERVICE_URL = "http://www.allocine.fr"
SERVICE_TYPE = "allocine"


def _extract_directors(movie_meta: dict) -> str:
    directors_list = []
    directors = movie_meta["credits"]
    if isinstance(directors, dict):
        # weird case happening sometimes
        directors = directors.get("nodes", [])

    for person in directors:
        if person.get("position", {}).get("name") == "DIRECTOR":
            # firstname = person['person'].get('firstName')
            # firstname = f"{firstname[0]}." if firstname else ''
            directors_list.append(person["person"].get("lastName", ""))

    return ",".join(directors_list)


def _extract_release_date(movie_meta: dict) -> Optional[datetime]:
    release_date = None
    for release in movie_meta["releases"][::-1]:
        # explore releases from oldest (last ones) to newest
        if release.get("releaseDate"):
            release_date = dateutil_parse(release["releaseDate"]["date"])
            current_year = date.today().year
            # we only want month and day for current year movies
            release_date = (
                datetime.strftime(release_date, "%d/%m") if release_date.year == current_year else release_date.year
            )
            break

    return release_date


def _extract_show_times(movie_showtimes: dict) -> set:
    showtimes = set()  # set prevents duplicates

    # shows are divided across dubbed, original, local, etc., so we need to merge them before anything
    showtime_list = chain.from_iterable(movie_showtimes.values())

    for showtime in showtime_list:
        lang_tags = showtime["tags"]
        if lang_tags and isinstance(lang_tags, list) and len(lang_tags) > 0:
            lang = lang_tags[0].replace("Localization.Language.", "")
        else:
            # unknown lang tags format or content, let's assert the show is VO
            lang = None
        lang = "VF" if lang == "French" else "VO"
        show_date = dateutil_parse(showtime["startsAt"])
        showtimes.add(f"{show_date.hour}:{str(show_date.minute).zfill(2)} ({lang})")

    return showtimes


def fetch_next_week_shows(cinemas: Dict[str, List["Cinema"]]) -> Dict[str, List[List[FilmShow]]]:
    """
    Fetch shows from Allociné for one week, from today.

    Returns a dict where keys are cities names,
    and values are a list of 7 days,
    where each day is a list of FilmShow objects.
    """
    shows = {}
    for city_name, city_cinemas in cinemas.items():
        for cinema in city_cinemas:
            if cinema.type != SERVICE_TYPE:
                continue

            coming_week_days = [date.today() + timedelta(days=i) for i in range(7)]
            for day_idx, current_day in enumerate(coming_week_days):
                formatted_day = current_day.strftime("%Y-%m-%d")
                print(f"Fetching {cinema.name} shows for {formatted_day}...")
                resource = f"{SERVICE_URL}/_/showtimes/theater-{cinema.code}/d-{formatted_day}/"
                res = requests.get(resource)
                try:
                    res_json = res.json()
                except JSONDecodeError:
                    raise RemoteResourceException(resource, "invalid JSON response")
                if res.status_code != 200:
                    raise RemoteResourceException(resource, res_json)

                for movie in res_json["results"]:
                    movie_meta = movie["movie"]
                    if not movie_meta:
                        # show times not linked to any movie... what is that!? skipping.
                        continue

                    movie_title = movie["movie"]["title"]
                    release_date = _extract_release_date(movie_meta)
                    showtimes = _extract_show_times(movie["showtimes"])
                    allocine_movie_url = f"/film/fichefilm_gen_cfilm={movie['movie']['internalId']}.html"
                    tags = [tag["name"].split("/")[0].split("-")[0].strip() for tag in movie_meta["relatedTags"]]
                    search_engines_query = quote_plus(f"{movie_title} {release_date}")

                    poster_metas = movie_meta.get("poster")
                    poster_url = poster_metas.get("url", "") if poster_metas else ""

                    if not shows.get(city_name):
                        # init the data structure that will store the shows
                        shows[city_name] = [[] for _ in range(7)]

                    film_show = FilmShow(
                        label=movie_title + f"<br>({release_date})<br>{_extract_directors(movie_meta)}",
                        cinema=cinema.name,
                        allocine_url=SERVICE_URL + allocine_movie_url,
                        yt_url=f"https://www.youtube.com/results?search_query=trailer+{search_engines_query}",
                        sc_url=f"https://www.senscritique.com/search?query={search_engines_query}",
                        rotten_tomatos_url=f"https://www.rottentomatoes.com/search?search={search_engines_query}",
                        # langs=', '.join(movie_meta["languages"]),
                        synopsis=movie_meta.get("synopsisFull") or "Synopsis indisponible",
                        tags=" / ".join(tags),
                        url=f"{SERVICE_URL}/seance/salle_gen_csalle={cinema.code}.html",
                        poster_url=poster_url,
                        seances="<br>".join(sorted(showtimes)) + f'<br><br>{movie_meta.get("runtime") or "??"}',
                    )
                    film_show.poster_url = download_poster(film_show)
                    shows[city_name][day_idx].append(film_show)

            print("... done!")

        # remove days with no shows for the current city
        if shows.get(city_name):
            shows[city_name] = [day_shows or [] for day_shows in shows[city_name]]

    return shows


def download_poster(film_show: FilmShow) -> Optional[str]:
    """
    Download poster and returns relative path to it.
    Note: some films (too old, foreign countries) do not have posters.
    """
    url = film_show.poster_url
    if not url:
        # some movies (too old, foreign countries) do not have posters
        return None
    pic_directory = OUT_PATH / "pic"
    pic_directory.mkdir(parents=True, exist_ok=True)

    file_extension = Path(url).suffix
    url_hash = md5(url.encode()).hexdigest()
    filename = f"{url_hash}{file_extension}"
    local_file_path = pic_directory / filename
    if not local_file_path.is_file():  # if the file does not exist already
        res = requests.get(url)
        if not (200 <= res.status_code < 300):
            print(f"Exception downloading {url}.")
        else:
            pic_bytes = res.content
            with open(local_file_path, "wb") as f:
                f.write(pic_bytes)

            # resize images to vignettes
            if COMPRESS_PIC and subprocess.call(["magick", local_file_path, "-resize", "120x160", local_file_path]):
                print(f"Exception during resizing of {local_file_path}")

    local_path = f"../pic/{filename}"
    return local_path
