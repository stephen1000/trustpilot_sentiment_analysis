""" Scraping subcategories from trustpilot """

from bs4 import BeautifulSoup
from selenium import webdriver

from settings import BASE_URL, CHROME_OPTIONS


def get_subcategories():
    # we just need to get the html on this page, so we'll close our browser as soon as we get it.
    browser = webdriver.Chrome(options=CHROME_OPTIONS)
    browser.get(BASE_URL + "/categories")
    html = browser.page_source
    browser.close()

    # We parse the page source to find the first 'section' tag, which is where the subcategory cards are located.
    soup = BeautifulSoup(html, features="lxml")
    subcategory_section = soup.find_all("section")[0]

    # can either use category or subcategory, seems subcategory may have overlap,
    # but also give us smaller chunks to work with (probably easier to start/stop)
    subcategory_links = set()

    for subcategory in subcategory_section.children:
        new_links = get_element_links(subcategory)
        # the first link in each subcategory is to the category, so discard
        subcategory_links.update(new_links[1:])

    return subcategory_links


def get_element_links(element):
    """ Fetches the href attribute of all a tags on an element """
    links = element.find_all("a")
    # we just want the href attribute (where the tag links to), so we parse those out with a list comprehension
    return [link.attrs.get("href") for link in links]


if __name__ == "__main__":
    # if we're running this directly, we see what subcategories we've found.
    subcategory_links = get_subcategories()
    print("\n".join(subcategory_links))
