# Notes on scraping the reviews

Things did not go as smoothly as they could have.

## How I thought the scraping would go

1. use selenium to get ~20 categories
2. use those to get a ~100 companies per category
3. use those to get ~100 reviews per company

That comes out to 200k total requests. Call it 50ms per request, puts us at like
150 minutes to get everything more or less. Sadly, this is not at all how it went...

## What I actually did

So the first thing I realized when grabbing the reviews was that there's a whole,
whole lot of them. Like tens of thousands for some companies. Also, you can only
view 20 per request. That's about an order of magnitude more requests than I had
anticipated, and Selenium just has way too much overhead for that.

The only thing selenium was providing that I wasn't able to get w/ requests was the
categories (which i thought would be easy to get on the company page... oops), but 
those are easy enough to backfill from [scrape/get_companies.py](get_companies.py)
if I really decide they're necessary.

So if I scrap categories, I can use requests instead of selenium. This is way way
way faster, but still not fast enough. It would have taken several days to get all
the reviews that way, and I'm trying to knock this out in a weekend, so that's a
nonstarter. 

## Speeding things up

One of the easiest ways to get a performance boost when dealing with network calls
is to go async, since most of the time it takes to get a response is spent waiting.
Parrallelizing (which I promise to misspell in many new and exciting ways) lets us
start new requests while the old ones are waiting.

## Why you always need a dead-letter queue

So some messages may not actually get processed. They may be malformed messages,
or rely on resources that are no longer present. Either way, if you don't clear
them out of your SQS queue, they'll just float around forever, being attempted by
whatever lambda you hooked up to it.