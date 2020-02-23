"""
So, figuring out which companies were inactive was easiest to do by running the script w/
a logging statement, which is how I generated ``inactive_companies.txt``. Not super
replicable, but sacrifices must be made.

This removes inactive companies from missing companies. Yes this would be faster
with set comprehensions, but meh, still runs fast enough.
"""

import os


inactive_path = os.path.join('scrape/inactive_companies.txt')
with open(inactive_path) as f:
    inactive = f.read().split('\n')

missing_path = os.path.join('scrape/missing_companies.txt')
with open(missing_path) as f:
    missing = f.read().split('\n')

actually_missing = set(missing) - set(inactive)

with open(missing_path, 'w') as f:
    f.write('\n'.join(actually_missing))
