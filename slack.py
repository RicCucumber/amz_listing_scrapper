import configparser
import requests
from pathlib import Path


basic_path = Path(__file__).parent

class Slack:

    def __init__(self, user):
        self.user = user
        self.token = self.read_config()
        self.params = {'token': self.token}


    def read_config(self):
        config = configparser.ConfigParser()
        config.read(str(basic_path / 'config.ini'))
        return config[self.user]['token']


    def send_api_call(self, api_call, _type, params=''):
        self.params.update(params)

        if _type == 'get':
            return requests.get(url=f'https://slack.com/api/{api_call}', params=self.params)
        elif _type == 'post':
            return requests.post(url=f'https://slack.com/api/{api_call}', params=self.params)
        else:
            return ''
