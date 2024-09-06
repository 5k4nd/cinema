"""
This module is a web scrapper for the Petit Kursaal cinema in Besançon.
"""

import time
from datetime import datetime
from typing import List

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common import NoSuchDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from unidecode import unidecode

from cinema.exceptions import GeckoDriverNotFound
from cinema.models import FilmShow
from cinema.settings import PROJECT_PATH

SERVICE_URL = "https://les2scenes.fr/cinema"


MONTHS_FR = (
    "janvier",
    "fevrier",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "aout",
    "septembre",
    "octobre",
    "novembre",
    "decembre",
)


def _get_next_month(month: str):
    must_return = False
    for cur_month in MONTHS_FR:
        if must_return:
            return cur_month
        elif cur_month == month:
            must_return = True
    # default case: decembre must return janvier
    return MONTHS_FR[0]


def _init_web_browser():
    """Download gecko driver here: https://github.com/mozilla/geckodriver/releases."""
    # Set up Selenium WebDriver with Firefox
    firefox_options = Options()
    firefox_options.add_argument("--headless")  # comment this line for debugging
    firefox_options.set_preference(
        "general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/126.0"
    )
    geckodriver_path = PROJECT_PATH / "geckodriver"
    service = Service(geckodriver_path)
    try:
        driver = webdriver.Firefox(service=service, options=firefox_options)
    except NoSuchDriverException:
        raise GeckoDriverNotFound()

    driver.get(SERVICE_URL)
    wait = WebDriverWait(driver, 1)
    wait.until(expected_conditions.visibility_of_element_located((By.ID, "calendar")))

    # Get the page source and parse it
    soup = BeautifulSoup(driver.page_source, "html.parser")
    return driver, soup


def _get_web_element_of_current_day(driver, cur_day_int: int):
    """Find the WebElement corresponding to the current day."""

    cur_day_web_elements = driver.find_elements(By.XPATH, f"//*[@id='calendar']//td[text()='{cur_day_int}']")
    if len(cur_day_web_elements) > 2:
        raise Exception(
            f"We fetched more than 2 days for the same day {cur_day_int}, this is bad, the HTML page has probably "
            f"changed A LOT since the writing of this script."
        )
    elif len(cur_day_web_elements) == 2 and "jsCalendar-previous" in cur_day_web_elements[0].get_attribute("class"):
        # we do have multiple days because we also fetched the day from the previous month, let's skip it and take
        # the second one directly
        return cur_day_web_elements[1]

    return cur_day_web_elements[0]


def _get_calendar_header_element(soup, element: str) -> str:
    calendar_div = soup.find("div", id="calendar")
    table = calendar_div.find("table")
    table_head = table.find("thead")
    header = table_head.find_all("th")
    for th in header:
        calendar_title_div = th.find("div", class_=element)
        if calendar_title_div:
            return unidecode(calendar_title_div.text.strip().lower())


def _open_popup_and_get_current_day_content(driver, cur_day_web_element):
    """
    Emulate mouse hover to display the popup which displays details about this day.
    Return a web element reference to the popup.
    """
    actions = ActionChains(driver)
    actions.move_to_element(cur_day_web_element).perform()
    # wait for the popup to appear
    time.sleep(0.1)
    return driver.find_element(By.XPATH, "//*[@id='calendar-popup']")


def _close_popup(driver):
    calendar_elem = driver.find_element(By.XPATH, "//html")
    actions = ActionChains(driver)
    actions.move_to_element(calendar_elem).perform()
    time.sleep(0.5)


def _fetch_movies_from_the_current_month(driver, soup, cur_month: str) -> dict:
    print(f"Fetching movies for {cur_month}...")
    ret_movies = {}

    calendar_div = soup.find("div", id="calendar")
    table = calendar_div.find("table")
    calendar_rows = table.find_all("tr")

    # iterate over calendar table rows and columns to find td-days for the current month
    for calendar_row in calendar_rows:
        current_row_days = calendar_row.find_all("td")
        for current_day in current_row_days:
            if "jsCalendar-previous" in current_day.attrs.get("class", []):
                # skipping days from the previous month
                continue
            if "jsCalendar-next" in current_day.attrs.get("class", []):
                # we are now iterating over days from the next month
                print(f"End of {cur_month}")
                return ret_movies

            if "has-events" not in current_day.attrs.get("class", []):
                # skipping days with no movies events
                continue

            cur_day_int = int(current_day.text.strip())
            cur_day_web_element = _get_web_element_of_current_day(driver, cur_day_int)

            movies_popup = _open_popup_and_get_current_day_content(driver, cur_day_web_element)
            for movie in movies_popup.find_elements(By.XPATH, "./ul/li"):
                movie_element = movie.find_element(By.XPATH, "./a")
                href_value = movie_element.get_attribute("href")
                if not ret_movies.get(cur_month):
                    ret_movies[cur_month] = {}
                if not ret_movies[cur_month].get(cur_day_int):
                    ret_movies[cur_month][cur_day_int] = []
                ret_movies[cur_month][cur_day_int].append((movie_element.text, href_value))
            _close_popup(driver)

    return ret_movies


