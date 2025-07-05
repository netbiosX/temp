import os
from flask import Flask, request, render_template, redirect, url_for, flash
import yaml
from sigma.collection import SigmaCollection
import openai

# Replace this with your actual OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-...")

openai.api_key = OPENAI_API_KEY

app = Flask(__name__)
app.secret_key = 'very_secret'  # Needed for flash messages

def parse_sigma(yaml_text):
    """Returns a dict with key info from a Sigma rule."""
    try:
        rule = yaml.safe_load(yaml_text)
        info = {
            "title": rule.get("title", "N/A"),
            "description": rule.get("description", ""),
            "logsource": rule.get("logsource", {}),
            "detection": rule.get("detection", {}),
        }
        fields = []
        detection = rule.get("detection", {})
        for k, v in detection.items():
            if isinstance(v, dict):
                fields += list(v.keys())
        info["fields"] = list(set(fields))
        return info
    except Exception as e:
        raise ValueError(f"Could not parse Sigma YAML: {e}")

def analyse_sigma_with_openai(summary, full_yaml):
    """Uses OpenAI's GPT to do web-based gap analysis of the Sigma rule."""
    # This will use the latest web-browsing enabled GPT-4o model
    prompt = (
        f"You are a cyber detection engineer. Analyse the following Sigma detection rule for detection gaps, weaknesses, and bypasses.\n\n"
        f"Sigma Rule Title: {summary['title']}\n"
        f"Description: {summary['description']}\n"
        f"Logsource: {summary['logsource']}\n"
        f"Detection fields: {summary['fields']}\n\n"
        f"Sigma YAML:\n{full_yaml}\n\n"
        f"Search the internet (including MITRE ATT&CK, security blogs, GitHub, and recent threat intel) for:\n"
        f"- Known ways attackers bypass similar detections\n"
        f"- Weaknesses in this rule or missing coverage\n"
        f"- Recommendations to improve the detection\n"
        f"Write a summary for a detection engineer, using references or links if appropriate."
    )

    # Use the "gpt-4o" model with browsing
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=700,
        temperature=0.2,
        tools=[{"type": "web_search"}],  # Activates web browsing (if available)
    )
    return response.choices[0].message.content

@app.route("/", methods=["GET", "POST"])
def index():
    sigma_yaml = ""
    analysis = ""
    error = None

    if request.method == "POST":
        if "sigma_file" in request.files and request.files["sigma_file"].filename:
            sigma_file = request.files["sigma_file"]
            sigma_yaml = sigma_file.read().decode("utf-8")
        else:
            sigma_yaml = request.form.get("sigma_text", "")

        if not sigma_yaml.strip():
            error = "Please upload or paste a Sigma rule."
            flash(error, "danger")
            return render_template("index.html", sigma_yaml=sigma_yaml, analysis=analysis, error=error)

        # Validate YAML
        try:
            info = parse_sigma(sigma_yaml)
        except Exception as e:
            error = str(e)
            flash(error, "danger")
            return render_template("index.html", sigma_yaml=sigma_yaml, analysis=analysis, error=error)

        # Call OpenAI for detection gap analysis
        try:
            analysis = analyse_sigma_with_openai(info, sigma_yaml)
        except Exception as e:
            error = f"OpenAI error: {e}"
            flash(error, "danger")
            return render_template("index.html", sigma_yaml=sigma_yaml, analysis=analysis, error=error)

        return render_template("index.html", sigma_yaml=sigma_yaml, analysis=analysis, error=error)

    return render_template("index.html", sigma_yaml=sigma_yaml, analysis=analysis, error=error)

if __name__ == "__main__":
    app.run(debug=True)
