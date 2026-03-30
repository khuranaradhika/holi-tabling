# AI.M Academy — Holi Festival Booth

Interactive AI experience platform built for festival/event booths. Features six hands-on AI activities designed for kids in grades 5–9, powered by OpenAI's GPT-4o and DALL-E APIs.

**Brand:** [aimacademy.us](https://aimacademy.us) | (470) 269-6906

---

## Activities

| Activity | File | Description |
|----------|------|-------------|
| Caricature Booth | `booth.html` | Generates a Pixar-style cartoon portrait from a webcam photo |
| AI Animal Quiz | `animal_quiz.html` | Personality quiz that assigns you an AI-themed animal (Neural Owl, Algorithm Cheetah, etc.) |
| Mood Detector | `mood_detector.html` | Detects facial expressions and emotion confidence scores |
| Superhero Builder | `superhero.html` | Creates a custom superhero story, stats, and illustrated portrait |
| You in 2050 | `future2050.html` | Generates a futuristic career profile and AI illustration |
| Train the AI | `train_ai.html` | Browser-based ML training using TensorFlow.js — no server required |

---

## Tech Stack

**Backend:** Python 3 · Flask · OpenAI API (GPT-4o, gpt-image-1) · Pillow · Gmail SMTP

**Frontend:** HTML/CSS/JavaScript · TensorFlow.js · MobileNet · KNN-Classifier · WebRTC · Canvas API

---

## Setup

### 1. Install dependencies

```bash
pip install flask flask-cors openai pillow python-dotenv
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```
OPENAI_API_KEY=sk-proj-...
GMAIL_ADDRESS=your-gmail@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

**Gmail App Password setup:**
1. Enable 2-Step Verification on your Google account
2. Go to `myaccount.google.com` → search "App Passwords"
3. Create a new app password (e.g., name it "Holi Booth")
4. Paste the 16-character password into `.env`

> If Gmail is not configured, emails are saved to `collected_emails.csv` only.

### 3. Add logo

Place `logo.png` in the project root. This gets overlaid on all generated images.

### 4. Run the server

```bash
python server.py
```

Server starts at `http://localhost:8000`.

### 5. Test email (optional)

```bash
python test_email.py
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/caricature` | Generate a caricature from a base64 image |
| `POST` | `/animal-quiz` | Get an AI animal personality result |
| `POST` | `/detect-mood` | Analyze facial expression from image |
| `POST` | `/superhero` | Generate superhero profile + illustration |
| `POST` | `/future2050` | Generate 2050 future profile + illustration |
| `POST` | `/analyze` | Holi-themed personalized message |
| `POST` | `/save-email` | Capture email address |
| `POST` | `/save-activity-email` | Email activity results to participant |
| `GET` | `/email-count` | Return total emails collected |

---

## Data Collection

Participant emails and activity data are stored locally in `collected_emails.csv`. No external database is used.

Fields collected: name, email, activity, timestamp.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `GMAIL_ADDRESS` | No | Gmail address for sending emails |
| `GMAIL_APP_PASSWORD` | No | Gmail App Password (16 chars) |
