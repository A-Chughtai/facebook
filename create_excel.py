import pandas as pd
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_excel_structure():
    # Create db directory if it doesn't exist
    os.makedirs("db", exist_ok=True)
    
    # Create social_media.xlsx
    social_media_path = os.getenv("EXCEL_PATH", "db/social_media.xlsx")
    posts_df = pd.DataFrame(columns=[
        'id',
        'user_id',
        'username',
        'post_id',
        'post_text',
        'post_url',  # Added post URL column
        'message_sent',
        'wa_no'  # WhatsApp number column
    ])
    posts_df.to_excel(social_media_path, index=False)
    print("Social media Excel file structure created successfully!")
    print(f"File location: {social_media_path}")
    print("\nColumns created:")
    for col in posts_df.columns:
        print(f"- {col}")
    
    # Create followups.xlsx
    followups_path = "db/followups.xlsx"
    followups_df = pd.DataFrame(columns=[
        'id',
        'user_id',
        'username',
        'phone_number',
        'post_url',  # Added post URL column
        'followup_date',
        'message',
        'status',  # 'pending' or 'completed'
        'created_at',  # When the follow-up was created
        'last_message_date'  # When the user was last messaged
    ])
    followups_df.to_excel(followups_path, index=False)
    print("\nFollow-ups Excel file structure created successfully!")
    print(f"File location: {followups_path}")
    print("\nColumns created:")
    for col in followups_df.columns:
        print(f"- {col}")

if __name__ == "__main__":
    create_excel_structure() 