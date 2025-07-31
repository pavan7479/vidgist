import os
import re
from flask import Flask, render_template, request
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv
import google.generativeai as genai
from markdown import markdown
from markdown.extensions import codehilite, fenced_code

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

app = Flask(__name__)
ytt_api = YouTubeTranscriptApi()

# --- Enhanced Prompt Templates with Better Code Formatting Instructions ---
detailed_explain_prompt = (
    "You are a helpful assistant that explains YouTube video content in a detailed and engaging manner.\n\n"
    "I will give you the full transcript text of a YouTube video. Your task is to:\n\n"
    "1. Read the transcript carefully.\n"
    "2. Explain everything as if you are the person speaking in the video, directly explaining it to the audience.\n"
    "3. Keep the tone natural and conversational, like how a YouTuber would talk to their viewers.\n"
    "4. Do not skip or summarize any point — include everything mentioned in the transcript in a detailed manner.\n"
    "5. If there are examples, code, explanations, comparisons, diagrams mentioned, include them as clearly as possible.\n"
    "6. Retain the order and logic of the original speaker, but improve clarity and flow if needed.\n"
    "7. Include proper formatting such as:\n"
    "   - Headings for sections (if present),\n"
    "   - Bullet points,\n"
    "   - Code blocks using triple backticks (```language) for syntax highlighting,\n"
    "   - Speaker thoughts or highlights in italics (optional).\n"
    "8. **IMPORTANT FOR CODE**: When including any code snippets:\n"
    "   - Always wrap code in triple backticks with the appropriate language (```python, ```javascript, ```html, etc.)\n"
    "   - Include proper indentation and formatting\n"
    "   - Add comments to explain complex parts\n"
    "   - Break long code into logical sections with explanations between them\n\n"
    "Please begin explaining the content as if you're the speaker, preserving all points in order without skipping anything.\n\n"
    "Here is the transcript:\n"
)

summary_prompt = (
    "You are an expert assistant that summarizes YouTube videos in a clear, concise, and well-structured format.\n\n"
    "I will give you the full transcript of a YouTube video. Your task is to:\n\n"
    "1. Read and understand the transcript thoroughly.\n"
    "2. Provide a structured summary that retains all important points, explanations, and examples.\n"
    "3. Organize the summary with clear headings and subheadings.\n"
    "4. Use bullet points for listing concepts or steps.\n"
    "5. **IMPORTANT FOR CODE**: Include code blocks using triple backticks with language specification (```python, ```javascript, etc.).\n"
    "6. Avoid skipping any concept; summarize it briefly but completely.\n"
    "7. Keep the tone neutral and informative (not from the speaker's point of view).\n"
    "8. If the transcript is long, break it into logical sections like:\n"
    "   - Introduction\n"
    "   - Key Concepts Explained\n"
    "   - Examples\n"
    "   - Code or Demonstrations\n"
    "   - Conclusion or Takeaways\n"
    "9. For any code mentioned:\n"
    "   - Format it properly with syntax highlighting\n"
    "   - Include brief explanations of what the code does\n"
    "   - Maintain proper indentation and structure\n\n"
    "Please provide the summary in a structured format as described above.\n\n"
    "Here is the transcript:\n"
)

revision_notes_prompt = (
    "You are a helpful assistant that converts YouTube video transcripts into clean, structured, and easy-to-revise notes.\n\n"
    "I will give you the transcript text of a video. Your task is to:\n\n"
    "1. Extract and organize all important points, facts, definitions, steps, or explanations from the transcript.\n"
    "2. Present them as concise, revision-friendly notes, suitable for quick studying.\n"
    "3. Use clear headings and subheadings to organize the notes by topics.\n"
    "4. Use bullet points or numbered lists for clarity.\n"
    "5. Include:\n"
    "   - Definitions\n"
    "   - Key concepts\n"
    "   - Examples\n"
    "   - Diagrams as text if any (describe them briefly)\n"
    "   - Code snippets with proper formatting using triple backticks\n"
    "6. Keep the tone neutral and educational (no first-person or speaker-style explanations).\n"
    "7. Ensure no major point from the transcript is missed.\n"
    "8. Avoid filler words or repetition; keep it crisp and to the point.\n"
    "9. **IMPORTANT FOR CODE**: Format all code snippets properly:\n"
    "   - Use triple backticks with language specification\n"
    "   - Include proper indentation\n"
    "   - Add brief comments explaining functionality\n"
    "   - Group related code concepts together\n\n"
    "Please provide structured notes ideal for revision, using the format mentioned above.\n\n"
    "Here is the transcript:\n"
)


# --- Extract Video ID from URL ---
def extract_video_id(url):
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None


# --- Fetch Transcript from YouTube ---
def fetch_transcript(video_id):
    transcript_text = ""
    try:
        extracted = ytt_api.fetch(video_id)
        for entry in extracted:
            transcript_text += entry.text + " "
        return transcript_text.strip()
    except Exception as e:
        return f"Error fetching transcript: {e}"


# --- Enhanced Generate Response with Better Markdown Processing ---
def generate_video_content(transcript_text, prompt):
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt + transcript_text)
    
    # Enhanced markdown conversion with code highlighting
    html_content = markdown(
        response.text, 
        extensions=[
            'codehilite',
            'fenced_code',
            'tables',
            'toc'
        ],
        extension_configs={
            'codehilite': {
                'css_class': 'highlight',
                'use_pygments': True,
                'guess_lang': True
            }
        }
    )
    
    return html_content


# --- Flask Routes ---
@app.route("/", methods=["GET", "POST"])
def index():
    result = ""
    error = ""

    if request.method == "POST":
        video_url = request.form.get("video_url")
        output_type = request.form.get("output_type")

        video_id = extract_video_id(video_url)

        if not video_id:
            error = "Invalid YouTube URL."
        else:
            transcript = fetch_transcript(video_id)
            if transcript.startswith("Error"):
                error = transcript
            else:
                if output_type == "explanation":
                    result = generate_video_content(transcript, detailed_explain_prompt)
                elif output_type == "summary":
                    result = generate_video_content(transcript, summary_prompt)
                elif output_type == "revision":
                    result = generate_video_content(transcript, revision_notes_prompt)
                else:
                    error = "Invalid output type selected."
    
    return render_template("index.html", result=result, error=error)


if __name__ == "__main__":
    app.run(debug=True)