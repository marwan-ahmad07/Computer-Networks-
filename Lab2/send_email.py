# Send Email using SMTP
# Computer Networks Lab 2

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import ssl
import socket


def send_email(sender_email, sender_password, recipient_email, subject, body, smtp_server=None, smtp_port=None):
    # Send email using SMTP
    # Returns True if successful, False if failed
    
    # Auto-detect server if not provided
    if smtp_server is None:
        smtp_server = get_smtp_server(sender_email)
    
    if smtp_port is None:
        smtp_port = 587  # Standard port for SMTP with TLS
    
    try:
        print(f"Preparing to send email...")
        print(f"From: {sender_email}")
        print(f"To: {recipient_email}")
        print(f"Subject: {subject}")
        print(f"Server: {smtp_server}:{smtp_port}")
        
        # Create email message
        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = recipient_email
        message['Subject'] = subject
        message.attach(MIMEText(body, 'plain'))
        
        # Setup SSL
        context = ssl.create_default_context()
        
        print(f"Connecting to server...")
        
        # Connect and send
        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            print(f"Starting encryption...")
            server.starttls(context=context)
            
            print(f"Logging in...")
            server.login(sender_email, sender_password)
            
            print(f"Sending...")
            server.send_message(message)
            
        print(f"Email sent successfully!")
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("ERROR: Wrong email or password")
        print("For Gmail, use App Password instead of regular password")
        return False
        
    except smtplib.SMTPConnectError:
        print(f"ERROR: Cannot connect to {smtp_server}:{smtp_port}")
        print("Check your internet connection")
        return False
        
    except socket.gaierror:
        print(f"ERROR: Cannot find SMTP server '{smtp_server}'")
        print(f"The email domain may not be valid or server name is wrong")
        print(f"Try manually specifying the SMTP server")
        return False
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False


def get_smtp_server(email):
    # Get SMTP server based on email domain
    domain = email.split('@')[1].lower()
    
    # Known email providers
    smtp_servers = {
        'gmail.com': 'smtp.gmail.com',
        'yahoo.com': 'smtp.mail.yahoo.com',
        'outlook.com': 'smtp-mail.outlook.com',
        'hotmail.com': 'smtp-mail.outlook.com',
        'live.com': 'smtp-mail.outlook.com',
        'ethereal.email': 'smtp.ethereal.email',
    }
    
    if domain in smtp_servers:
        return smtp_servers[domain]
    
    # Try standard format for unknown domains
    return f'smtp.{domain}'


def main():
    # Test the send email function
    print("=" * 60)
    print("EMAIL SENDER - SMTP Protocol")
    print("=" * 60)
    print()
    
    # Get email info from user
    sender_email = input("Enter your email address: ").strip()
    sender_password = input("Enter your password: ").strip()
    recipient_email = input("Enter recipient's email address: ").strip()
    subject = input("Enter email subject: ").strip()
    
    print("\nEnter email body (type END on a new line when done):")
    body_lines = []
    while True:
        line = input()
        if line.upper() == "END":
            break
        body_lines.append(line)
    
    body = "\n".join(body_lines)
    
    # Optional custom server
    print("\nSMTP Server Configuration:")
    print("Leave blank to auto-detect based on your email domain")
    print("Examples: smtp.gmail.com, smtp.mail.yahoo.com, smtp-mail.outlook.com, smtp.mail.tm")
    custom_server = input("Custom SMTP server (press Enter to skip): ").strip()
    smtp_server = custom_server if custom_server else None
    
    if smtp_server:
        try:
            smtp_port = int(input("SMTP port (default 587): ").strip() or "587")
        except ValueError:
            smtp_port = 587
    else:
        smtp_port = None
    
    print("\n" + "=" * 60)
    
    # Send the email
    success = send_email(sender_email, sender_password, recipient_email, 
                        subject, body, smtp_server, smtp_port)
    
    print("=" * 60)
    
    if success:
        print("\n✓ Email sent!")
    else:
        print("\n✗ Failed to send email")


if __name__ == "__main__":
    main()
