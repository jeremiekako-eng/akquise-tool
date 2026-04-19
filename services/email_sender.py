import os
import resend

def send_quote_email(to_email: str, customer_name: str, pdf_path: str, quote_id: str):
    resend.api_key = os.getenv('RESEND_API_KEY')
    if not resend.api_key:
        raise ValueError('RESEND_API_KEY fehlt in den Umgebungsvariablen.')

    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()

    resend.Emails.send({
        'from': 'Die Nordmänner <info@dienordmaenner.com>',
        'to': [to_email],
        'bcc': ['info@dienordmaenner.com'],
        'reply_to': 'info@dienordmaenner.com',
        'subject': f'Ihr Angebot #{quote_id} – Die Nordmänner',
        'html': f"""
        <div style="font-family:Inter,sans-serif;max-width:600px;margin:0 auto;background:#f7f8fa;padding:32px;border-radius:12px">
          <div style="background:#0d1b2a;padding:24px;border-radius:10px;margin-bottom:24px">
            <h1 style="color:#e8a020;margin:0;font-size:1.5rem">Die Nordmänner</h1>
            <p style="color:#8a9bb0;margin:4px 0 0">Spedition &amp; Transport</p>
          </div>
          <h2 style="color:#1a1a2e">Ihr Angebot #{quote_id}</h2>
          <p style="color:#444;line-height:1.7">Sehr geehrte(r) <strong>{customer_name}</strong>,<br><br>
          vielen Dank für Ihre Anfrage! Im Anhang finden Sie Ihr persönliches Angebot.<br><br>
          Das Angebot ist <strong>14 Tage gültig</strong>. Mit dem Buchungslink im PDF können Sie direkt buchen — wir melden uns anschließend zur Terminbestätigung.</p>
          <div style="background:#fff;border:1px solid #e0e0e0;border-radius:10px;padding:20px;margin:24px 0">
            <p style="margin:0;color:#444"><strong>📧</strong> info@dienordmaenner.com<br>
            <strong>📞</strong> +49 (0) 123 456 789<br>
            <strong>🕐</strong> Mo–Fr 07:00–19:00 Uhr</p>
          </div>
          <p style="color:#8a9bb0;font-size:.85rem">Mit freundlichen Grüßen,<br>Ihr Team der Nordmänner</p>
        </div>
        """,
        'attachments': [{
            'filename': f'Angebot_{quote_id}.pdf',
            'content': list(pdf_bytes),
        }]
    })
