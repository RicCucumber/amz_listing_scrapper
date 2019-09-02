from collections import namedtuple
import lxml.html
import time
from datetime import datetime

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
import urllib.parse

from scraper.scraper import SeleniumScraper

class AmazonBotListing(SeleniumScraper):

    fields = [
        'asin',
        'page_status',
        'product_title',
        'product_title_indexing',
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
        'stars_string',
        'report_date'
    ]

    parse_result = namedtuple('parse_result', field_names=fields, defaults=['']*len(fields))

    def __init__(self, headless=False):
        SeleniumScraper.__init__(self, headless)
        self.main_url = 'https://www.amazon.com'
        self.report_date = datetime.now()
        self.exception_bullets_list = []


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

        #REFACTORING
        # result_list = []
        # for each in search_list:
        #     check_sponsored = each.xpath('.//span[@class="a-size-base a-color-secondary" and contains(text(), "Sponsored")]')
        #     if len(check_sponsored) == 0:
        #         result_list.append(each.get('data-asin'))

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
        #REFCATORING
        # for each in tag_bullets:
        #     bullet_text = each.text.strip()
        #     if bullet_text != '':
        #         bullets_list.append(bullet_text)
        bullets_string = '\n'.join(bullets_list)

        #EBC and Description
        description_text = ''
        try:
            ebc_content = page_to_parse.xpath('//div[@class="aplus-v2 desktop celwidget"]//div//text()')
            ebc_list = [each.strip() for each in ebc_content if each and each.strip() != 'Read more']
            #REFACTORING
            # for each in ebc_content:
            #     ebc_text = each.strip()
            #     if ebc_text and ebc_text != 'Read more':
            #         ebc_list.append(ebc_text)

            ebc_string = ' '.join(ebc_list)

        except NoSuchElementException:
            ebc_string = ''

        if not ebc_string:
            description_tag = page_to_parse.xpath('//div[@id="productDescription"]/*[not(self::div)]//text()')
            description_list = [each.strip() for each in description_tag]
            description_text = ' '.join(description_list)
            #Part of the description's text for indexing
            #Disabled. TODO - realized another logic to check description's indexing
            # description_p_text_list = page_to_parse.xpath('//div[@id="productDescription"]//p/text()')
            # description_index_list = [each.strip() for each in description_p_text_list]

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
        review_quantity = review_block.xpath('.//h2[@data-hook="total-review-count"]/text()')[0].split(' ')[0]
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

        #REFACTORING
        # price = page_to_parse.xpath('//span[@id="priceblock_ourprice"]/text()')
        # if len(price) == 0:
        #     price = page_to_parse.xpath('//span[@id="priceblock_saleprice"]/text()')
        #     if len(price) == 0:
        #         price = 'Currently unavailable'
        #     else:
        #         price = price[0]
        # else:
        #     price = price[0]

        #top reviews
        top_reviews_stars = ''
        top_reviews = page_to_parse.xpath('//div[@data-hook="top-customer-reviews-widget"]/div[@data-hook="review"]')
        star_xpath = './/i[@data-hook="review-star-rating"]/span/text()'
        stars_list = [review.xpath(star_xpath)[0].split(' ')[0] for review in top_reviews]
        stars_string = '/'.join(stars_list)

        # REFACTORING
        # if len(top_reviews) > 0:
        #     star_list = []
        #     for each in top_reviews:
        #         star_list.append(each.xpath('.//i[@data-hook="review-star-rating"]/span/text()')[0].split(' ')[0])
        #     stars_string = '/'.join(star_list)
        # else:
        #     stars_string = ''

        #images
        image_tag = page_to_parse.xpath('//div[@id="main-image-container"]/ul/li[contains(@class, "itemNo")]')
        image_xpath = './/img/@src'
        image_list = [each.xpath(image_xpath)[0] for each in image_tag]
        images_string = '\n'.join(image_list)

        #REFACTORING
        # if len(image_container) > 0:
        #     for each in image_container:
        #         #link = each.xpath('.//img/@src')[0]
        #         #image_list.append(link.split('_')[0] + link.split('.')[-1:][0])
        #         image_list.append(each.xpath('.//img/@src')[0])
        #     images_string = '\n'.join(image_list)
        # else:
        #     images_string = ''

        #Check indexing for product title
        product_title_indexing = self.__lxml_check_indexing(product_title)

        #Check bullet indexing
        bullets_index_list = [self.__lxml_check_indexing(each)
            if each and each not in self.exception_bullets_list
            else
            ''
            for each in bullets_list
        ]

        bullets_index_string = '\n'.join(bullets_index_list)

        #REFACTORING
        # bullet_index_list = []
        # for each in bullets_list:
        #     if each and not each in self.exception_bullets_list:
        #         bullet_index_list.append(self.__lxml_check_indexing(each))
        #     else:
        #         bullet_index_list.append('')


        #Check indexing for product description
        if description_text:
            text_to_index = ''
            #product_description_indexing = __lxml_check_indexing(product_description[150:250])
            for description_index in description_list:
                if description_index != '':
                    text_to_index = text_to_index + description_index
                    description_indexing = self.__lxml_check_indexing(text_to_index)

                    if description_indexing == 'ok':
                        break
                    if len(text_to_index) > 255:
                        break
        else:
            description_indexing = ''

        return self.parse_result(asin, self.page_status, product_title, product_title_indexing, images_string,
                bullets_string, bullets_index_string, ebc_string, description_text, description_indexing,
                category, buybox, review_quantity, rating, price, stars_string, str(self.report_date))


a = AmazonBotListing(headless=False)
with a as bot:
    asin = 'B07MSLMX1J'
    data = bot.scrape_listing(asin=asin)
print(data)
