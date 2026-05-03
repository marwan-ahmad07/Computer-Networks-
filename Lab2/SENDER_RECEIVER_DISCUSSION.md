# Sender and Receiver Discussion Guide

## Scope
This guide focuses only on:
- send_email.py (SMTP sender)
- receive_email.py (IMAP receiver)

It excludes GUI details.

---

## 1) Sender Module: send_email.py

### Main Purpose
The sender module sends an email from one account to another using SMTP with TLS encryption.

### Function 1: send_email(sender_email, sender_password, recipient_email, subject, body, smtp_server=None, smtp_port=None)

#### Inputs
- sender_email: address of the sender account
- sender_password: account password or app password
- recipient_email: destination email address
- subject: mail subject header
- body: plain text content
- smtp_server: optional custom SMTP host
- smtp_port: optional custom port

#### Internal Flow
1. Server and port setup:
   - If smtp_server is missing, it auto-detects from sender domain using get_smtp_server.
   - If smtp_port is missing, it defaults to 587.

2. MIME message construction:
   - Creates a multipart message container.
   - Sets headers: From, To, Subject.
   - Attaches body as plain text.

3. Secure network session setup:
   - Builds TLS context using ssl.create_default_context.
   - Opens SMTP connection with timeout=10 seconds.

4. Protocol sequence:
   - starttls: upgrades connection to encrypted TLS channel.
   - login: authenticates with sender credentials.
   - send_message: transmits the email.

5. Return value:
   - Returns True if successful.
   - Returns False if any handled exception occurs.

#### Exceptions handled
- SMTPAuthenticationError: wrong credentials or app password requirement.
- SMTPConnectError: unable to connect to server or port.
- socket.gaierror: DNS/hostname resolution failure.
- Generic exception: catches other runtime errors.

### Function 2: get_smtp_server(email)

#### Purpose
Resolves SMTP host based on email domain.

#### Logic
1. Extracts domain from email after @ symbol.
2. Checks known domain-to-server map:
   - gmail.com -> smtp.gmail.com
   - yahoo.com -> smtp.mail.yahoo.com
   - outlook.com/hotmail.com/live.com -> smtp-mail.outlook.com
   - ethereal.email -> smtp.ethereal.email
3. For unknown domains, applies convention smtp.domain.

### Function 3: main()

#### Purpose
CLI test runner for manual sending.

#### Behavior
- Collects sender, password, recipient, subject.
- Reads multiline body until user types END.
- Allows optional manual SMTP host and port.
- Calls send_email and prints success/failure.

---

## 2) Receiver Module: receive_email.py

### Main Purpose
The receiver module connects to a mailbox through IMAP over SSL, fetches the latest message, parses it, and returns structured details.

### Function 1: receive_latest_email(user_email, user_password, imap_server=None, imap_port=None)

#### Inputs
- user_email: mailbox login email
- user_password: mailbox password or app password
- imap_server: optional custom IMAP host
- imap_port: optional custom IMAP port

#### Internal Flow
1. Server and port setup:
   - Auto-detect server if not provided using get_imap_server.
   - Default port is 993 (IMAP over SSL).

2. Secure IMAP connection:
   - Creates SSL context.
   - Opens IMAP4_SSL session to server.

3. Authentication and mailbox selection:
   - login with credentials.
   - select INBOX.

4. Latest email retrieval:
   - Reads total number of messages from select response.
   - If zero, logs out and returns None.
   - fetches message with sequence number equal to total count.

5. Parsing and output:
   - Converts RFC822 bytes into email.message object.
   - Calls extract_email_details for structured fields.
   - Calls display_email for formatted console print.
   - logout and return details dictionary.

#### Return value
- Dictionary with from, subject, date, body on success.
- None on failure or empty inbox.

#### Exceptions handled
- imaplib.IMAP4.error: authentication/protocol-level IMAP failure.
- socket.gaierror: DNS/server not found.
- Generic exception: all other runtime issues.

### Function 2: get_imap_server(email)

#### Purpose
Resolves IMAP host from email domain.

#### Logic
1. Extracts domain.
2. Uses known map:
   - gmail.com -> imap.gmail.com
   - yahoo.com -> imap.mail.yahoo.com
   - outlook.com/hotmail.com/live.com -> outlook.office365.com
   - ethereal.email -> imap.ethereal.email
3. Unknown domains fallback to imap.domain.

### Function 3: extract_email_details(email_message)

#### Purpose
Normalizes key fields from parsed email object.

#### Extracted fields
- from: decoded sender header
- subject: decoded subject header
- date: raw date header
- body: parsed text body

### Function 4: decode_email_header(header)

#### Purpose
Decodes encoded words in headers (for non-ASCII names and subjects).

#### Logic
- Uses decode_header to split parts.
- For byte parts, decodes with declared encoding or UTF-8 fallback.
- Ignores decode errors to prevent crash.
- Concatenates all parts into one readable string.

