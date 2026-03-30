"""
Quick Gmail test — run this to check if email sending works.
python test_email.py
"""

import smtplib
from email.mime.text import MIMEText

# ═══════════════════════════════════════
#  YOUR SETTINGS (same as server.py)
# ═══════════════════════════════════════
GMAIL_ADDRESS = "ai.mentoring.academy@gmail.com"
GMAIL_APP_PASSWORD = "glor qppu nprj kxng"   # your 16-char app password
TEST_SEND_TO = "mail.radhikakhurana@gmail.com"  # where to send the test
# ═══════════════════════════════════════

print("\n🧪 Gmail Email Test")
print("=" * 40)
print(f"From:     {GMAIL_ADDRESS}")
print(f"To:       {TEST_SEND_TO}")
print(f"Password: {'SET (' + str(len(GMAIL_APP_PASSWORD)) + ' chars)' if GMAIL_APP_PASSWORD != 'xxxx xxxx xxxx xxxx' else '❌ NOT SET'}")
print()

if GMAIL_APP_PASSWORD == "xxxx xxxx xxxx xxxx":
    print("❌ You need to set your Gmail App Password first!")
    print("   Go to: myaccount.google.com/apppasswords")
    exit()

if TEST_SEND_TO == "YOUR-PERSONAL-EMAIL@gmail.com":
    print("❌ Change TEST_SEND_TO to your real email!")
    exit()

try:
    print("Step 1: Creating test message...")
    msg = MIMEText("If you see this, email sending works! 🎉\n\nYour Holi Booth is ready to go.")
    msg["From"] = f"AI.M Academy <{GMAIL_ADDRESS}>"
    msg["To"] = TEST_SEND_TO
    msg["Subject"] = "🧪 Holi Booth Email Test"

    print("Step 2: Connecting to Gmail SMTP (smtp.gmail.com:465)...")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        print("Step 3: Logging in...")
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        print("Step 4: Sending message...")
        server.send_message(msg)
        print("Step 5: Done!")

    print(f"\n✅ SUCCESS! Check {TEST_SEND_TO} for the test email.")
    print("   (Also check spam/junk folder)")

except smtplib.SMTPAuthenticationError as e:
    print(f"\n❌ LOGIN FAILED: {e}")
    print("\nThis means your App Password is wrong. Try these fixes:")
    print("  1. Make sure you're using the APP PASSWORD, not your regular Gmail password")
    print("  2. The app password has no spaces? Try with spaces: 'abcd efgh ijkl mnop'")
    print("  3. Go to myaccount.google.com/apppasswords and create a NEW one")
    print("  4. Make sure 2-Step Verification is ON for this Google account")

except smtplib.SMTPException as e:
    print(f"\n❌ SMTP ERROR: {e}")

except ConnectionRefusedError:
    print(f"\n❌ CONNECTION REFUSED: Can't reach Gmail's servers.")
    print("   Check your internet connection.")

except Exception as e:
    print(f"\n❌ UNEXPECTED ERROR: {type(e).__name__}: {e}")