def _load_next_month(driver):
    """Load the next month in the calendar view. It triggers a js call."""
    next_month_elem = driver.find_element(
        By.XPATH, "//div[contains(@class, 'jsCalendar-title-right')]/div[contains(@class, 'jsCalendar-nav-right')]"
    )
    next_month_elem.click()
    # parse the new page
    soup = BeautifulSoup(driver.page_source, "html.parser")
    return soup


def fetch_next_months_shows(driver, soup)-> dict:
    """
    Get film shows from Cinemas Besançon.
    """
    current_month = _get_calendar_header_element(soup, "jsCalendar-title-name")
    movies_result = _fetch_movies_from_the_current_month(driver, soup, current_month)

    soup = _load_next_month(driver)

    movies_result |= _fetch_movies_from_the_current_month(driver, soup, _get_next_month(current_month))
    return movies_result


def refine_shows_to_next_week_only(movies_result: dict) -> List[List[FilmShow]]:
    # only keep next week shows
    current_month_fr = datetime.now().strftime('%B')

    # for each show, scrap details

    pass


def fetch_next_week_shows() -> List[List[FilmShow]]:
    driver, soup = _init_web_browser()
    # next_months_shows = fetch_next_months_shows(driver, soup)
    next_months_shows = {"juin": {"4": [["18h15 The Big Lebowski", "https://les2scenes.fr/cinema/big-lebowski"], ["20h30 No Country for Old Men", "https://les2scenes.fr/cinema/no-country-old-men"]], "5": [["16h The Big Lebowski", "https://les2scenes.fr/cinema/big-lebowski"], ["18h15 La M\u00e8re de tous les mensonges", "https://les2scenes.fr/cinema/la-mere-de-tous-les-mensonges"], ["20h30 Le Bleu du caftan", "https://les2scenes.fr/cinema/le-bleu-du-caftan"]], "6": [["16h La M\u00e8re de tous les mensonges", "https://les2scenes.fr/cinema/la-mere-de-tous-les-mensonges"], ["18h15 No Country for Old Men", "https://les2scenes.fr/cinema/no-country-old-men"], ["20h30 The Big Lebowski", "https://les2scenes.fr/cinema/big-lebowski"]], "7": [["16h Le Bleu du caftan", "https://les2scenes.fr/cinema/le-bleu-du-caftan"], ["18h15 La M\u00e8re de tous les mensonges", "https://les2scenes.fr/cinema/la-mere-de-tous-les-mensonges"], ["20h30 A Serious Man", "https://les2scenes.fr/cinema/serious-man"]], "8": [["16h Menus-Plaisirs Les Troisgros", "https://les2scenes.fr/cinema/menus-plaisirs-les-troisgros"], ["20h Caf\u00e9-cin\u00e9 | Juin 2024", "https://les2scenes.fr/cinema/cafe-cine-juin-2024"]], "10": [["18h15 True Grit", "https://les2scenes.fr/cinema/true-grit"], ["20h30 Animalia", "https://les2scenes.fr/cinema/animalia"]], "11": [["16h Animalia", "https://les2scenes.fr/cinema/animalia"], ["18h15 A Serious Man", "https://les2scenes.fr/cinema/serious-man"], ["20h30 Inside Llewyn Davis", "https://les2scenes.fr/cinema/inside-llewyn-davis"]], "13": [["18h15 The Big Lebowski", "https://les2scenes.fr/cinema/big-lebowski"], ["20h30 No Country for Old Men", "https://les2scenes.fr/cinema/no-country-old-men"]], "14": [["16h The Big Lebowski", "https://les2scenes.fr/cinema/big-lebowski"], ["18h15 La M\u00e8re de tous les mensonges", "https://les2scenes.fr/cinema/la-mere-de-tous-les-mensonges"], ["20h30 Le Bleu du caftan", "https://les2scenes.fr/cinema/le-bleu-du-caftan"]], "15": [["16h The Big Lebowski", "https://les2scenes.fr/cinema/big-lebowski"], ["18h15 La M\u00e8re de tous les mensonges", "https://les2scenes.fr/cinema/la-mere-de-tous-les-mensonges"], ["20h30 Le Bleu du caftan", "https://les2scenes.fr/cinema/le-bleu-du-caftan"]]}, "juillet": {"3": [["18h Yannick", "https://les2scenes.fr/cinema/yannick"], ["19h30 Caf\u00e9-cin\u00e9 | Juillet 2024", "https://les2scenes.fr/cinema/cafe-cine-juillet-2024"], ["20h30 Yannick", "https://les2scenes.fr/cinema/yannick"]], "8": [["14h Atelier Tremplin", "https://les2scenes.fr/cinema/atelier-tremplin"], ["14h30 Ratatouille", "https://les2scenes.fr/cinema/ratatouille"], ["18h Le Ch\u00e2teau dans le ciel", "https://les2scenes.fr/cinema/le-chateau-dans-le-ciel"]], "9": [["14h Atelier Tremplin", "https://les2scenes.fr/cinema/atelier-tremplin"], ["14h30 Mon ami robot", "https://les2scenes.fr/cinema/mon-ami-robot"], ["18h Migration", "https://les2scenes.fr/cinema/migration"]], "10": [["10h30 Un crocodile dans mon jardin", "https://les2scenes.fr/cinema/un-crocodile-dans-mon-jardin"], ["14h Atelier Tremplin", "https://les2scenes.fr/cinema/atelier-tremplin"], ["14h30 Le Ch\u00e2teau dans le ciel", "https://les2scenes.fr/cinema/le-chateau-dans-le-ciel"], ["18h Courts m\u00e9trages de L'\u00c9t\u00e9 au cin\u00e9ma 2024", "https://les2scenes.fr/cinema/courts-metrages-de-lete-au-cinema-2024"], ["18h Le Proc\u00e8s Goldman", "https://les2scenes.fr/cinema/le-proces-goldman"], ["20h30 Courts m\u00e9trages de L'\u00c9t\u00e9 au cin\u00e9ma 2024", "https://les2scenes.fr/cinema/courts-metrages-de-lete-au-cinema-2024"], ["20h30 Le Proc\u00e8s Goldman", "https://les2scenes.fr/cinema/le-proces-goldman"]], "11": [["10h30 Les Tourouges et les Toubleus", "https://les2scenes.fr/cinema/les-tourouges-et-les-toubleus"], ["14h Atelier Tremplin", "https://les2scenes.fr/cinema/atelier-tremplin"], ["14h30 Migration", "https://les2scenes.fr/cinema/migration"], ["18h Mon ami robot", "https://les2scenes.fr/cinema/mon-ami-robot"]], "12": [["10h30 Le Petit Chat curieux (Komaneko)", "https://les2scenes.fr/cinema/le-petit-chat-curieux-komaneko"], ["14h Atelier Tremplin", "https://les2scenes.fr/cinema/atelier-tremplin"], ["18h Ratatouille", "https://les2scenes.fr/cinema/ratatouille"]], "17": [["14h Atelier Tremplin", "https://les2scenes.fr/cinema/atelier-tremplin"], ["14h30 Ratatouille", "https://les2scenes.fr/cinema/ratatouille"], ["18h Le Ch\u00e2teau dans le ciel", "https://les2scenes.fr/cinema/le-chateau-dans-le-ciel"]], "24": [["18h Courts m\u00e9trages de L'\u00c9t\u00e9 au cin\u00e9ma 2024", "https://les2scenes.fr/cinema/courts-metrages-de-lete-au-cinema-2024"], ["18h Le R\u00e8gne animal", "https://les2scenes.fr/cinema/le-regne-animal"], ["20h30 Courts m\u00e9trages de L'\u00c9t\u00e9 au cin\u00e9ma 2024", "https://les2scenes.fr/cinema/courts-metrages-de-lete-au-cinema-2024"], ["20h30 Le R\u00e8gne animal", "https://les2scenes.fr/cinema/le-regne-animal"]]}}
    next_week_shows = refine_shows_to_next_week_only(next_months_shows)
    driver.quit()
    return next_week_shows