### Function 5: get_email_body(email_message)

#### Purpose
Extracts readable body text from simple or multipart email.

#### Logic
1. If multipart:
   - Walk through parts.
   - Prefer text/plain part that is not attachment.
   - If no plain text found, keeps text/html part as fallback.
2. If single-part:
   - Decodes payload directly.
3. Returns stripped body or No body content fallback.

### Function 6: display_email(email_details)

#### Purpose
Prints email details in clean console format.

### Function 7: main()

#### Purpose
CLI test runner for manual receiving.

#### Behavior
- Reads credentials.
- Optional custom IMAP host and port.
- Calls receive_latest_email.
- Prints success/failure status.

---

## 3) Core Networking and Protocol Concepts You Should Explain

1. SMTP role:
   - SMTP is used for sending/submitting email.

2. IMAP role:
   - IMAP is used for reading and managing email on the server.

3. Why two protocols:
   - Sending and receiving are separate workflows in email systems.

4. Transport layer:
   - Both protocols run over TCP for reliable ordered delivery.

5. Port meaning:
   - 587 for SMTP submission with STARTTLS.
   - 993 for IMAP over SSL from connection start.

6. TLS security:
   - Sender upgrades plain session to TLS with STARTTLS.
   - Receiver uses IMAP4_SSL (already encrypted at connect).

7. MIME concept:
   - Email messages contain headers and body; multipart enables multiple body formats and attachments.

8. Header encoding:
   - Subjects and sender names may use encoded words to support international characters.

9. DNS resolution:
   - Hostname like smtp.gmail.com must resolve to IP; failure raises gaierror.

10. Authentication constraints:
   - Modern providers may require app passwords or OAuth methods.

---

## 4) High-Probability Viva Questions with Model Answers

1. Why did you use SMTP for sender and IMAP for receiver?
Answer: SMTP is designed for outbound message submission, while IMAP is designed for mailbox access and retrieval.

2. Why is SMTP default port set to 587?
Answer: Port 587 is the standard message submission port where STARTTLS is commonly used for encryption.

3. Why is IMAP default port set to 993?
Answer: Port 993 is standard for IMAP over SSL/TLS with encryption from the start.

4. What is STARTTLS?
Answer: It is a protocol command that upgrades an existing plain TCP SMTP session into a TLS encrypted session.

5. Why create ssl.create_default_context?
Answer: It configures secure default TLS settings including certificate validation and modern cipher preferences.

6. Why use MIMEMultipart even for plain text?
Answer: It keeps the message structure extensible for future additions like attachments or HTML alternatives.

7. How do you detect SMTP/IMAP servers automatically?
Answer: By extracting domain from email and mapping known providers; unknown domains use smtp.domain or imap.domain fallback.

8. How is latest email identified?
Answer: The code selects INBOX, reads message count, and fetches the message with the highest sequence number.

9. What happens if inbox is empty?
Answer: It returns None after clean logout and prints No emails found.

10. Why decode email headers?
Answer: Headers may be encoded with RFC-compliant schemes for non-ASCII characters, so decoding is needed for readability.

11. Why ignore decode errors in header/body parsing?
Answer: To avoid crashing on partially malformed or mixed-encoding messages and still recover readable content.

12. How are attachments avoided in body extraction?
Answer: It checks Content-Disposition and skips parts marked as attachment.

13. Why catch socket.gaierror specifically?
Answer: It indicates DNS/hostname resolution issues and allows user-friendly troubleshooting messages.

14. Why return True/False or dict/None instead of raising?
Answer: This keeps caller logic simple for UI and CLI flows where direct status handling is preferred.

15. Why include timeout in SMTP connection?
Answer: To avoid indefinite blocking when network/server is unresponsive.

16. Is login always safe with password?
Answer: It is encrypted after TLS, but account policies may still require app passwords or OAuth for better security.

17. What is RFC822 in fetch?
Answer: It requests full raw message content in standard internet message format.

18. How can this design be improved for production?
Answer: Add OAuth2, retries with backoff, robust logging, UID-based fetch, HTML sanitization, and credential vault integration.

---

## 5) Discussion of Current Limitations

1. Latest email logic uses sequence number, not UID.
2. HTML body fallback is raw and not rendered nicely.
3. Broad exception handling in parsing may hide specific bugs.
4. Password-based auth only; no OAuth2 flow.
5. Unknown domain auto-detection may fail for providers with nonstandard hostnames.

---

## 6) Strong Closing Statement for Discussion

This implementation correctly separates outbound and inbound email workflows using SMTP and IMAP, secures communication with TLS/SSL, handles MIME formatting and parsing, and provides practical error handling for authentication, DNS, and connection issues. It is a solid educational implementation of email protocol fundamentals and can be extended toward production readiness with stronger authentication, richer parsing, and mailbox indexing improvements.
