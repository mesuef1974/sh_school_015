Twilio Sandbox & Webhook Setup - Quick Guide

1. Create a Twilio account: https://www.twilio.com/
2. In Console -> Messaging -> Try it out -> WhatsApp Sandbox, follow instructions to join the sandbox from your phone.
3. Set the Incoming messages webhook URL to: https://<your-domain>/api/whatsapp/webhook/
   - Twilio sends POST form-encoded fields: From, To, Body, MessageSid, etc.
4. For production, apply for WhatsApp Business API access or use a provider (WATI/Vonage).
5. Example Twilio reply using twilio-python:
   from twilio.rest import Client
   client = Client(account_sid, auth_token)
   message = client.messages.create(body='Hello', from_='whatsapp:+14155238886', to='whatsapp:+974XXXXXXXX')
6. Secure your webhook: verify requests, use HTTPS, and HMAC signature check.
7. Test locally using ngrok to expose local webhook to Twilio during development.
