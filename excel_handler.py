import pandas as pd
import os
from datetime import datetime

class ExcelHandler:
    def __init__(self, file_path="db/social_media.xlsx"):
        self.file_path = file_path
        self.ensure_file_exists()
    
    def ensure_file_exists(self):
        """Create Excel file with proper schema if it doesn't exist"""
        if not os.path.exists(self.file_path):
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            
            # Create DataFrame with schema
            df = pd.DataFrame(columns=[
                'id',
                'user_id',
                'username',
                'post_id',
                'post_text',
                'post_url',
                'message_sent',
                'wa_no'  # WhatsApp number column
            ])
            
            # Save to Excel
            df.to_excel(self.file_path, index=False)
    
    def get_unanswered_posts(self):
        """Get all posts where message_sent is 0"""
        try:
            df = pd.read_excel(self.file_path)
            return df[df['message_sent'] == 0].to_dict('records')
        except Exception as e:
            print(f"Error reading Excel file: {str(e)}")
            return []
    
    def mark_message_sent(self, post_id):
        """Mark a post as message sent"""
        try:
            df = pd.read_excel(self.file_path)
            df.loc[df['id'] == post_id, 'message_sent'] = 1
            df.to_excel(self.file_path, index=False)
            return True
        except Exception as e:
            print(f"Error updating Excel file: {str(e)}")
            return False
    
    def add_post(self, user_id, username, post_id, post_text, post_url=None, wa_no=None):
        """Add a new post to the Excel file"""
        try:
            df = pd.read_excel(self.file_path)
            
            # Generate new ID
            new_id = 1 if df.empty else df['id'].max() + 1
            
            # Create new row
            new_row = {
                'id': new_id,
                'user_id': user_id,
                'username': username,
                'post_id': post_id,
                'post_text': post_text,
                'post_url': post_url,
                'message_sent': 0,
                'wa_no': wa_no
            }
            
            # Append new row
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            
            # Save to Excel
            df.to_excel(self.file_path, index=False)
            return True
        except Exception as e:
            print(f"Error adding post to Excel file: {str(e)}")
            return False
    
    def update_whatsapp_number(self, post_id, wa_no):
        """Update WhatsApp number for a post"""
        try:
            df = pd.read_excel(self.file_path)
            df.loc[df['id'] == post_id, 'wa_no'] = wa_no
            df.to_excel(self.file_path, index=False)
            return True
        except Exception as e:
            print(f"Error updating WhatsApp number: {str(e)}")
            return False
    
    def get_all_posts(self):
        """Get all posts from the Excel file"""
        try:
            return pd.read_excel(self.file_path).to_dict('records')
        except Exception as e:
            print(f"Error reading Excel file: {str(e)}")
            return [] 