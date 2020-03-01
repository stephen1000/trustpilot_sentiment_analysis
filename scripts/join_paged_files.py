"""
So I've got a bunch of pages of downloaded information, now I need to join them
together to make a set of complete files.

They're all named <url>?page=<page>.csv, so we gan do some glob magic to get
everything together.
"""
from csv import DictReader, DictWriter
import os
from glob import glob
from urllib.parse import unquote, quote

HEADERS = [
    "company_url",
    "company_name",
    "company_review_count",
    "company_rating",
    "company_categories",
    "review_rating",
    "review_title",
    "review_body",
]


def get_company_files(company):
    """ fetches each filename for paged files """
    pattern = os.path.join("bits", "reviews", company + "*.csv")
    return {_ for _ in glob(pattern)}


def save_company(company):
    """ Create a file for the joined company file and populate it """
    new_file = os.path.join("bits", "joined", f"{company.replace('/','%2F')}.csv")

    with open(new_file, "w", encoding="utf-8", newline="") as f:
        writer = DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()

    for page_file in get_company_files(company):
        with open(page_file, encoding="utf-8") as f:
            reader = DictReader(f, fieldnames=HEADERS)
            next(reader)  # discard header row
            rows = []
            try:
                for row in reader:
                    rows.append(row)
            except Exception as e:
                print(repr(e))
        with open(new_file, "a", encoding="utf-8", newline="") as f:
            writer = DictWriter(f, fieldnames=HEADERS)
            writer.writerows(rows)


def main():
    """ Save all the things """
    company_file = os.path.join("scrape", "missing_companies.txt")
    with open(company_file, encoding="utf-8") as f:
        companies = [_.replace("/review/", "").replace("\n", "") for _ in f.readlines()]

    for company in companies:
        save_company(company)


if __name__ == "__main__":
    main()
