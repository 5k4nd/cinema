from cinema.cinemas_sources import allocine
from cinema.models import load_cinemas

from cinema.output_generator import generate_html_files

if __name__ == "__main__":
    cinemas = load_cinemas()

    one_week_shows = allocine.fetch_shows(cinemas)
    # one_week_shows |= besancon.fetch_shows(cinemas)  # fixme

    generate_html_files(cinemas, one_week_shows)
