import re  # yeah things are about to get weird
import os

from bs4 import BeautifulSoup
from retry import retry
from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    InvalidSessionIdException,
    NoSuchElementException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from get_subcategories import get_subcategories
from settings import BASE_URL, CHROME_OPTIONS, BASE_DIR


@retry(ElementClickInterceptedException, tries=10, delay=0.5)
def keep_clicking(browser, element):
    """ Click a few times, ignoring interception, and scrolling down each time """
    browser.find_element_by_tag_name("body").send_keys(Keys.ARROW_DOWN)
    element.click()


def get_companies():
    """
    Each subcategory has a number of companies, listed in pages of 20 at a time. We'll crawl through each page, adding to
    our set of company links all the entries on a page.

    We're using a set here because companies can be repeated between categories/subcategories.
    """
    subcategory_links = get_subcategories()
    company_links = set()

    browser = webdriver.Chrome(options=CHROME_OPTIONS)

    for subcategory_link in subcategory_links:
        # url is going to be used in case our sessionID gets invalidated by the site and we need to resume with a fresh
        # session. It gets updated each time we go to a new subcategory, or a new page w/in the subcategory
        url = BASE_URL + subcategory_link

        # this gives us a fresh browser in the event our session ID gets invalidated, and points it to the url we were at
        try:
            browser.get(url)
        except InvalidSessionIdException:
            browser = webdriver.Chrome(options=CHROME_OPTIONS)
            browser.get(url)

        # this lets us use the scroll action (later, when we're trying to click the next button)
        actions = ActionChains(browser)

        # So, i'm about to do the unspeakable: using regex on html. It's ok to take a few minutes and just bask in the
        # horror of this code, but there's some name munging going on and this cleans it up. This will break if, for
        # some goddamn reason the content we want embeds data in there, but that's not the case now (nor do i forsee it
        # ever becoming the case), so forgive me.

        # also i'm only doing this to the class attributes, as that's all i need for effective scraping here.

        # also yeah i know it's still janky as hell.

        while True:
            
            # get the content of the current page into some tasty soup
            html = browser.page_source
            name_demangler_pattern = r"\bclass=\"(.+?)___.+?\""
            name_demangler_replace = r'class="\1"'
            demangled_html = re.sub(
                name_demangler_pattern, name_demangler_replace, html
            )

            soup = BeautifulSoup(demangled_html, features="lxml")
            
            # get the container w/ all the links we want
            container = soup.find(attrs={"class": "businessUnitCardsContainer"})

            try:
                # get all the a tags in here, and then add their hrefs to our set of links
                company_elements = container.find_all("a", attrs={"class": "wrapper"})
                company_links.update(
                    [element.attrs.get("href") for element in company_elements]
                )
            except AttributeError:
                # if we try to access something here, it means we didn't get the element we wanted.
                # that's ok, we just need to continue as normal
                pass

            try:
                # So the "next page" button sometimes gets covered by this span that hovers over it
                # to counteract that, we are going to scroll to the button, then keep trying to click it
                # with the keep_clicking method above, which hits an "arrow down" button after each attempt,
                # so we eventually move down far enough we can click it
                next_button = browser.find_element_by_link_text("Next page")
                actions.move_to_element(next_button)
                keep_clicking(browser, next_button)
                url = browser.current_url
            except NoSuchElementException:
                # If there's no "Next Page" button, then we've gotten all the links for this subcategory
                break

        # Always close your browsers!
        browser.close()

    return company_links


if __name__ == "__main__":
    # If we're running this script directly, we will refresh our company list.
    company_links = get_companies()
    with open(os.path.join(BASE_DIR, "companies.txt"), "w") as f:
        f.write('\n'.join(company_links))
