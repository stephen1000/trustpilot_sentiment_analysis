"""
In this script, we're going to take the list of company urls we scraped in ``get_companies`` and visit each company
site and crawl through the reviews on each page.

This will be a bit easier to do, as there's no class name mangling on the review pages. We're going to extract the
following information:

Company details:

    Name:   I chose not to grab this at previous steps, since I wanted to do the least amount of scraping

    Categories: It might be interesting to look at sentiment across categories to see if some types of companies get
                different sentiment, especially if that doesn't correlate with a different rating

    Rating: There's a span that's got the number of reviews and a word describing the rating, which should be pretty
            straightforward to parse into a number.

Review details:

    Rating: looks like this is provided as an image, which we certainly don't want to download, but luckilly the src
            attribute of the img tag includes the actual rating number, so we'll strip that out.

    Title:  This is pretty easy to grab, and could be interesting as a lighter feature than the review body.

    Body:   The text of the review. This is what we'll use for our sentiment analysis.


I'm going to try a class based approach for this one, since it'll take the longest and it'll need to be fairly robust.

"""
import csv
import os
from dataclasses import dataclass, asdict
from itertools import cycle

from selenium import webdriver
from selenium.common.exceptions import (
    InvalidSessionIdException,
    NoSuchElementException,
    ElementClickInterceptedException,
)
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import settings


@dataclass
class Company(object):
    """ A company with reviews """

    url: str
    name: str
    categories: list
    review_count: int
    rating: int


@dataclass
class Review(object):
    """ A review for a company """

    company_url: str
    title: str
    body: str
    rating: int


@dataclass
class CompanyReviews(object):
    """ The flatfile review, which will be used for sentiment analysis """

    company_url: str
    company_name: str
    company_categories: str
    company_review_count: int
    company_rating: int
    review_title: str
    review_body: str
    review_rating: int

    @classmethod
    def from_company_and_review(cls, company: Company, review: Review):
        """ Instantiates from a ``Company`` and a ``Review`` object """
        return cls(
            company_url=company.url,
            company_name=company.name,
            company_categories=",".join(company.categories),
            company_review_count=company.review_count,
            company_rating=company.rating,
            review_title=review.title,
            review_body=review.body,
            review_rating=review.rating,
        )

    def as_dict(self) -> dict:
        """ Serializes to a json/csv compatible dictionary. I just hate the default name... """
        return asdict(self)


