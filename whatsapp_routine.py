import os
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from send_messages import send_whatsapp_message

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

class WhatsAppRoutine:
    def __init__(self, credentials_file="credentials.json"):
        self.credentials = Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
        self.client = gspread.authorize(self.credentials)
        self.sheet = self.client.open_by_key(os.getenv("WHATSAPP_ROUTINE_SHEET_ID"))
        self.worksheet = self.sheet.sheet1

    def get_users_to_message(self):
        try:
            all_records = self.worksheet.get_all_records()
            return [record for record in all_records if str(record.get('Message_Received', '')) in ['0', '0.0', '0.00']]
        except Exception as e:
            print(f"Error reading WhatsApp routine sheet: {str(e)}")
            return []

    def run(self):
        users = self.get_users_to_message()
        count = 0
        for idx, user in enumerate(users, start=2):  # start=2 to skip header row
            name = user.get('Name', '')
            number = str(user.get('number', '')).lstrip("'")  # Remove leading '
            message = user.get('Text', '')
            if not number or not message:
                continue
            success = send_whatsapp_message(number, message)
            count += 1
        return count


def run_whatsapp_routine():
    try:
        routine = WhatsAppRoutine()
        count = routine.run()
        return count > 0
    except Exception as e:
        print(f"Error running WhatsApp routine: {str(e)}")
        return False 

def main():
    run_whatsapp_routine()

if __name__ == "__main__":
    main()