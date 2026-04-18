import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

def send_quote_email(to_email: str, customer_name: str, pdf_path: str, quote_id: str):
    gmail_user = os.getenv('GMAIL_USER')
    gmail_pass = os.getenv('GMAIL_APP_PASSWORD')

    if not gmail_user or not gmail_pass:
        raise ValueError('GMAIL_USER und GMAIL_APP_PASSWORD müssen in der .env gesetzt sein.')

    msg = MIMEMultipart()
    msg['From']    = f'Die Nordmänner <{gmail_user}>'
    msg['To']      = to_email
    msg['Subject'] = f'Ihr Angebot #{quote_id} – Die Nordmänner'

    body = f"""Sehr geehrte(r) {customer_name},

vielen Dank für Ihre Anfrage bei Die Nordmänner!

Im Anhang finden Sie Ihr persönliches Angebot (Nr. {quote_id}).
Das Angebot ist 14 Tage gültig. Mit einem Klick auf den Buchungslink im PDF können Sie direkt buchen — wir melden uns anschließend zur Terminbestätigung.

Bei Fragen stehen wir Ihnen gerne zur Verfügung:
  📧  info@dienordmaenner.com
  📞  +49 (0) 123 456 789
  🕐  Mo–Fr 07:00–19:00 Uhr

Mit freundlichen Grüßen,
Ihr Team der Nordmänner"""

    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    with open(pdf_path, 'rb') as f:
        part = MIMEApplication(f.read(), Name=f'Angebot_{quote_id}.pdf')
        part['Content-Disposition'] = f'attachment; filename="Angebot_{quote_id}.pdf"'
        msg.attach(part)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as srv:
        srv.login(gmail_user, gmail_pass)
        srv.send_message(msg)
