import subprocess
from datetime import date, datetime
from hashlib import md5
from itertools import chain
from pathlib import Path
from typing import Dict, List
from urllib.parse import quote_plus

import requests
from dateutil.parser import parse as dateutil_parse
from requests import JSONDecodeError

from cinema.exceptions import RemoteResourceException
from cinema.main import Cinema
from cinema.settings import COMPRESS_PIC, OUT_PATH


SERVICE_URL = "http://www.allocine.fr"
SERVICE_TYPE = "allocine"


def fetch_shows(cinemas: Dict[str, List[Cinema]]) -> dict:
    """Fetch shows from Allociné for one week, from today."""
    shows = {}
    for city_name, city_cinemas in cinemas.items():
        for cinema in city_cinemas:
            if cinema.type != SERVICE_TYPE:
                continue
            for day_from_today in range(0, 7):
                print(f"Fetching {cinema.name} shows day today+{day_from_today}...")
                resource = f"{SERVICE_URL}/_/showtimes/theater-{cinema.code}/d-{day_from_today}/"
                res = requests.get(resource)
                if res.status_code != 200:
                    try:
                        res_json = res.json()
                    except JSONDecodeError:
                        raise RemoteResourceException(resource, "invalid JSON response")
                    raise RemoteResourceException(resource, res_json)

                for movie in res.json()["results"]:
                    movie_meta = movie["movie"]
                    if not movie_meta:
                        # show times not linked to any movie... what is that!? skipping.
                        continue

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
                        lang_tags = showtime["tags"]
                        if lang_tags and isinstance(lang_tags, list) and len(lang_tags) > 0:
                            lang = lang_tags[0].replace("Localization.Language.", "")
                        else:
                            # unknown lang tags format or content, let's assert the show is VO
                            lang = None
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

                    poster_metas = movie_meta.get("poster")
                    poster_url = poster_metas.get("url", "") if poster_metas else ""

                    if not shows.get(city_name):
                        shows[city_name] = [[] for _ in range(7)]
                    shows[city_name][day_from_today] += [
                        {
                            "film": movie_title + f"<br>({release_date})<br>{director_name}",
                            "cinema": cinema.name,
                            "allocineUrl": SERVICE_URL + allocine_movie_url,
                            "ytUrl": f"https://www.youtube.com/results?search_query=trailer+{search_engines_query}",
                            "scUrl": f"https://www.senscritique.com/search?query={search_engines_query}",
                            "rottenTomatosUrl": f"https://www.rottentomatoes.com/search?search={search_engines_query}",
                            # "langs": ', '.join(movie_meta["languages"]),
                            "synopsis": movie_meta.get("synopsisFull") or "Synopsis indisponible",
                            "tags": " / ".join(tags),
                            "allocineTheaterUrl": f"{SERVICE_URL}/seance/salle_gen_csalle={cinema.code}.html",
                            "posterUrl": poster_url,
                            "seance": "<br>".join(sorted(showtimes)) + f'<br><br>{movie_meta.get("runtime") or "??"}',
                        }
                    ]

            print("... done!")

        # remove days with no shows for the current city
        if shows.get(city_name):
            shows[city_name] = {idx: day_shows for idx, day_shows in enumerate(shows[city_name]) if day_shows}

    return shows


def download_posters(shows: dict) -> dict:
    """
    Download posters images into 'pic' path (set up in settings).
    Note that some movies (too old, foreign countries) do not have posters.
    """
    print("Downloading missing posters...")
    pic_path = OUT_PATH / "pic"
    pic_path.mkdir(parents=True, exist_ok=True)
    for city_name, city_shows in shows.items():
        for day_idx, day in city_shows.items():
            for show_idx, show in enumerate(day):
                url: str = show["posterUrl"]
                if not url:
                    # some movies (too old, foreign countries) do not have posters
                    continue
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

                        # resize images to vignettes
                        if COMPRESS_PIC and subprocess.call(
                            ["convert", local_file_path, "-resize", "120x160", local_file_path]
                        ):
                            print(f"Exception during resizing of {local_file_path}")

                # change url from remote to local
                shows[city_name][day_idx][show_idx]["posterUrl"] = ".." / Path("pic") / filename

    print("Done!")
    return shows
