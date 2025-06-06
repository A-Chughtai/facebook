from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

class FollowupSheetsHandler:
    def __init__(self, credentials_file="credentials.json"):
        self.credentials = Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
        self.client = gspread.authorize(self.credentials)
        self.followups_sheet = self.client.open_by_key(os.getenv("FOLLOWUPS_SHEET_ID"))
        self.worksheet = self.followups_sheet.sheet1
        
        # Ensure headers exist
        headers = self.worksheet.row_values(1)
        if not headers:
            self.worksheet.append_row([
                'id', 'user_id', 'username', 'phone_number', 'post_url',
                'followup_date', 'message', 'status', 'created_at',
                'last_message_date', 'user_replied'
            ])
    
    def add_followup(self, user_id: str, username: str, phone_number: str, 
                    post_url: str, followup_date: datetime, message: Optional[str] = None, 
                    last_message_date: Optional[datetime] = None) -> bool:
        """Add a new follow-up entry to the Google Sheet"""
        try:
            # Get all records to determine new ID
            all_records = self.worksheet.get_all_records()
            new_id = 1 if not all_records else max(int(record['id']) for record in all_records) + 1
            
            # Handle None values and ensure proper data types
            phone_number = str(phone_number) if phone_number is not None else ""
            message = str(message) if message is not None else ""
            last_message_date = last_message_date or datetime.now()
            
            # Prepare new row
            new_row = [
                str(new_id),
                str(user_id),
                str(username),
                phone_number,
                str(post_url),
                followup_date.strftime('%Y-%m-%d %H:%M:%S'),
                message,
                'pending',
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                last_message_date.strftime('%Y-%m-%d %H:%M:%S'),
                'FALSE'  # user_replied as string for Google Sheets
            ]
            
            # Append new row
            self.worksheet.append_row(new_row)
            return True
        except Exception as e:
            print(f"Error adding follow-up to Google Sheet: {str(e)}")
            return False
    
    def get_pending_followups(self) -> List[Dict]:
        """Get all pending follow-ups that were scheduled one day ago or more and user hasn't replied"""
        try:
            all_records = self.worksheet.get_all_records()
            today = datetime.now().date()
            one_day_ago = today - timedelta(days=1)
            
            # Convert string dates to datetime objects
            for record in all_records:
                record['followup_date'] = datetime.strptime(record['followup_date'], '%Y-%m-%d %H:%M:%S').date()
                record['created_at'] = datetime.strptime(record['created_at'], '%Y-%m-%d %H:%M:%S').date()
                record['user_replied'] = record['user_replied'].lower() == 'true'
            
            # Filter for pending follow-ups
            pending = [
                record for record in all_records
                if (record['status'] == 'pending' and
                    record['created_at'] <= one_day_ago and
                    not record['user_replied'])
            ]
            
            # Update status for replied follow-ups
            for record in all_records:
                if record['user_replied'] and record['status'] == 'pending':
                    cell = self.worksheet.find(str(record['id']))
                    if cell:
                        self.worksheet.update_cell(cell.row, 8, 'cancelled')  # Update status column
            
            return pending
        except Exception as e:
            print(f"Error processing follow-ups: {str(e)}")
            return []
    
    def mark_followup_completed(self, followup_id: int) -> bool:
        """Mark a follow-up as completed"""
        try:
            cell = self.worksheet.find(str(followup_id))
            if cell:
                self.worksheet.update_cell(cell.row, 8, 'completed')  # Update status column
                return True
            return False
        except Exception as e:
            print(f"Error updating follow-up status: {str(e)}")
            return False
    
    def delete_followup(self, followup_id: int) -> bool:
        """Delete a follow-up entry"""
        try:
            cell = self.worksheet.find(str(followup_id))
            if cell:
                self.worksheet.delete_row(cell.row)
                return True
            return False
        except Exception as e:
            print(f"Error deleting follow-up: {str(e)}")
            return False
    
    def get_all_followups(self) -> List[Dict]:
        """Get all follow-ups with their creation timestamps"""
        try:
            all_records = self.worksheet.get_all_records()
            # Convert string dates to datetime objects
            for record in all_records:
                record['created_at'] = datetime.strptime(record['created_at'], '%Y-%m-%d %H:%M:%S')
                record['followup_date'] = datetime.strptime(record['followup_date'], '%Y-%m-%d %H:%M:%S')
            return all_records
        except Exception as e:
            print(f"Error reading follow-ups: {str(e)}")
            return [] 