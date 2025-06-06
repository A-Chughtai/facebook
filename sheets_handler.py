from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

class SheetsHandler:
    def __init__(self, credentials_file="credentials.json"):
        self.credentials = Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
        self.client = gspread.authorize(self.credentials)
        self.social_media_sheet = self.client.open_by_key(os.getenv("SOCIAL_MEDIA_SHEET_ID"))
        self.worksheet = self.social_media_sheet.sheet1
        
        # Ensure headers exist
        headers = self.worksheet.row_values(1)
        if not headers:
            self.worksheet.append_row([
                'id', 'user_id', 'username', 'post_id', 'post_text', 
                'post_url', 'message_sent', 'wa_no'
            ])
    
    def get_unanswered_posts(self):
        """Get all posts where message_sent is 0"""
        try:
            all_records = self.worksheet.get_all_records()
            return [record for record in all_records if str(record['message_sent']) in ['0', '0.0', '0.00']]
        except Exception as e:
            print(f"Error reading Google Sheet: {str(e)}")
            return []
    
    def mark_message_sent(self, post_id):
        """Mark a post as message sent"""
        try:
            # Find the row with the matching post_id
            cell = self.worksheet.find(str(post_id))
            if cell:
                # Update message_sent to 1 (column G)
                self.worksheet.update_cell(cell.row, 7, '1')
                return True
            return False
        except Exception as e:
            print(f"Error updating Google Sheet: {str(e)}")
            return False
    
    def add_post(self, user_id, username, post_id, post_text, post_url=None, wa_no=None):
        """Add a new post to the Google Sheet"""
        try:
            # Get all records to determine new ID
            all_records = self.worksheet.get_all_records()
            new_id = 1 if not all_records else max(int(record['id']) for record in all_records) + 1
            
            # Prepare new row
            new_row = [
                str(new_id),
                str(user_id),
                str(username),
                str(post_id),
                str(post_text),
                str(post_url) if post_url else '',
                '0',  # message_sent
                str(wa_no) if wa_no else ''
            ]
            
            # Append new row
            self.worksheet.append_row(new_row)
            return True
        except Exception as e:
            print(f"Error adding post to Google Sheet: {str(e)}")
            return False
    
    def update_whatsapp_number(self, post_id, wa_no):
        """Update WhatsApp number for a post"""
        try:
            cell = self.worksheet.find(str(post_id))
            if cell:
                # Update wa_no (column H)
                self.worksheet.update_cell(cell.row, 8, str(wa_no))
                return True
            return False
        except Exception as e:
            print(f"Error updating WhatsApp number: {str(e)}")
            return False
    
    def get_all_posts(self):
        """Get all posts from the Google Sheet"""
        try:
            return self.worksheet.get_all_records()
        except Exception as e:
            print(f"Error reading Google Sheet: {str(e)}")
            return [] 