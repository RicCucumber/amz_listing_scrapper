from datetime import datetime
import schedule
import time
import traceback
import re


from gsheet import GoogleSheet
from foxy import Amazon
from slack import Slack

def job():
    """
    Основная функция парсинга
    для передачи ее в функцию schedule
    """
    def check_gs_data(data, pretty_list):
        """
        Проверка целостности и полноты данных
        полученных с googlesheet
        """
        if not 'values' in data or len(data['values']) == 1:
            return []
        else:
            if pretty_list:
                correct_list = []
                for each in data['values'][1:]:
                    correct_list.append(each[0].strip())
                return correct_list
            else:
                return data['values'][1:]


    def issue_notifier(data_to_upload):


        def slack_send_message(message_text, channel):
            slack = Slack('rikcucumber')
            query = 'chat.postMessage'
            method = 'post'

            params = {
                'channel': channel,
                'text': message_text,
                'as_user': False,
                'username': 'Listing_checker',
                'icon_url': 'https://www.freeiconspng.com/uploads/amazon-icon-2.png'
            }

            slack.send_api_call(api_call=query, _type=method, params=params)


        def slack_get_messages(channel):
            slack = Slack('rikcucumber')
            query = 'conversations.history'
            method = 'get'
            params = {
                'channel':channel,
            }

            response = slack.send_api_call(api_call=query, _type=method, params=params)

            if response.status_code != 200:
                print('Issue with Slack connection')
                return {'messages': []}

            return response.json()['messages']


        def check_period(message_text, period):
           """
           Достаточно ли времени прошло с момента последнего сообщения в слаке
           """
           for each in slack_mes_history:

               if message_text in each['text']:
                   message_date_time = datetime.fromtimestamp(float(each['ts']))
                   date_now = datetime.now()
                   time_delta = date_now - message_date_time
                   time_delta_minutes = time_delta.seconds // 60

                   if time_delta_minutes > int(period):
                       return True
                   else:
                       return False

           return True


        def check_rule(product, rule):
            """
            Подготовка сообщения и проверка на время с
            последней нотификахи
            """
            message = f'{product["brand"]} - {product["asin"]} - {rule["message"]} - {rule["tag"]}'

            split_mes_list = message.split(' - ')

            if len(split_mes_list) != 4:
                print(message_text)
                return False

            check_mes_text = f'{split_mes_list[0]} - {split_mes_list[1]} - {split_mes_list[2]}'
            if check_period(message_text=check_mes_text, period=rule['period']):
                return message

            return ''


        def get_image_id(iterable):
            for each in iterable:
                yield re.search(pattern=PATTERN, string=each).group(1)



        channel = 'CKH1UGQ66'
        gs = GoogleSheet(token='token_swan.pickle')
        SS = '1lTaA0MnfDcsDxI0N1fqld8-ZJKg4mZwN0sEoNX_YJ3E'
        main_data = gs.get_values(SPREADSHEET_ID=SS, RANGE_NAME='main_data')
        #historical data
        main_data = main_data['values'][1:]
        main_data.reverse()
        #master data
        master_data = gs.get_values(SPREADSHEET_ID=SS, RANGE_NAME='ASINs!A:G')
        master_data = check_gs_data(master_data, False)
        #slack messages
        slack_mes_history = slack_get_messages(channel)
        #rules dict
        rules_data = gs.get_values(SPREADSHEET_ID=SS, RANGE_NAME='Task!A:E')
        rules_data = rules_data['values'][1:]
        rules_dict = {}
        #Pattern for image id parsing
        PATTERN = 'I/(.+?)\.'

        for each in rules_data:
            rules_dict[each[0]] = {
                'period': each[2],
                'message': each[3],
                'tag': f'<{each[4]}>'
            }

        last_data = []
        for i in range(0, len(main_data)):
            if i+1 == len(main_data):
                last_data = main_data[:]
                break

            if main_data[i][17] != main_data[i+1][17]:
                last_data = main_data[:i+1]
                break

        message_list = []
        for each in data_to_upload:

            asin = each[0]
            last_data_check_asin = list(map(lambda x: asin in x, last_data))
            master_data_check_asin = list(map(lambda x: asin in x, master_data))

            if True not in master_data_check_asin:
                print(f'ASIN {asin} has been removed from master data sheet. Skip.')
                continue

            md_row = master_data[master_data_check_asin.index(True)]
            product = {
                'asin': md_row[1],
                'brand': md_row[0]
            }
            #Page does not exist notification
            if each[1] == 'Not exist':
                message_list.append(check_rule(product=product, rule = rules_dict['PAGE_STATUS']))
                continue

            #EBC/Description issue
            if each[7] == '' and each[8] == '':
                message_list.append(check_rule(product=product, rule = rules_dict['EBC/DESCRIPTION']))

            #Title indexing
            if asin not in title_index_skip_list:
                if each[3] == 'problem':
                    message_list.append(check_rule(product=product, rule = rules_dict['TITLE_INDEX']))

            #Bullets indexing
            if 'problem' in each[6]:
                message_list.append(check_rule(product=product, rule = rules_dict['BULLETS_INDEX']))

            #Description indexing
            if asin not in description_index_skip_list:
                if 'problem' in each[9]:
                    message_list.append(check_rule(product=product, rule = rules_dict['DESCRIPTION_INDEX']))

            #BuyBox missing
            if each[11] == 'False':
                message_list.append(check_rule(product=product, rule = rules_dict['BUYBOX']))

            #Check if asin in skip list
            if not asin in rating_skip_list:
                #Low Rating
                if float(each[13]) < 3.8:
                    message_list.append(check_rule(product=product, rule = rules_dict['RATING_TOTAL']))

            if not asin in review_skip_list:
                #Top Ratings
                for each_star in each[15].split('/'):
                    if float(each_star) < 4:
                        message_list.append(check_rule(product=product, rule = rules_dict['REVIEW_TOP']))
                        break

            #Image change notifications
            md_image_list = list(get_image_id(md_row[5].split('\n')))
            image_list = list(get_image_id(each[4].split('\n')))
            for img in image_list:
                if not img in md_image_list:
                    message_list.append(check_rule(product=product, rule = rules_dict['IMAGES']))
                    break

            #Bullet change notification
            if each[5] != md_row[4] and md_row[4] != 'no_info':
                message_list.append(check_rule(product=product, rule = rules_dict['BULLETS']))

            #Category change notification
            if each[10] != md_row[6] and md_row[6] != 'no_info':
                message_list.append(check_rule(product=product, rule = rules_dict['CATEGORY']))

            if True in last_data_check_asin:
                last_asin_row = last_data[last_data_check_asin.index(True)]

                #Title change notification
                if each[2] != last_asin_row[2]:
                    message_list.append(check_rule(product=product, rule = rules_dict['PRODUCT_TITLE']))

                #Price change
                if each[14] != last_asin_row[14]:
                    message_list.append(check_rule(product=product, rule = rules_dict['PRICE']))

                #Reviews reduced
                if int(each[12].replace(',', '')) < int(last_asin_row[12].replace(',', '')):
                    message_list.append(check_rule(product=product, rule = rules_dict['REVIEW_QUANTITY']))

                #Rating reduced
                if float(each[13]) < float(last_asin_row[13]):
                    message_list.append(check_rule(product=product, rule = rules_dict['RATING_DECREASE']))

        if len(message_list) != message_list.count(''):
            messages_string = '\n'.join(message_list)
            slack_send_message(message_text=messages_string, channel=channel)
        else:
            text = 'So far so good :smiley:'
            if check_period(message_text=text, period=360):
                slack_send_message(message_text=text, channel=channel)

    print('Start scrapping...')
    gs = GoogleSheet(token='token_swan.pickle')
    amazon_scraper = Amazon('com', 'chrome')

    SS = '1lTaA0MnfDcsDxI0N1fqld8-ZJKg4mZwN0sEoNX_YJ3E'
    R_MAIN = 'main_data'
    #list of asins
    asin_data = gs.get_values(SPREADSHEET_ID=SS, RANGE_NAME='ASINs!B:B')
    asin_data = check_gs_data(asin_data, True)
    if asin_data == []:
        print('No asins to scrape. Exit')
        exit()

    #get last row
    main_data = gs.get_values(SPREADSHEET_ID=SS, RANGE_NAME=R_MAIN)
    last_range = len(main_data['values'])

    #bullets index exceptions
    bullet_data = gs.get_values(SPREADSHEET_ID=SS, RANGE_NAME='ASINs!J:J')
    exception_bullets_list = check_gs_data(bullet_data, True)

    #rating alert skip
    rating_skip_data = gs.get_values(SPREADSHEET_ID=SS, RANGE_NAME='ASINs!I:I')
    rating_skip_list = check_gs_data(rating_skip_data, True)

    #review alert skip
    review_skip_data = gs.get_values(SPREADSHEET_ID=SS, RANGE_NAME='ASINs!K:K')
    review_skip_list = check_gs_data(review_skip_data, True)

    #title index alert skip
    title_index_skip_data = gs.get_values(SPREADSHEET_ID=SS, RANGE_NAME='ASINs!L:L')
    title_index_skip_list = check_gs_data(title_index_skip_data, True)

    #description indexing alert skip
    description_index_skip_data = gs.get_values(SPREADSHEET_ID=SS, RANGE_NAME='ASINs!M:M')
    description_index_skip_list = check_gs_data(description_index_skip_data, True)

    #ASIN scrape skip list
    scrape_skip_data = gs.get_values(SPREADSHEET_ID=SS, RANGE_NAME='ASINs!N:N')
    scrape_skip_list = check_gs_data(scrape_skip_data, True)

    data_to_upload = []
    #amazon_scraper.enable_headless()
    amazon_scraper.run()
    #amazon_scraper.choose_location('75201')
    #time.sleep(1)

    for asin in asin_data:
        if asin in scrape_skip_list: continue
        try:
            data_to_upload.append(amazon_scraper.parse_listing_lxml(asin, exception_bullets_list))
        except Exception as e:
            traceback.print_exc()
            return ''
    amazon_scraper.close()

    try:
        issue_notifier(data_to_upload)
    except Exception as e:
        traceback.print_exc()
        input('Wait to continue...')

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    timestamp_lst = [tuple([timestamp])]
    timestamp_lst *= len(data_to_upload)

    try:
        gs = GoogleSheet(token='token_swan.pickle')
        gs.update_values(values=data_to_upload, SPREADSHEET_ID=SS, RANGE_NAME=f'{R_MAIN}!A{last_range+1}')
        gs.update_values(values=timestamp_lst, SPREADSHEET_ID=SS, RANGE_NAME=f'{R_MAIN}!R{last_range+1}')
    except:
        time.sleep(5)
        gs = GoogleSheet(token='token_swan.pickle')
        gs.update_values(values=data_to_upload, SPREADSHEET_ID=SS, RANGE_NAME=f'{R_MAIN}!A{last_range+1}')
        gs.update_values(values=timestamp_lst, SPREADSHEET_ID=SS, RANGE_NAME=f'{R_MAIN}!R{last_range+1}')

    print(f'{timestamp} - {len(data_to_upload)} ASIN have been parsed.')
    print('Sleep for 30 min...')

"""
interval_minutes = int(input('Please, enter parsing interval in minutes...\n'))
schedule.every(interval_minutes).minutes.do(job)
while True:
    schedule.run_pending()
    time.sleep(1)
"""
if __name__ == '__main__':
    job()
