"""
This module is a web scrapper for the Petit Kursaal cinema in Besançon.
"""

import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from unidecode import unidecode


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
    geckodriver_path = "/cinema/geckodriver"
    service = Service(geckodriver_path)
    driver = webdriver.Firefox(service=service, options=firefox_options)

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


def get_shows():
    """
    Get the shows from the Petit Kursaal cinema in Besançon.
    """
    driver, soup = _init_web_browser()
    current_month = _get_calendar_header_element(soup, "jsCalendar-title-name")
    movies_result = _fetch_movies_from_the_current_month(driver, soup, current_month)

    soup = _load_next_month(driver)

    movies_result |= _fetch_movies_from_the_current_month(driver, soup, _get_next_month(current_month))
    print(movies_result)

    # todo: fetch info for each movie from its URL, then build the final dict...

    driver.quit()
