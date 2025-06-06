import json
import re
import time
from datetime import datetime
import argparse
from typing import List, Dict, Any
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from langchain.schema.runnable import RunnablePassthrough
import os
import sys
from dotenv import load_dotenv
from sheets_handler import SheetsHandler

# Set console encoding to UTF-8 for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv()

class PostClassification(BaseModel):
    category: str = Field(description="The category of the post: 'job' or 'spam'")
    confidence: float = Field(description="Confidence score between 0 and 1")
    reasoning: str = Field(description="Brief explanation for the classification")

class PhoneNumberExtraction(BaseModel):
    phone_numbers: List[str] = Field(description="List of WhatsApp numbers found in the text")
    confidence: float = Field(description="Confidence score between 0 and 1")

def setup_langchain():
    # Initialize Groq model
    llm = ChatGroq(
        model_name=os.getenv("GROQ_MODEL", "mixtral-8x7b-32768"),
        temperature=float(os.getenv("TEMPERATURE", "0")),
        api_key=os.getenv("GROQ_API_KEY")
    )
    
    # Create output parser for post classification
    classification_parser = PydanticOutputParser(pydantic_object=PostClassification)
    
    # Create output parser for phone number extraction
    phone_parser = PydanticOutputParser(pydantic_object=PhoneNumberExtraction)
    
    # Create prompt template for post classification
    classification_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert at classifying social media posts, specifically focused on job postings and spam detection.
        
        Your task is to analyze each post and determine if it's a legitimate job posting or spam.
        
        For legitimate job posts, look for:
        - Clear job description and requirements
        - Specific role or position mentioned
        - Professional tone and language
        - Contact information (phone, email, etc.)
        - Salary/compensation details (if mentioned)
        - Location or work arrangement details
        
        For spam posts, look for:
        - Promotional content without job details
        - Suspicious links or URLs
        - Get-rich-quick schemes
        - MLM or pyramid scheme indicators
        - Vague or overly generic job descriptions
        - Excessive use of emojis or clickbait language
        
        Provide your classification with a confidence score and brief reasoning.
        
        {format_instructions}"""),
        ("human", "Post text: {text}")
    ])
    
    # Create prompt template for phone number extraction
    phone_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert at extracting WhatsApp numbers from text. Your task is to identify all valid WhatsApp numbers in the given text.

        Guidelines:
        - Look for numbers that are likely WhatsApp numbers
        - Numbers may be in various formats (e.g., +1234567890, 1234567890, 123-456-7890)
        - Numbers should be 10-12 digits long (excluding country code)
        - Always include the country code if present
        - Format all numbers with a '+' prefix
        - Remove any spaces, dashes, or other separators
        - Provide a confidence score for each number
        
        {format_instructions}"""),
        ("human", "Text: {text}")
    ])
    
    # Create chains
    classification_chain = (
        RunnablePassthrough.assign(
            format_instructions=lambda _: classification_parser.get_format_instructions()
        )
        | classification_prompt
        | llm
        | classification_parser
    )
    
    phone_chain = (
        RunnablePassthrough.assign(
            format_instructions=lambda _: phone_parser.get_format_instructions()
        )
        | phone_prompt
        | llm
        | phone_parser
    )
    
    return classification_chain, phone_chain

def format_phone_number(phone: str) -> str:
    # Remove spaces and keep existing + if present
    if phone.startswith('+'):
        return '+' + re.sub(r'\s+', '', phone[1:])
    return '+' + re.sub(r'\s+', '', phone)

def get_processed_posts(sheets_handler):
    """Get all post IDs that have been processed"""
    posts = sheets_handler.get_all_posts()
    return {post['post_id'] for post in posts}

