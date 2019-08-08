import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pathlib import Path


basic_path = Path(__file__).parent

class GoogleSheet:


    def __init__(self, token):
        self.token = token
        self.service = self.build_service()


    def build_service(self):
        if os.path.exists(basic_path / self.token):
            with open(basic_path / self.token, 'rb') as token:
                creds = pickle.load(token)
            return build('sheets', 'v4', credentials=creds)
        else:
            print('No token, please check')
            exit()


    def get_values(self, SPREADSHEET_ID, RANGE_NAME):
        sheet = self.service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                                    range=RANGE_NAME).execute()
        return result


    def update_values(self, values, SPREADSHEET_ID, RANGE_NAME):
        body = {
            'values': values
        }
        result = self.service.spreadsheets().values().update(spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME, valueInputOption='RAW', body=body).execute()


    def clear_range(self, SPREADSHEET_ID, RANGE_NAME):
        sheet = self.service.spreadsheets()
        result = sheet.values().clear(spreadsheetId=SPREADSHEET_ID,
                                    range=RANGE_NAME).execute()

    def clear_sheet(self, spreadsheet_id, sheet_id):
        requests = [
            {'updateCells': {'range': {'sheetId': sheet_id}, 'fields': '*'}}
        ]

        body = {
            'requests': requests
        }

        sheet = self.service.spreadsheets()
        response = sheet.batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
        return response
