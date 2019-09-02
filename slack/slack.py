import configparser
import requests

class Slack:

    def __init__(self, slack_user):
        self.slack_user = slack_user
        self.slack_config = configparser.ConfigParser()
        self.slack_config.read(r'D:\github\amz_listing_scrapper_test\slack\slack.ini')
        self.slack_params = {
            'token': self.slack_config[self.slack_user]['token']
        }

        self.slack_request_methods = {
            'get': requests.get,
            'post': requests.post
        }

    def slack_api_call(self, api_call, _type, params=''):
        self.slack_params.update(params)
        self.slack_url = f'https://slack.com/api/{api_call}'
        try:
            return self.slack_request_methods[_type](url=self.slack_url, params=self.slack_params)
        except TypeError:
            print(f'Method {_type} does not allow')