class CompanyPageCrawler(object):
    """ A company review page on trustpilot.com """
    rating_map = {
        'Excellent': 5,
        'Great': 4,
        'Average': 3,
        'Poor': 2,
        'Bad': 1,
        '': 0,
    }

    def __init__(self):
        self._browser = None
        self.url = None

    def _get_browser(self):
        """ Generate a fresh browser, using the options found in ``settings``"""
        browser = webdriver.Chrome(options=settings.CHROME_OPTIONS)
        browser.implicitly_wait(settings.MAX_PAGE_LOAD_TIME)
        browser.get(settings.BASE_URL)
        return browser

    def _reset_browser(self):
        """ Clear out the current browser and replace it with a new one """
        try:
            self._browser.close()
        except Exception as e:
            # replace this with the actual exception raised if/when it happens
            print(repr(e))

        self._browser = self._get_browser()

        return self.browser

    @property
    def browser(self):
        """ Returns _browser, initalizing if the browser is lost """
        if not self._browser:
            self._browser = self._get_browser()
        return self._browser

    def get(self, url: str, retries=1):
        """ 
        1-  Sets the ``self.url`` to ``url``
        2-  Fetches a url with ``self.browser``, resetting ``retries`` times if an invalid sessionID is found, 
            if the browser isn't pointed at the current page already
        """
        self.url = url

        if settings.BASE_URL + url == self.browser.current_url:
            return

        try:
            self.browser.get(settings.BASE_URL + url)
        except InvalidSessionIdException:
            if retries > 0:
                self._reset_browser()
                self.get(url, retries=retries - 1)

    def get_company_reviews(self, company_url: str) -> list:
        """ Gets a list of ``CompanyReview`` for the given url """
        company = self.get_company(company_url)
        reviews = self.get_reviews(company_url)

        return [
            CompanyReviews.from_company_and_review(company, review)
            for company, review in zip(cycle([company]), reviews)
        ]

    def get_company(self, company_url: str) -> Company:
        """ Populate a company object from ``company_url`` """
        self.get(company_url)

        # The page header has the company name, and a subheader with the review count/rating
        header = self.browser.find_element_by_class_name("header-section")
        name = header.find_element_by_class_name("multi-size-header__big").text

        # The subheader has a bunch of spaces in its body that we don't need, and i feel like there might be commas
        # in the review count, but i haven't found anything w/ 1k reviews so i'm just being cautious.
        subheader_text = (
            header.find_element_by_class_name("header--inline")
            .text.replace(" ", "")
            .replace(",", "")
        )

        # this is just assigns review_count to the first half and rating to the second
        review_count, rating = tuple(subheader_text.split("•"))
        rating = self.rating_map.get(rating, None)

        category_holder = self.browser.find_element_by_class_name("categories")
        categories = [
            link.text for link in category_holder.find_elements_by_tag_name("a")
        ]

        return Company(
            url=company_url,
            name=name,
            categories=categories,
            review_count=review_count,
            rating=rating,
        )

    def get_reviews(self, company_url: str) -> list:
        """ Populate a list of reviews from ``company_url`` """
        self.get(company_url)

        reviews = list()

        while True:
            review_elements = self.browser.find_elements_by_class_name("review")

            for review_element in review_elements:

                # title and body can be found by class name
                title = review_element.find_element_by_class_name(
                    "review-content__title"
                ).text
                # Sometimes there's no review body, so we'll pass '' instead
                try:
                    body = review_element.find_element_by_class_name(
                        "review-content__text"
                    ).text
                # newlines in the body break the csv file and aren't necessary for this anyways, so we'll 
                # replace them with spaces.
                    body = body.replace('\n',' ')
                except NoSuchElementException:
                    body = ""

                # rating has to be derived from the src attribute of the rating image
                # ^ I thought that, but the alt text is much easier to parse (just need the first character)
                rating_img = self.browser.find_element_by_class_name(
                    "star-rating"
                ).find_element_by_tag_name("img")
                rating = int(rating_img.get_attribute("alt")[0])

                reviews.append(
                    Review(
                        company_url=company_url, title=title, body=body, rating=rating,
                    )
                )

            if not self.go_to_next_page():
                break

        return reviews

    def go_to_next_page(self, retries=10):
        """ 
        Attempts to click the "next page" button, returning ``True`` if successful or ``False`` otherwise.

        Retries ``retries`` times.
        """
        try:
            next_button = self.browser.find_element_by_class_name("next-page")
        except NoSuchElementException:
            return False

        actions = ActionChains(self.browser)
        actions.move_to_element(next_button)
        return self._click_next_page(next_button, retries=retries)

    def _click_next_page(self, next_button, retries=10) -> bool:
        """ 
        Attempts to click the "next page", scrolling down after each failed attempt.
        Retries ``retries`` times.
        """
        try:
            next_button.click()
        except ElementClickInterceptedException:
            # Something's blocking the button, so we scroll down and try again
            if retries > 0:
                self.browser.find_element_by_tag_name("body").send_keys(Keys.ARROW_DOWN)
                return self._click_next_page(next_button, retries=retries - 1)
        except NoSuchElementException:
            # There isn't a next page
            return False
        # There is a next page button, and we clicked it, so update our current url
        self.url = self.browser.current_url
        return True

    def save_reviews_for_company(
        self, company_url: str, save_dir: str, file_name: str
    ) -> list:
        """ Saves the reviews for a company in save_dir"""

        reviews = self.get_company_reviews(company_url)
        headers = list(reviews[0].as_dict().keys())

        with open(os.path.join(save_dir, file_name), "w", newline="", encoding='utf-8') as f:
            writer = csv.DictWriter(f, headers)
            writer.writeheader()
            writer.writerows([review.as_dict() for review in reviews])


def get_reviews(urls: list):
    """
    Write reviews for each company to a csv in scrape/reviews/<company_url>.csv

    This is so we can start/stop wherever (I'm anticipating this will take a while), or if I decide we need to go
    multithreaded (which I *really* don't want to do for this project).
    """
    crawler = CompanyPageCrawler()
    save_dir = os.path.join(settings.BASE_DIR, "reviews")
    url_count = len(urls)

    for i, url in enumerate(urls):
        print(f"Starting {url} ({i+1} of {url_count})...")
        file_name = f"{url}.csv".replace("/review/", "")
        crawler.save_reviews_for_company(url, save_dir, file_name)
        print(f"... done with {url} ({url_count-i-1} remaining)!")


if __name__ == "__main__":
    with open(os.path.join(settings.BASE_DIR, "companies.txt")) as f:
        urls_string = f.read()
    urls = urls_string.split("\n")
    get_reviews(urls)
