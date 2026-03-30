"""
Holi Booth — Server with Logo Overlay + Email
===============================================
1. pip install flask flask-cors openai pillow python-dotenv
2. Copy .env.example to .env and fill in your credentials
3. Save your logo as logo.png in the same folder
4. python server.py
5. Open booth.html in your browser

Gmail App Password setup:
  - Go to myaccount.google.com → search "App Passwords"
  - Enable 2-Step Verification first if needed
  - Create a new app password named "Holi Booth"
  - Copy the 16-char password into .env
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from dotenv import load_dotenv
import base64, json, os, io, smtplib, threading

load_dotenv()

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max request size

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
GMAIL_ADDRESS = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]

client = OpenAI(api_key=OPENAI_API_KEY)
emails = []
last_caricature = {}  # stores {name: image_b64} for the most recent caricature

# Load logo once at startup
LOGO = None
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")
if os.path.exists(LOGO_PATH):
    LOGO = Image.open(LOGO_PATH).convert("RGBA")
    print("✅ Logo loaded from logo.png")
else:
    print("⚠️  logo.png not found — caricatures will have text branding only")


def add_logo_to_image(caric_b64):
    """
    Overlay AI.M branded banner on caricature.
    Inspired by aimacademy.us — dark bg, logo left, bold AI.M, subtitle, URL.
    """
    img = Image.open(io.BytesIO(base64.b64decode(caric_b64))).convert("RGBA")
    w, h = img.size

    # ── Banner dimensions ──
    banner_h = int(h * 0.16)
    banner = Image.new("RGBA", (w, banner_h), (15, 15, 30, 220))

    # ── Subtle gradient accent line at top of banner ──
    accent = Image.new("RGBA", (w, 4), (0, 0, 0, 0))
    accent_draw = ImageDraw.Draw(accent)
    for x in range(w):
        r = int(255 - (255 - 255) * x / w)
        g = int(20 + (107 - 20) * x / w)
        b = int(147 - (147 - 53) * x / w)
        accent_draw.point((x, 0), fill=(r, g, b, 255))
        accent_draw.point((x, 1), fill=(r, g, b, 200))
        accent_draw.point((x, 2), fill=(r, g, b, 100))
        accent_draw.point((x, 3), fill=(r, g, b, 50))
    banner.paste(accent, (0, 0), accent)

    # ── Logo on the left ──
    pad_left = int(w * 0.03)
    if LOGO:
        logo_h = int(banner_h * 0.65)
        logo_ratio = LOGO.width / LOGO.height
        logo_w = int(logo_h * logo_ratio)
        logo_resized = LOGO.resize((logo_w, logo_h), Image.LANCZOS)
        logo_y = (banner_h - logo_h) // 2 + 2
        banner.paste(logo_resized, (pad_left, logo_y), logo_resized)
        text_start_x = pad_left + logo_w + int(w * 0.025)
    else:
        text_start_x = pad_left

    # ── Load fonts ──
    font_paths_bold = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:\\Windows\\Fonts\\arialbd.ttf",
        "arial.ttf",
    ]
    font_paths_reg = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:\\Windows\\Fonts\\arial.ttf",
        "arial.ttf",
    ]

    def load_font(paths, size):
        for p in paths:
            try:
                return ImageFont.truetype(p, size)
            except:
                continue
        return ImageFont.load_default()

    font_big = load_font(font_paths_bold, int(banner_h * 0.30))
    font_sub = load_font(font_paths_reg, int(banner_h * 0.17))
    font_url = load_font(font_paths_bold, int(banner_h * 0.15))

    # ── Draw text ──
    draw = ImageDraw.Draw(banner)
    y_top = int(banner_h * 0.12)
    draw.text((text_start_x, y_top), "AI.M", fill=(255, 255, 255, 255), font=font_big)
    aim_bbox = draw.textbbox((0, 0), "AI.M", font=font_big)
    aim_w = aim_bbox[2] - aim_bbox[0]
    draw.text(
        (text_start_x + aim_w + int(w * 0.015), y_top + int(banner_h * 0.04)),
        "Academy", fill=(255, 20, 147, 255), font=font_big
    )
    y_sub = y_top + int(banner_h * 0.38)
    draw.text(
        (text_start_x, y_sub),
        "AI Mentorship Academy  •  Real AI Education for Kids",
        fill=(180, 180, 200, 220), font=font_sub
    )
    url_text = "aimacademy.us"
    url_bbox = draw.textbbox((0, 0), url_text, font=font_url)
    url_w = url_bbox[2] - url_bbox[0]
    draw.text(
        (w - url_w - pad_left, int(banner_h * 0.65)),
        url_text, fill=(255, 107, 53, 255), font=font_url
    )

    img.paste(banner, (0, h - banner_h), banner)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    return base64.b64encode(buf.getvalue()).decode()


# ══════════════════════════════════════════════════
#  EMAIL FUNCTIONS (unchanged from v21)
# ══════════════════════════════════════════════════

def send_email_background(to_email, child_name, image_b64):
    print(f"   ⏳ Background: sending email to {to_email}...")
    success = send_email(to_email, child_name, image_b64)
    if success:
        print(f"   ✅ Background: email sent to {to_email}!")
    else:
        print(f"   ❌ Background: email to {to_email} failed — see error above")


def send_activity_email(to_email, child_name, activity_name, results_html):
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"AI.M Academy <{GMAIL_ADDRESS}>"
        msg["To"] = to_email
        msg["Subject"] = f"🧠 {child_name}'s AI Experience at AI.M Academy"

        html = f"""
        <html><body style="font-family:Arial,sans-serif;text-align:center;background:#F3E5F5;padding:20px;">
          <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:20px;padding:30px;box-shadow:0 4px 20px rgba(0,0,0,0.1);">
            <h1 style="color:#9C27B0;margin-bottom:4px;">🧠 {child_name} trained an AI!</h1>
            <p style="color:#888;font-size:14px;">At the AI.M Academy booth</p>
            <div style="background:linear-gradient(135deg,#F3E5F5,#E8EAF6);border-radius:14px;padding:20px;margin:16px 0;text-align:left;">
              {results_html}
            </div>
            <div style="background:linear-gradient(135deg,#FFF0F5,#F3E5F5);border-radius:14px;padding:20px;margin:16px 0;">
              <p style="color:#555;font-size:15px;line-height:1.6;">
                <strong style="color:#FF1493;">Your child just did real machine learning!</strong> At AI.M Academy, kids in grades 5–9 build AI projects like this and more — chatbots, image tools, recommendation systems.
              </p>
              <p style="color:#555;font-size:15px;line-height:1.6;margin-top:8px;">
                Weekend classes with only <strong>3–5 students</strong>. Personalized mentorship from AI experts.
              </p>
            </div>
            <a href="https://aimacademy.us/contact" style="display:inline-block;background:linear-gradient(135deg,#9C27B0,#E040FB);color:#fff;padding:14px 32px;border-radius:12px;text-decoration:none;font-weight:bold;font-size:16px;margin:10px 0;">Book a Free Info Session</a>
            <p style="color:#bbb;font-size:12px;margin-top:20px;">AI.M Academy — Real AI Education for Kids<br>aimacademy.us | 470-269-6906</p>
          </div>
        </body></html>
        """
        msg.attach(MIMEText(html, "html"))

        print(f"   Connecting to Gmail SMTP...")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            print(f"   Logging in as {GMAIL_ADDRESS}...")
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            print(f"   Sending message...")
            server.send_message(msg)
            print(f"   Message sent!")
        return True
    except Exception as e:
        print(f"   ❌ EMAIL ERROR: {e}")
        return False


def send_activity_email_background(to_email, child_name, activity_name, results_html):
    print(f"   ⏳ Background: sending {activity_name} email to {to_email}...")
    success = send_activity_email(to_email, child_name, activity_name, results_html)
    if success:
        print(f"   ✅ Background: {activity_name} email sent to {to_email}!")
    else:
        print(f"   ❌ Background: {activity_name} email to {to_email} failed")


def send_email(to_email, child_name, image_b64):
    """Send image email to parent — used by caricature, superhero, and 2050."""
    try:
        msg = MIMEMultipart("related")
        msg["From"] = f"AI.M Academy <{GMAIL_ADDRESS}>"
        msg["To"] = to_email
        msg["Subject"] = f"🎨 {child_name}'s AI Creation — AI.M Academy"

        html = f"""
        <html><body style="font-family:Arial,sans-serif;text-align:center;background:#FFF0F5;padding:20px;">
          <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:20px;padding:30px;box-shadow:0 4px 20px rgba(0,0,0,0.1);">
            <h1 style="color:#FF1493;margin-bottom:4px;">Happy Holi, {child_name}! 🎨</h1>
            <p style="color:#888;font-size:14px;">Here's your AI-generated creation</p>
            <img src="cid:caricature" style="width:100%;max-width:500px;border-radius:16px;margin:16px 0;border:3px solid #FF1493;" />
            <div style="background:linear-gradient(135deg,#FFF0F5,#F3E5F5);border-radius:14px;padding:20px;margin:16px 0;">
              <p style="color:#555;font-size:15px;line-height:1.6;">
                <strong style="color:#FF1493;">Did you know?</strong> This was created using AI — the same technology your child can learn to build at <strong>AI.M Academy</strong>.
              </p>
              <p style="color:#555;font-size:15px;line-height:1.6;">
                We teach kids in <strong>grades 5–9</strong> to build real AI projects — chatbots, image tools, and more. Weekend classes with only <strong>3–5 students</strong> per class.
              </p>
            </div>
            <a href="https://aimacademy.us/contact" style="display:inline-block;background:linear-gradient(135deg,#FF1493,#FF6B35);color:#fff;padding:14px 32px;border-radius:12px;text-decoration:none;font-weight:bold;font-size:16px;margin:10px 0;">Book a Free Info Session</a>
            <p style="color:#bbb;font-size:12px;margin-top:20px;">AI.M Academy — Real AI Education for Kids<br>aimacademy.us | 470-269-6906</p>
          </div>
        </body></html>
        """
        msg.attach(MIMEText(html, "html"))

        img_data = base64.b64decode(image_b64)
        img_mime = MIMEImage(img_data, _subtype="png")
        img_mime.add_header("Content-ID", "<caricature>")
        img_mime.add_header("Content-Disposition", "inline", filename=f"{child_name}_holi_creation.png")
        msg.attach(img_mime)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)

        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False


# ══════════════════════════════════════════════════
#  EXISTING ENDPOINTS (unchanged from v21)
# ══════════════════════════════════════════════════

@app.route("/analyze", methods=["POST"])
def analyze():
    d = request.json
    try:
        resp = client.chat.completions.create(
            model="gpt-4o", max_tokens=500,
            messages=[{"role":"user","content":[
                {"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{d['photo']}"}},
                {"type":"text","text":f'You are a fun AI at a Holi festival booth for AI.M Academy (AI education for kids grades 5-9). A child named "{d["name"]}" took a photo. Respond ONLY in valid JSON, no backticks or markdown:\n{{"holiTitle":"A fun Holi-themed title (e.g. The Color Commander, Holi\'s Brightest Spark)","holiMessage":"Fun warm 2-3 sentence personalized Holi message referencing their appearance positively and creatively. Mention colors and celebration. Age-appropriate and enthusiastic.","funFact":"A short cool AI fun fact a kid would love"}}'}
            ]}]
        )
        txt = resp.choices[0].message.content.replace("```json","").replace("```","").strip()
        return jsonify(json.loads(txt))
    except Exception as e:
        return jsonify({"error":str(e)}), 500


@app.route("/caricature", methods=["POST"])
def caricature():
    d = request.json
    try:
        result = client.images.edit(
            model="gpt-image-1",
            image=[("photo.jpg", base64.b64decode(d["photo"]), "image/jpeg")],
            prompt="Transform this photo into a vibrant colorful Pixar-style 3D cartoon caricature in a Holi festival celebration. The caricature should clearly resemble the person but with playful exaggerated cartoon proportions. Surround them with clouds of bright colored powder (pink, yellow, green, purple, orange). Pixar 3D animation style, bright saturated Holi colors, festive background with color explosions. Fun vibrant kid-friendly!",
            size="1024x1024",
            quality="medium"
        )
        raw_b64 = result.data[0].b64_json
        branded_b64 = add_logo_to_image(raw_b64)
        last_caricature["image"] = branded_b64
        last_caricature["name"] = d.get("name", "")
        print(f"   💾 Caricature saved for email ({len(branded_b64)} chars)")
        return jsonify({"image": branded_b64})
    except Exception as e:
        return jsonify({"error":str(e)}), 500


@app.route("/detect-mood", methods=["POST"])
def detect_mood():
    d = request.json
    try:
        resp = client.chat.completions.create(
            model="gpt-4o", max_tokens=400,
            messages=[{"role":"user","content":[
                {"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{d['photo']}"}},
                {"type":"text","text":f'You are a fun, playful AI mood detector at a Holi festival booth for kids. A child named "{d["name"]}" just made a face. Analyze their facial expression. Respond ONLY in valid JSON, no backticks:\n{{"mood":"one word emotion (Happy, Surprised, Confused, Excited, Silly, Angry, Scared, Bored, Mysterious, Mischievous, etc)","emoji":"single emoji that matches the mood","confidence":a number 70-99,"funnyComment":"a short funny 1-sentence reaction to their expression, be playful and kid-friendly, reference what you see in their face","tip":"a silly tip like: Try raising one eyebrow to confuse me! or Show me your best surprised face!"}}'
                }
            ]}]
        )
        txt = resp.choices[0].message.content.replace("```json","").replace("```","").strip()
        return jsonify(json.loads(txt))
    except Exception as e:
        return jsonify({"error":str(e)}), 500


# ══════════════════════════════════════════════════
#  NEW ENDPOINTS: Animal Quiz, Superhero, 2050
# ══════════════════════════════════════════════════

@app.route("/animal-quiz", methods=["POST"])
def animal_quiz():
    """GPT-4o generates a personalized AI animal personality."""
    d = request.json
    try:
        resp = client.chat.completions.create(
            model="gpt-4o", max_tokens=500,
            messages=[{"role":"user","content":
                f'You are a fun AI at a Holi festival booth for AI.M Academy (AI education for kids grades 5-9). A child named "{d["name"]}" answered a personality quiz with these traits: {d["answers"]}. Assign them one of these AI animal personalities (or create a unique one): Neural Owl (analytical), Algorithm Cheetah (fast/action), Deep Learning Octopus (creative), Data Wolf (strategic/social). Respond ONLY in valid JSON, no backticks:\n{{"emoji":"single animal emoji","name":"AI Animal Name (e.g. Neural Owl)","title":"Short fun title (e.g. The Thoughtful Analyst)","desc":"3-4 sentence fun personalized description for the child. Reference their quiz answers. Explain what kind of AI builder they would be. Age-appropriate and encouraging.","traits":["trait1","trait2","trait3","trait4"]}}'
            }]
        )
        txt = resp.choices[0].message.content.replace("```json","").replace("```","").strip()
        return jsonify(json.loads(txt))
    except Exception as e:
        return jsonify({"error":str(e)}), 500


@app.route("/superhero", methods=["POST"])
def superhero():
    """GPT-4o generates superhero story + gpt-image-1 creates illustration."""
    d = request.json
    name = d.get("name","Hero")
    hero_name = d.get("heroName","Super Hero")
    power = d.get("power","Super Strength")
    mission = d.get("mission","Save the world")
    gender = d.get("gender","kid")
    try:
        # Step 1: Generate story
        print(f"   Generating superhero story for {name}...")
        resp = client.chat.completions.create(
            model="gpt-4o", max_tokens=500,
            messages=[{"role":"user","content":
                f'You are a fun AI at a Holi festival booth for AI.M Academy (AI education for kids grades 5-9). A {gender} child named "{name}" created an AI superhero. Respond ONLY in valid JSON, no backticks:\nSuperhero Name: {hero_name}\nSpecial Power: {power}\nMission: {mission}\n\n{{"heroName":"{hero_name}","tagline":"A cool 5-word tagline for this hero","origin":"A fun 3-4 sentence origin story for this superhero. Make it exciting, age-appropriate, and tie in AI/tech somehow. Reference their power and mission. Use she/her pronouns if {gender} is girl, he/him if boy.","stats":{{"power":a number 70-99,"speed":a number 70-99,"intelligence":a number 70-99,"creativity":a number 70-99}},"catchphrase":"A short cool catchphrase this hero would say"}}'
            }]
        )
        txt = resp.choices[0].message.content.replace("```json","").replace("```","").strip()
        story = json.loads(txt)

        # Step 2: Generate superhero image
        print(f"   Generating superhero image...")
        img_prompt = f"Create a vibrant, colorful comic book style illustration of a {gender} kid superhero called '{hero_name}'. The hero is a {gender}. Their special power is '{power}' and their mission is '{mission}'. Dynamic action pose, bright bold colors, energy effects around them showing their power. Comic book art style, kid-friendly, exciting and heroic. Background should show a futuristic city."

        if d.get("photo"):
            result = client.images.edit(
                model="gpt-image-1",
                image=[("photo.jpg", base64.b64decode(d["photo"]), "image/jpeg")],
                prompt=f"Transform this child into a {gender} kid superhero called '{hero_name}'. Keep their resemblance but make them heroic. " + img_prompt,
                size="1024x1024",
                quality="medium"
            )
        else:
            result = client.images.generate(
                model="gpt-image-1",
                prompt=img_prompt,
                size="1024x1024",
                quality="medium"
            )

        img_b64 = result.data[0].b64_json
        print(f"   Image generated ({len(img_b64)} chars)")
        branded_b64 = add_logo_to_image(img_b64)
        last_caricature["image"] = branded_b64
        last_caricature["name"] = name
        print(f"   💾 Superhero saved for email")
        story["image"] = branded_b64
        return jsonify(story)
    except Exception as e:
        print(f"   ❌ Superhero error: {e}")
        return jsonify({"error":str(e)}), 500


@app.route("/future2050", methods=["POST"])
def future2050():
    """GPT-4o generates a futuristic 2050 version of the child."""
    d = request.json
    name = d.get("name","")
    career = d.get("career","AI Engineer")
    gender = d.get("gender","kid")
    try:
        # Step 1: Generate future profile
        print(f"   Generating 2050 profile for {name}...")
        resp = client.chat.completions.create(
            model="gpt-4o", max_tokens=500,
            messages=[{"role":"user","content":
                f'You are a fun AI at a Holi festival booth for AI.M Academy (AI education for kids grades 5-9). A {gender} child named "{name}" wants to see themselves in the year 2050 as a "{career}". Respond ONLY in valid JSON, no backticks:\n{{"title":"{career}","futureTitle":"A cool professional title for 2050 (e.g. Chief Neural Architect, Lead Mars Colony Engineer)","company":"A cool futuristic company or organization they work at in 2050","achievement":"A single impressive achievement they accomplished by 2050","bio":"A fun 3-4 sentence bio of {name} in 2050. Make it exciting, futuristic, age-appropriate. Use {"she/her" if gender == "girl" else "he/him"} pronouns. Reference the career and how they started learning AI as a kid.","funFact":"A fun fictional fact about life in 2050"}}'
            }]
        )
        txt = resp.choices[0].message.content.replace("```json","").replace("```","").strip()
        profile = json.loads(txt)

        # Step 2: Generate futuristic portrait
        print(f"   Generating 2050 portrait...")
        gender_word = "girl" if gender == "girl" else "boy"
        img_prompt = f"Create a futuristic professional portrait of a {gender_word} who has grown up to be a {career} in the year 2050. They should look like a young adult in their late 20s. Sleek futuristic clothing, holographic elements, advanced technology in the background. The setting should be a stunning futuristic workspace — think glass walls, floating screens, advanced AI interfaces. Style: cinematic, high-tech, hopeful and inspiring. Bright lighting, professional but approachable."

        if d.get("photo"):
            result = client.images.edit(
                model="gpt-image-1",
                image=[("photo.jpg", base64.b64decode(d["photo"]), "image/jpeg")],
                prompt=f"Transform this child's photo into a futuristic portrait of them as a young adult {career} in the year 2050. Age them up to look like they are in their late 20s but keep their resemblance. " + img_prompt,
                size="1024x1024",
                quality="medium"
            )
        else:
            result = client.images.generate(
                model="gpt-image-1",
                prompt=img_prompt,
                size="1024x1024",
                quality="medium"
            )

        img_b64 = result.data[0].b64_json
        print(f"   Image generated ({len(img_b64)} chars)")
        branded_b64 = add_logo_to_image(img_b64)
        last_caricature["image"] = branded_b64
        last_caricature["name"] = name
        print(f"   💾 2050 portrait saved for email")
        profile["image"] = branded_b64
        return jsonify(profile)
    except Exception as e:
        print(f"   ❌ 2050 error: {e}")
        return jsonify({"error":str(e)}), 500


# ══════════════════════════════════════════════════
#  SAVE EMAIL — handles ALL activities
# ══════════════════════════════════════════════════

@app.route("/save-email", methods=["POST"])
def save_email():
    d = request.json
    email_addr = d.get("email","")
    child_name = d.get("name","")
    activity = d.get("activity","Caricature")
    results_html = d.get("results","")
    # Use stored image for any activity that generates images
    image_b64 = last_caricature.get("image", "") if activity in ["Caricature", "Superhero Builder", "You in 2050"] else ""
    email_sent = False

    if email_addr:
        emails.append({"name":child_name, "email":email_addr, "activity":activity})
        with open("collected_emails.csv","a") as f:
            f.write(f'{child_name},{email_addr},{activity}\n')
        print(f"\n📧 Email saved: {child_name} → {email_addr} ({activity})")

        if GMAIL_APP_PASSWORD != "xxxx xxxx xxxx xxxx":
            if image_b64:
                # Image email (caricature, superhero, 2050)
                print(f"   Sending image email in background...")
                thread = threading.Thread(
                    target=send_email_background,
                    args=(email_addr, child_name, image_b64)
                )
                thread.start()
                email_sent = True
            elif results_html:
                # Activity email (text results only — train AI, mood detector)
                print(f"   Sending {activity} email in background...")
                thread = threading.Thread(
                    target=send_activity_email_background,
                    args=(email_addr, child_name, activity, results_html)
                )
                thread.start()
                email_sent = True
            else:
                # Generic email
                print(f"   Sending generic info email in background...")
                generic_html = f'<p style="color:#555;font-size:15px;">{child_name} visited the AI.M Academy booth and experienced our {activity} activity!</p>'
                thread = threading.Thread(
                    target=send_activity_email_background,
                    args=(email_addr, child_name, activity, generic_html)
                )
                thread.start()
                email_sent = True
        else:
            print(f"   ⚠️  Gmail not configured — password still default")

    return jsonify({"count":len(emails), "sent":email_sent})


@app.route("/email-count")
def count():
    return jsonify({"count":len(emails)})


@app.route("/save-activity-email", methods=["POST"])
def save_activity_email_route():
    d = request.json
    email_addr = d.get("email","")
    child_name = d.get("name","")
    activity = d.get("activity","Activity")
    results_html = d.get("results","")
    email_sent = False

    if email_addr:
        emails.append({"name":child_name, "email":email_addr, "activity":activity})
        with open("collected_emails.csv","a") as f:
            f.write(f'{child_name},{email_addr},{activity}\n')
        print(f"\n📧 Activity email saved: {child_name} → {email_addr} ({activity})")

        if GMAIL_APP_PASSWORD != "xxxx xxxx xxxx xxxx":
            print(f"   Sending {activity} email in background...")
            thread = threading.Thread(
                target=send_activity_email_background,
                args=(email_addr, child_name, activity, results_html)
            )
            thread.start()
            email_sent = True
        else:
            print(f"   ⚠️  Gmail not configured")

    return jsonify({"count":len(emails), "sent":email_sent})


if __name__=="__main__":
    if not os.path.exists("collected_emails.csv"):
        with open("collected_emails.csv","w") as f: f.write("name,email,activity\n")

    print("\n" + "="*50)
    print("  🎨 AI.M Academy — Holi Booth Server")
    print("="*50)
    if GMAIL_APP_PASSWORD == "xxxx xxxx xxxx xxxx":
        print("⚠️  Gmail not configured — emails will be saved to CSV only")
    else:
        print(f"📧 Emails will send from {GMAIL_ADDRESS}")
    print(f"📁 Emails also saved to collected_emails.csv")
    print(f"\n✅ Now open any booth HTML in your browser")
    print("🛑 Press Ctrl+C to stop\n")
    app.run(host="0.0.0.0", port=8000)