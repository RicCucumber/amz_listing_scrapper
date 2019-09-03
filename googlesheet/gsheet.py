import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


class GoogleSheet:


    def __init__(self, token_path):

        def build_service():
            if os.path.exists(r'D:\github\amz_listing_scrapper_test\googlesheet\token_swan.pickle'):
                with open(r'D:\github\amz_listing_scrapper_test\googlesheet\token_swan.pickle', 'rb') as token:
                    creds = pickle.load(token)
                return build('sheets', 'v4', credentials=creds)
            else:
                print('No token, please check')
                exit()

        self.token_path = token_path
        self.service = build_service()


    def googlesheet_values(self, SPREADSHEET_ID, RANGE_NAME):
        sheet = self.service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                                    range=RANGE_NAME).execute()
        return result


    def googlesheet_update(self, values, SPREADSHEET_ID, RANGE_NAME):
        body = {
            'values': values
        }
        result = self.service.spreadsheets().values().update(spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME, valueInputOption='RAW', body=body).execute()


    def googlesheet_clear_range(self, SPREADSHEET_ID, RANGE_NAME):
        sheet = self.service.spreadsheets()
        result = sheet.values().clear(spreadsheetId=SPREADSHEET_ID,
                                    range=RANGE_NAME).execute()

    def googlesheet_clear_sheet(self, SPREADSHEET_ID, SHEET_ID):
        requests = [
            {'updateCells': {'range': {'sheetId': SHEET_ID}, 'fields': '*'}}
        ]

        body = {
            'requests': requests
        }

        sheet = self.service.spreadsheets()
        response = sheet.batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()
        return response
