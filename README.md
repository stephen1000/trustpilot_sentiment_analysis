# Trustpilot Sentiment Analysis app

Inspired by/following:
https://medium.com/swlh/end-to-end-machine-learning-from-data-collection-to-deployment-ce74f51ca203

This is a mini webapp that will run on AWS Lambda + Vue.js to do live sentiment analysis of reviews.

I'm doing some fairly significant deviations from the article above, because I like the added challenge
of not having anything I could just copy/paste if/when I get stuck.

## Why am I doing this?

Because machine learning, especially sentiment analysis, seems super cool and I want to try it out.

I also haven't done any good ol' fashioned selenium scraping in a while, so I'm taking this as an
opportunity to do some quick and some good scraping.

Since this is a project where I'm trying a bunch of different stuff, the requirements.txt is a mess.
I **highly** reccomend using a [virtual environment](https://docs.python.org/3/library/venv.html)
if you're going to clone this.

## Scraping

The trustpilot structure goes:

Subcategory > Company (paged) > Reviews (paged)

I'm tackling this by getting urls for each subcategory ([get_subcategories.py](scrape/get_subcategories.py)),
then getting a **set** of company urls w/in each subcategory ([get_companies.py](scrape/get_companies.py)),
and finally getting all the reviews for each company ([get_reviews.py](scrape/get_reviews.py)).

## Deviations from the article

1. I'm not using scrapy (I'm not a fan of it)
2. Aside from looking at what features are in the dataset, I'm doing the scraping on my own.

- I'm a bit concerned that the article's author has duplicate reviews in their dataset,
  since companies can belong to multiple categories. This could cause issues by reinforcing
  scores for those duplicate reviews
- Ok so I may have regretted not using scrapy... but I did get a cool opportunity to use lambda + sqs
  to chew through all the companies (except some went > 15min... still working on that)

3. I'm going to try to use tensorflow for the ML part. Again, this is personal preference.
4. I'm including my collected data in source control. If you're just interested in trying the ML
   part of this experiment, then there's no need to scrape trustpilot yourself. **actually that
   seems like a bad idea so I'm not doing it now**
