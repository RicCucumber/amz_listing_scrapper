from selenium import webdriver

class SeleniumScraper:
    def __init__(self, headless):
        self.opts = webdriver.ChromeOptions()
        self.opts.add_argument('--start-maximized')
        if headless: self.opts.add_argument('--headless')
        # self.browser = webdriver.Chrome(executable_path=r'D:\github\amz_listing_scrapper_test\scraper\chromedriver.exe', options=self.opts)
        # return self
    def __enter__(self):
        self.browser = webdriver.Chrome(executable_path=r'D:\github\amz_listing_scrapper_test\scraper\chromedriver.exe', options=self.opts)
        return self

    def __exit__(self, *execp):
        self.browser.quit()
