from collections import namedtuple
import lxml.html
import time
from datetime import datetime
import configparser
import re

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
import urllib.parse

from scraper.scraper import SeleniumScraper
from slack.slack import Slack
from googlesheet.gsheet import GoogleSheet



class AmazonBotListing(SeleniumScraper, Slack, GoogleSheet):

    fields = [
        'asin',
        'page_status',
        'title',
        'title_indexing',
        'images_string',
        'bullets_string',
        'bullets_indexing',
        'ebc_string',
        'description',
        'description_indexing',
        'category',
        'buybox',
        'review_quantity',
        'rating',
        'price',
        'top_reviews_rating',
        'report_date'
    ]

    parse_result = namedtuple('parse_result', field_names=fields, defaults=['']*len(fields))


    def __init__(self, headless=False, slack_user='', gs_token_path=''):
        #Inheritance __init__ from parents classes
        SeleniumScraper.__init__(self, headless)
        Slack.__init__(self, slack_user)
        GoogleSheet.__init__(self, gs_token_path)

        self.config = configparser.ConfigParser()
        self.config.read(r'D:\github\amz_listing_scrapper_test\main.ini')

        #Slack info
        self.slack_channel = self.config['slack']['channel']

        #GoogleSheet info
        self.gs_spreadsheet_id = self.config['googlesheet']['spreadsheet_id']
        self.gs_main_sheet = self.config['googlesheet']['main_sheet']
        self.gs_master_data_sheet = self.config['googlesheet']['master_data_sheet']
        self.gs_rules_sheet = self.config['googlesheet']['rule_sheet']

        #Scrapping results from main sheet
        self.main_data = self.googlesheet_values(SPREADSHEET_ID=self.gs_spreadsheet_id, RANGE_NAME=self.gs_main_sheet).get('values', [])
        self.main_sheet_last_row = len(self.main_data)
        #Get last scrapping result
        #self.last_data = [row for row in self.main_data[:] if row[17] == self.main_data[-1][17]] - Takes more time on biggest data
        if self.main_data:
            self.main_data.reverse()
            for i in range(0, len(self.main_data)):
                if self.main_data[i][17] != self.main_data[0][17]:
                    break
            self.last_data = self.main_data[:i]
        else:
            self.last_data = []


        #Master data
        self.master_data = self.googlesheet_values(SPREADSHEET_ID=self.gs_spreadsheet_id, RANGE_NAME=self.gs_master_data_sheet)
        #Generate dict -> {columns name: index}
        self.md_columns = {name: self.master_data['values'][0].index(name) for name in self.master_data['values'][0]}
        #get clear master data list
        self.master_data = self.master_data['values'][1:]
        #Generate dict -> {ASIN: Brand}
        self.asin_brand_dict = {row[self.md_columns['ASIN']]: row[self.md_columns['Brand']] for row in self.master_data}

        def exception_list(column_name):
            #Function to get exceptions list by column name in master data sheet
            #Condition len(row) >= (self.md_columns[column_name] + 1) - means rows that contain values in certain exceptin columns
            #in this case len of the row should be equal or more than (index + 1) value

            if column_name not in self.md_columns:
                return []

            return [row[self.md_columns[column_name]] for row in self.master_data if len(row) >= (self.md_columns[column_name] + 1)]

        #Get all exceptions lists
        self.asins_skip_rating_check = exception_list('Raiting - ASINs do not check')
        self.bullets_exception = exception_list('Bullets  indexing - do not check')
        self.asins_skip_reviews_check = exception_list('Reviews - do not check')
        self.asins_skip_title_check = exception_list('Titles - do not check')
        self.asins_skip_description_indexing = exception_list('Description  indexing - do not check')
        self.inactive_asins = exception_list('Inactive')

        #Notification rules data
        self.rules_data = self.googlesheet_values(SPREADSHEET_ID=self.gs_spreadsheet_id, RANGE_NAME=self.gs_rules_sheet)
        self.rules_dict = {row[0]:{'period': row[2], 'message': row[3], 'tag': row[4]} for row in self.rules_data['values'][1:]}

        self.main_url = 'https://www.amazon.com'
        self.report_date = datetime.now()


    def scrape_listing(self, asin):

        self.browser.get(f'{self.main_url}/dp/{asin}')

        #Check wrong page
        if self.browser.title == 'Page Not Found':
            return self.parse_result(asin=asin, page_status='Not exist', report_date=self.report_date)
        #Robot check
        elif self.browser.title == 'Robot Check':
            return self.parse_result(asin=asin, page_status='Issue with page load - Robot Check', report_date=self.report_date)
        else:
            self.page_status = 'ok'

        #select each image on listing to load it's url on page
        images_block = WebDriverWait(self.browser, 20).until(
                                EC.presence_of_element_located((By.XPATH, '//div[@id="altImages"]')))
        image_list = images_block.find_elements_by_xpath('.//li[@class="a-spacing-small item imageThumbnail a-declarative"]')

        for image in image_list:
            image.click()
            time.sleep(0.1)

        return self.parse_page(self.browser.page_source)


    def __lxml_check_indexing(self, text):

        def sponsored(search_item_element):

            if search_item_element.xpath('.//span[@class="a-size-base a-color-secondary" and contains(text(), "Sponsored")]'):
                return True

            return False

        select_departments = Select(self.browser.find_element_by_id('searchDropdownBox'))
        select_departments.select_by_value('search-alias=aps')

        url_search = urllib.parse.quote_plus(text)
        self.browser.get(f'{self.main_url}/s?k={url_search}')
        page_to_parse = lxml.html.fromstring(self.browser.page_source)
        search_list = page_to_parse.xpath('//div[@class="s-result-list s-search-results sg-row"]/div[contains(@class, "s-result-item")]')
        asin_list = [each.get('data-asin') for each in search_list if not sponsored(each)]

        if not asin in asin_list or asin_list.index(asin) > 11:
            return 'problem'

        return 'ok'


    def parse_page(self, page_to_parse):
        page_to_parse = lxml.html.fromstring(page_to_parse)

        #product_title
        product_title = page_to_parse.xpath('//span[@id="productTitle"]/text()')[0].strip()

        #bullets
        bullets_tag = page_to_parse.xpath('//div[@id="feature-bullets"]//ul/li/span')
        bullets_list = [each.text.strip() for each in bullets_tag if each.text.strip()]
        bullets_string = '\n'.join(bullets_list)

        #EBC and Description
        description_text = ''
        try:
            ebc_content = page_to_parse.xpath('//div[@class="aplus-v2 desktop celwidget"]//div//text()')
            ebc_list = [each.strip() for each in ebc_content if each and each.strip() != 'Read more']
            ebc_string = ' '.join(ebc_list)

        except NoSuchElementException:
            ebc_string = ''

        if not ebc_string:
            description_tag = page_to_parse.xpath('//div[@id="productDescription"]/*[not(self::div)]//text()')
            description_list = [each.strip() for each in description_tag]
            description_text = ' '.join(description_list)

        #category
        breadcrumb = page_to_parse.xpath('//div[@id="wayfinding-breadcrumbs_container"]//li//text()')
        category = ''
        for each in breadcrumb:
            category = category + each.strip().replace('\n', '').replace('\t', '') + ' '
        category = category.strip()

        #buy_box
        if page_to_parse.xpath('//div[@id="buybox"]'):
            buybox = 'True'
        else:
            buybox = 'False'


        #REVIEW BLOCK
        review_block = page_to_parse.xpath('//div[@id="reviewsMedley"]')[0]
        #review quantity
        review_quantity = review_block.xpath('.//h2[@data-hook="total-review-count"]/text()')[0].split(' ')[0].replace(',', '')
        #rating
        rating = review_block.xpath('.//span[@data-hook="rating-out-of-text"]/text()')[0].split(' ')[0]


        #possible price xpaths
        price_xpaths = [
            '//span[@id="priceblock_ourprice"]/text()',
            '//span[@id="priceblock_saleprice"]/text()'
        ]
        price = ''
        for x_path in price_xpaths:
            if page_to_parse.xpath(x_path):
                price = page_to_parse.xpath(x_path)[0]
                break

        #top reviews
        top_reviews_stars = ''
        top_reviews = page_to_parse.xpath('//div[@data-hook="top-customer-reviews-widget"]/div[@data-hook="review"]')
        star_xpath = './/i[@data-hook="review-star-rating"]/span/text()'
        stars_list = [review.xpath(star_xpath)[0].split(' ')[0] for review in top_reviews]
        stars_string = '/'.join(stars_list)

        #images
        image_tag = page_to_parse.xpath('//div[@id="main-image-container"]/ul/li[contains(@class, "itemNo")]')
        image_xpath = './/img/@src'
        image_list = [each.xpath(image_xpath)[0] for each in image_tag]
        images_string = '\n'.join(image_list)

        #Check indexing for product title
        product_title_indexing = self.__lxml_check_indexing(product_title)

        #Check bullet indexing
        bullets_index_list = [self.__lxml_check_indexing(each)
            if each and each not in self.bullets_exception
            else
            ''
            for each in bullets_list
        ]

        bullets_index_string = '\n'.join(bullets_index_list)

        #Description indexing
        def check_description_indexing(description_list):
            """
            Function to check description indexing
            The text for the index is generated by traversing the list with the addition of each subsequent element in the text

            If there is no successful result, the first element becomes the next one and the process repeats
            """
            while description_list:
                #unpacking the list into 2 parts - the first sentence and the rest (rest become a new list)
                text_to_index, *description_list = description_list
                #iterate over everything else to check indexing until the sentence is more than 300 characters
                for each in description_list:
                    if len(text_to_index) > 300:
                        #go to the next sentence as the first
                        break
                    description_indexing = self.__lxml_check_indexing(text_to_index)

                    if description_indexing == 'ok':
                        return description_indexing

                    text_to_index += ' ' + each

            return 'problem'

        description_indexing = check_description_indexing(description_list=description_list)

        return self.parse_result(asin, self.page_status, product_title, product_title_indexing, images_string,
                bullets_string, bullets_index_string, ebc_string, description_text, description_indexing,
                category, buybox, review_quantity, rating, price, stars_string, str(self.report_date))


    def slack_message_history(self):
        slack_query = 'conversations.history'
        params = {
            'channel': self.slack_channel,
        }

        response = self.slack_api_call(api_call=slack_query, _type='get', params=params)

        if response.status_code != 200:
            print('Issue with Slack')
            return {'messages': []}

        return response


    def slack_send_message(self, message_text):
        query = 'chat.postMessage'
        params = {
            channel: self.slack_channel,
            'text': message_text,
            'as_user': False,
            'username': 'Listing_checker',
            'icon_url': 'https://www.freeiconspng.com/uploads/amazon-icon-2.png'
        }

        return self.slack_api_call(api_call=query, _type='post', params=params)


    def check_rules(self, parsed_result):
        #Method to check if there is any issue with listing based on rules
        def images_compare(master_data_images, parsed_result_images):
            #TODO - add description comment
            #TODO - try to modify both list in more pythonic way
            master_data_images = master_data_images.split('\n')
            parsed_result_images = parsed_result_images.split('\n')

            PATTERN = 'I/(.+?)\.'
            master_data_images = [re.search(pattern=PATTERN, string=each).group(1) for each in master_data_images]
            parsed_result_images = [re.search(pattern=PATTERN, string=each).group(1) for each in parsed_result_images]

            for image_id in parsed_result_images:
                if image_id not in master_data_images:
                    return True

            return False


        def top_review_reduced(parsed_result_stars):
            parsed_result_stars = parsed_result_stars.split('/')
            for rating in parsed_result_stars:
                if float(rating) < 4.0:
                    return True

            return False

        #TODO - more efficient way to get rows by asin value???
        master_data_row = []
        for row in self.master_data:
            if row[1] == parsed_result.asin:
                master_data_row = row
                break

        last_data_row = []
        for row in self.last_data:
            if row[0] == parsed_result.asin:
                last_data_row = row
                break

        rules_issue = {
            'PAGE_STATUS': parsed_result.asin == 'Not exist',
            'PRODUCT_TITLE': parsed_result.title != last_data_row[2],
            'IMAGES': images_compare(master_data_row[5], parsed_result.images_string),
            'BULLETS': parsed_result.bullets_string != master_data_row[4],
            'EBC/DESCRIPTION': not parsed_result.ebc_string and not parsed_result.description,
            'TITLE_INDEX': parsed_result.title_indexing == 'problem',
            'BULLETS_INDEX': 'problem' in parsed_result.bullets_indexing,
            'DESCRIPTION_INDEX': parsed_result.description_indexing == 'problem',
            'CATEGORY': parsed_result.category != master_data_row[6],
            'BUYBOX': parsed_result.buybox == 'False',
            'PRICE': parsed_result.price != last_data_row[14],
            'REVIEW_QUANTITY': parsed_result.review_quantity < last_data_row[12].replace(',', ''),
            'RATING_TOTAL': float(parsed_result.rating) < 3.8,
            'RATING_DECREASE': float(parsed_result.rating) < float(last_data_row[13]),
            'REVIEW_TOP': top_review_reduced(parsed_result.top_reviews_rating)
        }

        return rules_issue


a = AmazonBotListing(headless=False, slack_user='main')
with a as bot:
    asin = 'B06X91Y91V'
    data = bot.scrape_listing(asin=asin)
    print(a.check_rules(data))
    a.googlesheet_update(SPREADSHEET_ID=a.gs_spreadsheet_id, RANGE_NAME=f'main_data!A{a.main_sheet_last_row+2}', values=[tuple(data)])
