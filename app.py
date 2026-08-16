import os
import json

from flask import Flask, render_template, request
from dotenv import load_dotenv
from google import genai


# ==================================================
# CONFIGURATION
# ==================================================

load_dotenv()

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

RESUME_FILE = os.path.join(BASE_DIR, "resume.txt")
JSON_FILE = "portfolio.json"


# ==================================================
# ERROR HANDLER
# ==================================================

def show_error(title, message):

    return render_template(
        "error.html",
        title=title,
        message=message
    ), 400


# ==================================================
# HOME
# ==================================================

@app.route("/")
def home():

    return render_template("index.html")


# ==================================================
# GENERATE PORTFOLIO
# ==================================================

@app.route("/generate", methods=["POST"])
def generate():

    # ------------------------------------------------
    # 1. Get resume from UI
    # ------------------------------------------------

    resume_input = request.form.get(
        "resume",
        ""
    )


    # ------------------------------------------------
    # 2. Save user input to resume.txt
    # ------------------------------------------------

    try:

        with open(
            RESUME_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(resume_input)

    except OSError:

        return show_error(
            "FILE ERROR",
            "The application could not save resume.txt."
        )


    # ------------------------------------------------
    # 3. Check whether resume.txt exists
    # ------------------------------------------------

    if not os.path.exists(RESUME_FILE):

        return show_error(
            "RESUME NOT FOUND",
            "resume.txt could not be found. "
            "Please provide a resume and try again."
        )


    # ------------------------------------------------
    # 4. Read resume.txt
    # ------------------------------------------------

    try:

        with open(RESUME_FILE, "r", encoding="utf-8") as f:
            resume_text = f.read()

    except OSError:

        return show_error(
            "FILE ERROR",
            "The application could not read resume.txt."
        )


    # ------------------------------------------------
    # 5. Empty resume test
    # ------------------------------------------------

    if not resume_text.strip():

        return show_error(
            "EMPTY RESUME",
            "Your resume is empty. "
            "Please paste your resume and try again."
        )


    # ------------------------------------------------
    # 6. Very short resume test
    # ------------------------------------------------

    if len(resume_text.strip()) < 50:

        return show_error(
            "RESUME TOO SHORT",
            "The resume is too short to generate "
            "a meaningful portfolio. "
            "Please provide more information."
        )


    # ------------------------------------------------
    # 7. Clean resume
    # ------------------------------------------------

    lines = [

        line.strip()

        for line in resume_text.splitlines()

        if line.strip()

    ]

    clean_resume = "\n".join(lines)


    # ------------------------------------------------
    # 8. Check API key
    # ------------------------------------------------

    api_key = os.getenv(
        "GEMINI_API_KEY"
    )

    if not api_key:

        return show_error(
            "CONFIGURATION ERROR",
            "Gemini API key is missing. "
            "Please configure GEMINI_API_KEY "
            "in the .env file."
        )


    # ------------------------------------------------
    # 9. Create Gemini client
    # ------------------------------------------------

    try:

        client = genai.Client(
            api_key=api_key
        )

    except Exception:

        return show_error(
            "CONFIGURATION ERROR",
            "The Gemini API client could not "
            "be configured."
        )


    # ------------------------------------------------
    # 10. Create prompt
    # ------------------------------------------------

    prompt = f"""
You are an AI resume-to-portfolio
data extraction system.

Analyze the resume below and convert it
into structured portfolio information.

IMPORTANT RULES:

1. Use ONLY information explicitly supported
   by the resume.

2. NEVER invent information.

3. Do not create fake:
   - skills
   - projects
   - companies
   - education
   - certifications
   - achievements
   - contact details

4. If a section is missing, return an
   empty list or empty string.

5. Keep descriptions concise and professional.

6. Return ONLY valid JSON.

7. Do NOT return Markdown.

8. Do NOT use ```json.

Use exactly this structure:

{{
    "name": "",
    "title": "",
    "about": "",

    "skills": [],

    "education": [],

    "experience": [],

    "projects": [],

    "certifications": [],

    "contact": {{
        "email": "",
        "phone": "",
        "github": "",
        "linkedin": ""
    }}
}}

RESUME:

------------------------------

{clean_resume}

------------------------------
"""


    # ------------------------------------------------
    # 11. Call Gemini
    # ------------------------------------------------

    try:

        interaction = client.interactions.create(

        model="gemini-3.5-flash",

        input=prompt

    )

        response_text = interaction.output_text.strip()

    except Exception as e:

        print("\n================ GEMINI ERROR ================")

        print(e)

        print("================================================\n")

        return show_error(

            "AI SERVICE ERROR",

            f"Gemini could not process the resume.please try again"

        )


    # ------------------------------------------------
    # 12. Validate Gemini response
    # ------------------------------------------------

    if not response_text:

        return show_error(
            "EMPTY AI RESPONSE",
            "Gemini returned an empty response. "
            "The portfolio could not be generated."
        )


    # ------------------------------------------------
    # 13. Convert JSON to Python dictionary
    # ------------------------------------------------

    try:

        data = json.loads(
            response_text
        )

    except json.JSONDecodeError:

        return show_error(
            "INVALID AI RESPONSE",
            "Gemini returned invalid JSON. "
            "The portfolio was not generated."
        )


    # ------------------------------------------------
    # 14. Make sure top-level JSON is a dictionary
    # ------------------------------------------------

    if not isinstance(data, dict):

        return show_error(
            "INVALID JSON STRUCTURE",
            "Gemini returned JSON, but the "
            "structure was not valid for a portfolio."
        )


    # ------------------------------------------------
    # 15. Required fields
    # ------------------------------------------------

    list_fields = [

        "skills",
        "education",
        "experience",
        "projects",
        "certifications"

    ]

    text_fields = [

        "name",
        "title",
        "about"

    ]


    # Missing sections become empty.
    # They are NOT invented.

    for field in list_fields:

        if field not in data:

            data[field] = []

        elif not isinstance(
            data[field],
            list
        ):

            data[field] = []


    for field in text_fields:

        if field not in data:

            data[field] = ""

        elif not isinstance(
            data[field],
            str
        ):

            data[field] = ""


    # ------------------------------------------------
    # 16. Contact validation
    # ------------------------------------------------

    if "contact" not in data:

        data["contact"] = {}

    elif not isinstance(
        data["contact"],
        dict
    ):

        data["contact"] = {}


    contact_fields = [

        "email",
        "phone",
        "github",
        "linkedin"

    ]

    for field in contact_fields:

        if field not in data["contact"]:

            data["contact"][field] = ""


    # ------------------------------------------------
    # 17. Save portfolio.json
    # ------------------------------------------------

    try:

        with open(
            JSON_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

    except OSError:

        return show_error(
            "FILE ERROR",
            "The structured portfolio data "
            "could not be saved."
        )


    # ------------------------------------------------
    # 18. Generate portfolio.html
    # ------------------------------------------------

    try:

        return render_template(
            "portfolio.html",
            data=data
        )

    except Exception:

        return show_error(
            "GENERATION ERROR",
            "The portfolio could not be generated."
        )


# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )