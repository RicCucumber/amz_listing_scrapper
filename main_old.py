from gsheet import GoogleSheet
from foxy import Amazon
from slack import Slack
from datetime import datetime
import schedule
import time
import traceback


def job():


    def check_gs_data(data, pretty_list):

        if not 'values' in data or len(data['values']) == 1:
            return []
        else:
            if pretty_list:
                correct_list = []
                for each in data['values'][1:]:
                    correct_list.append(each[0])
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


        def too_many_time(message_text):
            """
            Достаточно ли времени прошло с момента последнего сообщения в слаке
            Добавить динамическую переменную из google sheet!!!
            """
            for each in slack_mes_history:

                if message_text in each['text']:
                    message_date_time = datetime.fromtimestamp(float(each['ts']))
                    date_now = datetime.now()
                    time_delta = date_now - message_date_time
                    time_delta_hours = time_delta.seconds // 3600
                    time_delta_days = time_delta.days
                    if time_delta_days > 0:
                        return True
                    else:
                        return False

            return True


        channel = 'CL0LU9K54'
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

        for each in rules_data:
            rules_dict[each[0]] = {
                'period': each[2],
                'message': each[3],
                'tag': f'<!{each[4]}>'
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

            #Page does not exist notification
            if each[1] == 'Not exist':
                notification_text = f'{asin} - NOT_PAGE_!!! - <!channel>'
                if too_many_time(notification_text): message_list.append(notification_text)
                continue

            #EBC/Description issue
            if each[7] == '' and each[8] == '':
                notification_text = f'{asin} - NOT_EBC & NOT_DESCRIPTION - <!channel>'
                if too_many_time(notification_text): message_list.append(notification_text)

            #Title indexing
            if asin not in title_index_skip_list:
                if each[3] == 'problem':
                    notification_text = f'{asin} - NOT_TITLE_INDEX - <!channel>'
                    message_list.append(notification_text)

            #Bullets indexing
            if 'problem' in each[6]:
                notification_text = f'{asin} - NOT_BULLETS_INDEX - <!channel>'
                if too_many_time(notification_text): message_list.append(notification_text)

            #Description indexing
            if 'problem' in each[9]:
                notification_text = f'{asin} - NOT_DESCRIPTION_INDEX - <!channel>'
                if too_many_time(notification_text): message_list.append(notification_text)

            #BuyBox missing
            if each[11] == 'False':
                notification_text = f'{asin} - NOT_BUYBOX_!!! - <!channel>'
                message_list.append(notification_text)

            #Skip asin's rating check
            if not asin in rating_skip_list:
                #Low Rating
                if float(each[13]) < 3.8:
                    notification_text = f'{asin} - LOW_RATING - <!channel>'
                    if too_many_time(notification_text): message_list.append(notification_text)

            if not asin in review_skip_list:
                #Top Ratings
                for each_star in each[15].split('/'):
                    if float(each_star) < 4:
                        notification_text = f'{asin} - LOW_REVIEW - <!channel>'
                        message_list.append(notification_text)
                        break


            if True in master_data_check_asin:
                md_row = master_data[master_data_check_asin.index(True)]

                #Image change notifications
                md_image_list = md_row[5].split('\n')
                image_list = each[4].split('\n')
                for img in image_list:
                    if not img in md_image_list:
                        notification_text = f'{asin} - NOT_IMAGE - <!channel>'
                        if too_many_time(notification_text): message_list.append(notification_text)

                #Bullet change notification
                if each[5] != md_row[4] and md_row[4] != 'no_info':
                    notification_text = f'{asin} - NOT_BULLETS - <!channel>'
                    if too_many_time(notification_text): message_list.append(notification_text)

                #Category change notification
                if each[10] != md_row[6] and md_row[6] != 'no_info':
                    notification_text = f'{asin} - OTHER_CATEGORY - <!channel>'
                    if too_many_time(notification_text): message_list.append(notification_text)

            if True in last_data_check_asin:
                last_asin_row = last_data[last_data_check_asin.index(True)]

                #Title change notification
                if each[2] != last_asin_row[2]:
                    notification_text = f'{asin} - NOT_PRODUCT_TITLE - <!channel>'
                    if too_many_time(notification_text): message_list.append(notification_text)

                #Price change
                if each[15] != last_asin_row[15]:
                    print(each[15], last_asin_row[15])
                    notification_text = f'{asin} - PRICE_CHANGED - <!channel>'
                    message_list.append(notification_text)

                #Reviews reduced
                if int(each[12].replace(',', '')) < int(last_asin_row[12].replace(',', '')):
                    notification_text = f'{asin} - REVIEWS_REDUCED - <!channel>'
                    message_list.append(notification_text)

                #Rating reduced
                if float(each[13]) < float(last_asin_row[13]):
                    notification_text = f'{asin} - MINUS_RATING - <!channel>'
                    if too_many_time(notification_text): message_list.append(notification_text)

        messages_string = '\n'.join(message_list)
        slack_send_message(message_text=messages_string, channel=channel)

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

    data_to_upload = []
    #amazon_scraper.enable_headless()
    amazon_scraper.run()
    amazon_scraper.choose_location('90001')
    time.sleep(1)
    for asin in asin_data:
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


interval_minutes = int(input('Please, enter parsing interval in minutes...\n'))
schedule.every(interval_minutes).minutes.do(job)
while True:
    schedule.run_pending()
    time.sleep(1)
