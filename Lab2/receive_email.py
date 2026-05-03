# Receive Email using IMAP
# Computer Networks Lab 2

import imaplib
import email
from email.header import decode_header
import ssl
import socket


def receive_latest_email(user_email, user_password, imap_server=None, imap_port=None):
    # Fetch latest email using IMAP
    # Returns email details dict or None if failed
    
    # Auto-detect server if not provided
    if imap_server is None:
        imap_server = get_imap_server(user_email)
    
    if imap_port is None:
        imap_port = 993  # Standard port for IMAP with SSL
    
    try:
        print(f"Connecting to IMAP server...")
        print(f"Email: {user_email}")
        print(f"Server: {imap_server}:{imap_port}")
        
        # Create secure connection
        context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(imap_server, imap_port, ssl_context=context)
        
        # Login
        print(f"Logging in...")
        mail.login(user_email, user_password)
        
        # Select inbox
        print(f"Opening inbox...")
        status, messages = mail.select("INBOX")
        
        if status != "OK":
            print("ERROR: Could not open inbox")
            return None
        
        # Check number of emails
        num_messages = int(messages[0])
        print(f"Total emails: {num_messages}")
        
        if num_messages == 0:
            print("No emails found")
            mail.logout()
            return None
        
        # Fetch latest email
        print(f"Fetching latest email...")
        status, msg_data = mail.fetch(str(num_messages), "(RFC822)")
        
        if status != "OK":
            print("ERROR: Could not fetch email")
            mail.logout()
            return None
        
        # Parse email
        email_body = msg_data[0][1]
        email_message = email.message_from_bytes(email_body)
        
        # Extract details
        email_details = extract_email_details(email_message)
        
        # Display
        display_email(email_details)
        
        # Logout
        mail.logout()
        print(f"Disconnected")
        
        return email_details
        
    except imaplib.IMAP4.error as e:
        print(f"ERROR: {str(e)}")
        print("Check email and password. Gmail needs App Password")
        return None
        
    except socket.gaierror:
        print(f"ERROR: Cannot find IMAP server '{imap_server}'")
        print(f"The email domain may not be valid or server name is wrong")
        return None
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return None


def get_imap_server(email):
    # Get IMAP server based on email domain
    domain = email.split('@')[1].lower()
    
    # Known email providers
    imap_servers = {
        'gmail.com': 'imap.gmail.com',
        'yahoo.com': 'imap.mail.yahoo.com',
        'outlook.com': 'outlook.office365.com',
        'hotmail.com': 'outlook.office365.com',
        'live.com': 'outlook.office365.com',
        'ethereal.email': 'imap.ethereal.email',
    }
    
    if domain in imap_servers:
        return imap_servers[domain]
    
    # Try standard format for unknown domains
    return f'imap.{domain}'


def extract_email_details(email_message):
    # Get important info from email message
    details = {}
    
    # Get sender
    from_header = email_message.get("From", "Unknown")
    details['from'] = decode_email_header(from_header)
    
    # Get subject
    subject_header = email_message.get("Subject", "No Subject")
    details['subject'] = decode_email_header(subject_header)
    
    # Get date
    details['date'] = email_message.get("Date", "Unknown Date")
    
    # Get body
    details['body'] = get_email_body(email_message)
    
    return details


def decode_email_header(header):
    # Decode encoded email headers
    decoded_parts = decode_header(header)
    decoded_string = ""
    
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            decoded_string += part.decode(encoding or 'utf-8', errors='ignore')
        else:
            decoded_string += part
    
    return decoded_string


def get_email_body(email_message):
    # Extract body text from email (handles multipart and plain emails)
    body = ""
    
    # Check if email has multiple parts
    if email_message.is_multipart():
        for part in email_message.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            
            # Look for text content (not attachments)
            if content_type == "text/plain" and "attachment" not in content_disposition:
                try:
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    break
                except:
                    pass
            elif content_type == "text/html" and not body and "attachment" not in content_disposition:
                try:
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                except:
                    pass
    else:
        # Plain single-part email
        try:
            body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
        except:
            body = str(email_message.get_payload())
    
    return body.strip() if body else "No body content"


def display_email(email_details):
    # Print email in a nice format
    print("\n" + "=" * 60)
    print("LATEST EMAIL")
    print("=" * 60)
    print(f"From: {email_details['from']}")
    print(f"Subject: {email_details['subject']}")
    print(f"Date: {email_details['date']}")
    print("-" * 60)
    print("Body:")
    print("-" * 60)
    print(email_details['body'])
    print("=" * 60)


def main():
    # Test the receive email function
    print("=" * 60)
    print("EMAIL RECEIVER - IMAP Protocol")
    print("=" * 60)
    print()
    
    # Get credentials from user
    user_email = input("Enter your email address: ").strip()
    user_password = input("Enter your password: ").strip()
    
    # Optional custom server
    print("\nIMAP Server Configuration:")
    print("Leave blank to auto-detect based on your email domain")
    print("Examples: imap.gmail.com, imap.mail.yahoo.com, outlook.office365.com, imap.mail.tm")
    custom_server = input("Custom IMAP server (press Enter to skip): ").strip()
    imap_server = custom_server if custom_server else None
    
    if imap_server:
        try:
            imap_port = int(input("IMAP port (default 993): ").strip() or "993")
        except ValueError:
            imap_port = 993
    else:
        imap_port = None
    
    print("\n" + "=" * 60)
    
    # Fetch latest email
    result = receive_latest_email(user_email, user_password, imap_server, imap_port)
    
    if result:
        print("\n✓ Email retrieved!")
    else:
        print("\n✗ Failed to retrieve email")


if __name__ == "__main__":
    main()
