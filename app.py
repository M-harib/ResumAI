from flask import Flask, render_template, request, make_response, jsonify
from xhtml2pdf import pisa
from io import BytesIO
from openai import OpenAI
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Load API keys
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY")  # Optional DeepSeek key

client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

print("Loaded OpenAI Key:", repr(OPENAI_KEY))
print("Loaded DeepSeek Key:", repr(DEEPSEEK_KEY))

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/preview", methods=["POST"])
def preview():
    data = {
        "name": request.form["name"],
        "email": request.form["email"],
        "phone": request.form["phone"],
        "summary": request.form["summary"],
        "experience": request.form["experience"],
        "education": request.form["education"],
        "skills": request.form["skills"].split(","),
    }
    return render_template("preview.html", data=data)

@app.route("/download", methods=["POST"])
def download():
    data = {
        "name": request.form["name"],
        "email": request.form["email"],
        "phone": request.form["phone"],
        "summary": request.form["summary"],
        "experience": request.form["experience"],
        "education": request.form["education"],
        "skills": request.form["skills"].split(","),
    }

    html = render_template("resume_pdf.html", data=data)
    pdf = BytesIO()
    pisa.CreatePDF(html, dest=pdf)
    response = make_response(pdf.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "attachment; filename=resume.pdf"
    return response

@app.route("/suggest", methods=["POST"])
def suggest():
    section = request.json.get("section")
    context = request.json.get("context", "")

    prompt_map = {
        "summary": f"Write a professional summary for someone with this background: {context}",
        "experience": f"Write a strong work experience bullet point for this role: {context}",
        "education": f"Write a short academic background summary based on this: {context}",
    }

    prompt = prompt_map.get(section)
    if not prompt:
        return jsonify({"error": "Invalid section type"}), 400

    # 1️⃣ Try OpenAI
    if client:
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.7,
            )
            suggestion = response.choices[0].message.content.strip()
            return jsonify({"suggestion": suggestion})
        except Exception as e:
            print("OpenAI error:", e)

    # 2️⃣ Try DeepSeek if key exists
    if DEEPSEEK_KEY:
        try:
            headers = {"Authorization": f"Bearer {DEEPSEEK_KEY}"}
            json_data = {"prompt": prompt, "max_tokens": 150}
            ds_response = requests.post(
                "https://api.openrouter.ai/v1/engines/deepseek/completions",
                headers=headers,
                json=json_data,
            )
            ds_response.raise_for_status()
            suggestion = ds_response.json()["choices"][0]["text"].strip()
            return jsonify({"suggestion": suggestion})
        except Exception as e:
            print("DeepSeek error:", e)

    # 3️⃣ Fallback mock suggestion
    mock = f"This is a sample {section} suggestion."
    return jsonify({"suggestion": mock})

if __name__ == "__main__":
    app.run(debug=True)
