import sys
from pathlib import Path
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
import time
from datetime import date
import lxml.html
import urllib.parse


class Amazon:

    def __init__(self, web_site, browser):
        self.basic_path = Path(__file__).parent
        self.url = f'https://www.amazon.{web_site}'
        self.browser = browser

        if self.browser == 'firefox':
            self.opts = webdriver.FirefoxOptions()
            self.opts.add_argument("--start-maximized")

        elif self.browser == 'chrome':
            self.opts = webdriver.ChromeOptions()
            self.opts.add_argument('--start-maximized')
            self.opts.add_argument('--mute-audio')


    def save_webpage(self):
        with open(f'{self.asin}.html', 'w') as f:
            f.write(self.browser.page_source)


    def enable_headless(self):
        self.opts.set_headless()
        assert self.opts.headless


    def run(self):
        if self.browser == 'firefox':
            self.browser = webdriver.Firefox(executable_path=str(self.basic_path / 'geckodriver.exe'), options=self.opts)
        elif self.browser == 'chrome':
            self.browser = webdriver.Chrome(executable_path=str(self.basic_path / 'chromedriver.exe'), options=self.opts)
        self.browser.get(self.url)


    def choose_location(self, index):
        try:
            address_button = WebDriverWait(self.browser,5).until(
                                    EC.element_to_be_clickable((By.XPATH, '//input[@data-action-type="SELECT_LOCATION"]')))
        except:
            address_button = WebDriverWait(self.browser,5).until(
                                    EC.element_to_be_clickable((By.XPATH, '//div[id@="nav-global-location-slot"]')))

        address_button.click()

        index_field = WebDriverWait(self.browser,5).until(
                                EC.visibility_of_element_located((By.XPATH, '//input[@id="GLUXZipUpdateInput"]')))
        index_field.send_keys(index)
        time.sleep(0.4)
        self.browser.find_element_by_xpath('//div[@id="GLUXZipInputSection"]//span[@id="GLUXZipUpdate"]//input[@aria-labelledby="GLUXZipUpdate-announce"]').click()
        time.sleep(0.4)
        self.browser.find_element_by_xpath('//div[@class="a-popover-footer"]//input[@id="GLUXConfirmClose"]').click()


    def close(self):
        self.browser.quit()


    def parse_listing_lxml(self, asin, exception_bullets_list):

        self.asin = asin
        self.exception_bullets_list = exception_bullets_list

        def __lxml_check_indexing(text_to_index):
            """
            search_input = WebDriverWait(self.browser,5).until(
                                    EC.presence_of_element_located((By.XPATH, '//input[@id="twotabsearchtextbox"]')))
            search_input.clear()
            search_input.click()
            search_input.send_keys(text_to_index)
            self.browser.find_element_by_xpath('//input[@class="nav-input"]').click()
            time.sleep(0.1)
            """
            url_search = urllib.parse.quote_plus(text_to_index)
            self.browser.get(f'{self.url}/s?k={url_search}')
            page_to_parse = lxml.html.fromstring(self.browser.page_source)
            search_list = page_to_parse.xpath('//div[@class="s-result-list s-search-results sg-row"]/div[contains(@class, "s-result-item")]')
            result_list = []
            for each in search_list:
                check_sponsored = each.xpath('.//span[@class="a-size-base a-color-secondary" and contains(text(), "Sponsored")]')
                if len(check_sponsored) == 0:
                    result_list.append(each.get('data-asin'))

            if not asin in result_list:
                return 'problem'

            if result_list.index(asin) > 11:
                return 'problem'

            return 'ok'

        #report date
        report_date = date.today()

        self.browser.get(f'{self.url}/dp/{asin}')
        print(asin)

        #check page existing
        try:
            exist_check = self.browser.title
            if exist_check == 'Page Not Found':
                page_status = 'Not exist'
                return ((asin, page_status, '', '', '', '', '', '', '', '', '', '', '', '', '', '',  ''))
            else:
                page_status = 'Exist'
        except NoSuchElementException:
            page_status = 'Not exist'
            return ((asin, page_status, '', '', '', '', '', '', '', '', '', '', '', '', '', '',  ''))

        try:
            images_block = WebDriverWait(self.browser, 20).until(
                                    EC.presence_of_element_located((By.XPATH, '//div[@id="altImages"]')))
        except:
            print('Wait too long, continue...')

        image_block = images_block.find_elements_by_xpath('.//li[@class="a-spacing-small item imageThumbnail a-declarative"]')
        for each in image_block:
            each.click()
            time.sleep(0.1)

        page_to_parse = lxml.html.fromstring(self.browser.page_source)

        #Title
        product_title = page_to_parse.xpath('//span[@id="productTitle"]/text()')[0].strip()

        #bullets
        bullets_list = []
        tag_bullets = page_to_parse.xpath('//div[@id="feature-bullets"]//ul/li/span')
        for each in tag_bullets:
            bullet_text = each.text.strip()
            if bullet_text != '':
                bullets_list.append(bullet_text)
        bullets_string = '\n'.join(bullets_list)

        #EBC
        ebc_list = []
        try:
            ebc_content = page_to_parse.xpath('//div[@class="aplus-v2 desktop celwidget"]//div//text()')
            for each in ebc_content:
                ebc_text = each.strip()
                if ebc_text != '' and ebc_text != 'Read more':
                    ebc_list.append(ebc_text)

            ebc_string = ' '.join(ebc_list)

        except NoSuchElementException:
            ebc_string = ''

        #product_description
        if ebc_string == '':
            description_list = []
            product_description = page_to_parse.xpath('//div[@id="productDescription"]/*[not(self::div)]//text()')
            if len(product_description) > 0:
                for each in product_description:
                    description_list.append(each.strip())
                product_description = ' '.join(description_list)
                description_p_text_list = page_to_parse.xpath('//div[@id="productDescription"]//p/text()')
                description_index_list = []
                for each in description_p_text_list:
                    if not each.isupper():
                        description_index_list.append(each.strip())
            else:
                product_description = ''
        else:
            product_description = ''

        #category
        breadcrumb = page_to_parse.xpath('//div[@id="wayfinding-breadcrumbs_container"]//li//text()')
        category = ''
        for each in breadcrumb:
            category = category + each.strip().replace('\n', '').replace('\t', '') + ' '
        category = category.strip()

        #buy_box
        buybox = page_to_parse.xpath('//div[@id="buybox"]')
        if len(buybox) > 0:
            buybox = 'True'
        else:
            buybox = 'False'


        #REVIEW BLOCK
        review_block = page_to_parse.xpath('//div[@id="reviewsMedley"]')[0]
        #review quantity
        review_quantity = review_block.xpath('.//h2[@data-hook="total-review-count"]/text()')[0].split(' ')[0]
        #rating
        rating = review_block.xpath('.//span[@data-hook="rating-out-of-text"]/text()')[0].split(' ')[0]


        #price-our-tag
        price = page_to_parse.xpath('//span[@id="priceblock_ourprice"]/text()')
        if len(price) == 0:
            price = page_to_parse.xpath('//span[@id="priceblock_saleprice"]/text()')
            if len(price) == 0:
                price = 'Currently unavailable'
            else:
                price = price[0]
        else:
            price = price[0]

        #top reviews
        top_reviews = page_to_parse.xpath('//div[@data-hook="top-customer-reviews-widget"]/div[@data-hook="review"]')
        if len(top_reviews) > 0:
            star_list = []
            for each in top_reviews:
                star_list.append(each.xpath('.//i[@data-hook="review-star-rating"]/span/text()')[0].split(' ')[0])
            stars_string = '/'.join(star_list)
        else:
            stars_string = ''

        #images
        image_list = []
        image_container = page_to_parse.xpath('//div[@id="main-image-container"]/ul/li[contains(@class, "itemNo")]')

        if len(image_container) > 0:
            for each in image_container:
                #link = each.xpath('.//img/@src')[0]
                #image_list.append(link.split('_')[0] + link.split('.')[-1:][0])
                image_list.append(each.xpath('.//img/@src')[0])
            images_string = '\n'.join(image_list)
        else:
            images_string = ''

        select_departments = Select(self.browser.find_element_by_id('searchDropdownBox'))
        select_departments.select_by_value('search-alias=aps')


        #Check indexing for product title
        product_title_indexing = __lxml_check_indexing(product_title)
        #Check bullet indexing
        bullet_index_list = []
        for each in bullets_list:
            if each != '' and not each in self.exception_bullets_list:
                bullet_index_list.append(__lxml_check_indexing(each))
            else:
                bullet_index_list.append('')
        bullets_index = '\n'.join(bullet_index_list)

        #Check indexing for product description

        if product_description != '':
            text_to_index = ''
            #product_description_indexing = __lxml_check_indexing(product_description[150:250])
            for description_index in description_list:
                if description_index != '':
                    text_to_index = text_to_index + description_index
                    product_description_indexing = __lxml_check_indexing(text_to_index)
                    if product_description_indexing == 'ok':
                        break
        else:
            product_description_indexing = ''

        return((asin, page_status, product_title, product_title_indexing, images_string,
                bullets_string, bullets_index, ebc_string, product_description, product_description_indexing,
                category, buybox, review_quantity, rating, price, stars_string, str(report_date)))