def process_posts(reprocess_all: bool = False):
    # Check Groq API key
    if not os.getenv("GROQ_API_KEY"):
        print("Error: GROQ_API_KEY not found in environment variables")
        return

    # Initialize LangChain
    classification_chain, phone_chain = setup_langchain()
    
    # Initialize Google Sheets handler
    sheets_handler = SheetsHandler()
    
    # Load Facebook data
    print("Loading Facebook data...")
    with open("facebook_scraped_data.json", "r", encoding="utf-8") as file:
        data = json.load(file)
    
    # Get already processed posts
    processed_posts = get_processed_posts(sheets_handler)
    print(f"Found {len(processed_posts)} already processed posts")
    
    # Filter out already processed posts
    if not reprocess_all:
        data = [post for post in data if post.get("id", "") not in processed_posts]
    
    total_posts = len(data)
    if total_posts == 0:
        print("No new posts to process!")
        return
        
    print(f"\nStarting to process {total_posts} posts...")
    print("=" * 50)
    
    start_time = time.time()
    processed_count = 0
    job_posts_count = 0
    spam_posts_count = 0
    skipped_count = 0
    
    for post in data:
        post_start_time = time.time()
        text = post.get("text", "").strip()
        user = post.get("user", {})
        fb_id = user.get("id", "N/A")
        username = user.get("name", "Unknown")
        post_id = post.get("id", "N/A")
        post_url = post.get("url", "")
        
        # Input validation
        if not text:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Skipping post {processed_count + 1}/{total_posts}")
            print(f"User: {username} (ID: {fb_id})")
            print(f"Post ID: {post_id}")
            print("Error: Post text is empty or None")
            skipped_count += 1
            processed_count += 1
            continue
            
        if post_id in processed_posts:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Skipping already processed post {processed_count + 1}/{total_posts}")
            print(f"User: {username} (ID: {fb_id})")
            print(f"Post ID: {post_id}")
            print("Post already exists in database, skipping...")
            skipped_count += 1
            processed_count += 1
            continue
        
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Processing post {processed_count + 1}/{total_posts}")
        print(f"User: {username} (ID: {fb_id})")
        print(f"Post ID: {post_id}")
        
        try:
            # Classify post using LangChain
            print("Classifying post...")
            result = classification_chain.invoke({"text": text})
            classification = result.category
            confidence = result.confidence
            reasoning = result.reasoning
            
            print(f"Classification: {classification} (Confidence: {confidence:.2f})")
            print(f"Reasoning: {reasoning}")
            
            # Skip if post is classified as spam
            if classification == 'spam':
                print("Skipping spam post...")
                spam_posts_count += 1
                processed_count += 1
                continue
            
            # Extract phone numbers using LangChain
            print("Extracting phone numbers...")
            phone_result = phone_chain.invoke({"text": text})
            phone_numbers = phone_result.phone_numbers
            
            # Format phone numbers
            formatted_numbers = [format_phone_number(num) for num in phone_numbers]
            wa_no = formatted_numbers[0] if formatted_numbers else None
            
            if wa_no:
                print(f"Found WhatsApp number: {wa_no}")
            else:
                print("No WhatsApp number found")
            
            # Add post to Google Sheets
            success = sheets_handler.add_post(
                fb_id, 
                username, 
                post_id, 
                text, 
                post_url=post_url,
                wa_no=wa_no
            )
            
            if success:
                job_posts_count += 1
                processed_count += 1
                post_time = time.time() - post_start_time
                total_time = time.time() - start_time
                avg_time = total_time / processed_count
                
                print(f"Job post stored successfully!")
                print(f"Post processed in {post_time:.2f} seconds")
                print(f"Progress: {processed_count}/{total_posts} posts ({(processed_count/total_posts)*100:.1f}%)")
                print(f"Job posts found: {job_posts_count}")
                print(f"Average time per post: {avg_time:.2f} seconds")
                print(f"Estimated time remaining: {(avg_time * (total_posts - processed_count))/60:.1f} minutes")
                print("-" * 50)
            else:
                print("Failed to store post in Google Sheets")
            
            # Add a small delay between posts
            time.sleep(1)
            
        except Exception as e:
            print(f"Error processing post: {str(e)}")
            continue
    
    total_time = time.time() - start_time
    print(f"\nProcessing completed!")
    print(f"Total time: {total_time/60:.1f} minutes")
    print(f"Total posts processed: {processed_count}")
    print(f"Posts skipped (already in database): {skipped_count}")
    print(f"Job posts found and stored: {job_posts_count}")
    print(f"Spam posts skipped: {spam_posts_count}")

    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process Facebook posts using LangChain and Groq')
    parser.add_argument('--reprocess-all', action='store_true', help='Reprocess all posts, including already processed ones')
    args = parser.parse_args()
    
    process_posts(reprocess_all=args.reprocess_all) 