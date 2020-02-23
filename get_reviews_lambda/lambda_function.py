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
import re
import time
from dataclasses import asdict, dataclass
from itertools import cycle, zip_longest
from io import StringIO

import requests
from bs4 import BeautifulSoup
import boto3

s3 = boto3.client("s3")
BASE_URL = "https://trustpilot.com"
BASE_DIR = os.path.dirname(__file__)
S3_BUCKET = os.environ.get("S3_BUCKET")


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
    company_review_count: int
    company_rating: int
    company_categories: str
    review_rating: int
    review_title: str
    review_body: str

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
        "Excellent": 5,
        "Great": 4,
        "Average": 3,
        "Poor": 2,
        "Bad": 1,
        "": 0,
    }

    @staticmethod
    def remove_whitespace(string: str):
        """ Strip unwanted characters out of a string """
        return re.sub(r"\s", "", string)

    @staticmethod
    def replace_breaks(string: str, replace_char=" "):
        """ Replace line breaks with ``replace_char`` """
        return string.replace("\n", replace_char).replace("\r", replace_char)

    def __init__(self):
        self.soup = None

    def get(self, url: str):
        """ 
        1-  Sets the ``self.url`` to ``url``
        2-  Fetches a url with ``self.soup``, resetting ``retries`` times if an invalid sessionID is found, 
            if the soup isn't pointed at the current page already
        """
        response = requests.get(BASE_URL + url)
        self.soup = BeautifulSoup(response.text, features="html.parser")
        return response

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
        header = self.soup.find(attrs={"class": "header-section"})
        name = header.find(attrs={"class": "multi-size-header__big"}).text
        name = self.replace_breaks(name)

        # The subheader has a bunch of spaces in its body that we don't need, and i feel like there might be commas
        # in the review count, but i haven't found anything w/ 1k reviews so i'm just being cautious.
        subheader_text = header.find(attrs={"class": "header--inline"}).text
        subheader_text = subheader_text.replace(",", "")
        subheader_text = self.replace_breaks(subheader_text)
        subheader_text = self.remove_whitespace(subheader_text)

        # this is just assigns review_count to the first half and rating to the second
        review_count, rating = tuple(subheader_text.split("•"))
        rating = self.rating_map.get(rating, None)

        categories = ""  # [link.text for link in category_holder.find_all("a")]

        return Company(
            url=company_url,
            name=name,
            categories=categories,
            review_count=int(review_count),
            rating=rating,
        )

    def get_reviews(self, company_url: str) -> list:
        """ Populate a list of reviews from ``company_url`` """
        self.get(company_url)

        reviews = list()

        while True:
            review_elements = self.soup.find_all(attrs={"class": "review"})

            for review_element in review_elements:

                # title and body can be found by class name
                title = review_element.find(
                    attrs={"class": "review-content__title"}
                ).text
                title = self.replace_breaks(title)
                # Sometimes there's no review body, so we'll pass '' instead
                body = review_element.find(attrs={"class": "review-content__text"})
                if not body:
                    body = ""
                else:
                    # newlines in the body break the csv file and aren't necessary for this anyways, so we'll
                    # replace them with spaces.
                    body = body.text
                    body = self.replace_breaks(body)

                rating_img = review_element.find(attrs={"class": "star-rating"}).find(
                    "img"
                )
                rating = int(
                    rating_img.attrs["src"].split("/")[-1].replace(".svg", "")[-1]
                )

                reviews.append(
                    Review(
                        company_url=company_url, title=title, body=body, rating=rating,
                    )
                )

            company_url, next_page = self.go_to_next_page(company_url)
            if not next_page:
                break

        return reviews

    def go_to_next_page(self, url: str):
        """ 
        Attempts to click the "next page" button, returning ``True`` if successful or ``False`` otherwise.

        Retries ``retries`` times.
        """
        parts = url.split("?page=")
        if len(parts) == 1:
            url = url + "?page=2"
        else:
            page = int(parts[-1])
            url = f"{parts[0]}?page={page+1}"
        response = self.get(url)

        if response.url.endswith(url):
            # We would have gotten redirected if we were out of pages, so we want to parse this page if we're at the
            # url we thought we'd be at.
            return url, True
        return url, False

    def save_reviews_for_company(self, company_url: str) -> list:
        """ Saves the reviews for a company in save_dir"""

        reviews = self.get_company_reviews(company_url)
        headers = list(reviews[0].as_dict().keys())

        f = StringIO()
        writer = csv.DictWriter(f, headers)
        writer.writeheader()
        writer.writerows([review.as_dict() for review in reviews])

        return f


crawler = CompanyPageCrawler()


def lambda_handler(event, context):
    """ process an aws event """
    url = event["Records"][0]["body"]
    try:
        review_body = crawler.save_reviews_for_company(url)
        file_name = "reviews/" + url.replace("/review/", "").replace("/", "__") + ".csv"
        s3.put_object(Bucket=S3_BUCKET, Key=file_name, Body=review_body.getvalue())

        return {"status": 200, "response": "nailed it"}
    except Exception as e:
        return {"status": 500, "response": repr(e)}

