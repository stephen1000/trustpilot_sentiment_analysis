"""
So, the lambda timed out on some of the bigger scripts, plus some of the abnormal pages.
This will identify which companies from companies.txt we're missing in ./reviews
"""

import os

from glob import glob

# fetch all csvs in the reviews folder
reviews_dir = os.path.join(".", "reviews", "*.csv")
reviews = glob(reviews_dir)
# I replaced / w/ __ in the lambda, so we've got to undo that here
reviews = [
    review.replace("__", "/").replace(".\\reviews\\", "/review/").replace(".csv", "")
    for review in reviews
]

companies_path = os.path.join(".", "scrape", "companies.txt")
with open(companies_path) as f:
    companies = f.read().split("\n")

missing = set(companies) - set(reviews)

print(len(missing))

with open('missing_companies.txt','w') as f:
    f.write('\n'.join(missing))


