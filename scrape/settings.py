from selenium.webdriver.chrome.options import Options

# This is where we'll start our app from
BASE_URL = 'https://trustpilot.com'

# This is how our chrome browser will run
CHROME_OPTIONS = Options()
# Rendering a browser graphically is computationally expensive, and kind of annoying (pops over stuff), so we'll use a
# "headless" browser, which will just run in the background, instead of appearing as a new window. If you want to see
# the browser work, remove this option.
CHROME_OPTIONS.add_argument('--headless')