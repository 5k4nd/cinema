from sources import allocine
from utils.output_generator import generate_html_files


if __name__ == "__main__":
    theaters = allocine.load_theaters_config()
    one_week_shows = allocine.fetch_shows(theaters)
    one_week_shows = allocine.download_posters(one_week_shows)
    generate_html_files(theaters, one_week_shows)
