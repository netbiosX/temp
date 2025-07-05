import yaml
import requests
from sigma.collection import SigmaCollection

OPENAI_API_KEY = "sk-..."   # Or use a different LLM provider

def parse_sigma_rule(sigma_yaml: str):
    """Parse Sigma YAML, extract detection logic and relevant fields."""
    rule = yaml.safe_load(sigma_yaml)
    info = {
        "title": rule.get("title"),
        "logsource": rule.get("logsource", {}),
        "detection": rule.get("detection", {}),
        "description": rule.get("description", ""),
    }
    # Extract detection fields and operators
    fields = []
    detection = rule.get("detection", {})
    for key, value in detection.items():
        if isinstance(value, dict):
            fields += list(value.keys())
    info["fields"] = list(set(fields))
    return info

def search_detection_gaps(summary):
    """Do a web search for detection gaps, bypasses, or improvement tips."""
    query = f"Bypass or detection gaps for {summary['title']} in {summary['logsource'].get('category','')} detection {summary['fields']}"
    # Use Bing/Google or LLM web tool. Here's a fake web search for illustration.
    print(f"Searching internet for: {query}")
    # For real code, use a search API and parse the top results.
    # Optionally, use the OpenAI web search/gpt-4o web tool.
    # For this prototype, we'll just fake it:
    web_results = [
        "Some attackers evade process_creation rules by using alternate command interpreters.",
        "Sigma rule misses 'pwsh.exe' as alternate PowerShell host.",
        "Mitre ATT&CK recommends also watching WMI and script-based activity.",
    ]
    return "\n".join(web_results)

def ask_llm_for_gaps(rule_summary, web_info):
    """Query LLM to synthesize detection gaps from web data."""
    import openai
    openai.api_key = OPENAI_API_KEY
    prompt = (
        f"Given this Sigma rule:\n"
        f"Title: {rule_summary['title']}\n"
        f"Description: {rule_summary['description']}\n"
        f"Logsource: {rule_summary['logsource']}\n"
        f"Detection fields: {rule_summary['fields']}\n\n"
        f"And this threat intelligence found on the internet:\n{web_info}\n\n"
        "Identify any detection gaps, evasion techniques, or improvements. Write a clear summary for a detection engineer."
    )
    # For real use:
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.4,
    )
    return response.choices[0].message.content

def analyse_sigma_rule(sigma_yaml):
    # 1. Parse
    summary = parse_sigma_rule(sigma_yaml)
    # 2. Internet search
    web_info = search_detection_gaps(summary)
    # 3. LLM synthesis
    analysis = ask_llm_for_gaps(summary, web_info)
    return analysis

if __name__ == "__main__":
    # Example Sigma YAML
    sigma = """
title: Simple LSASS Dump
description: Detects use of procdump to dump lsass.exe process.
logsource:
  category: process_creation
detection:
  selection:
    Image|endswith:
      - lsass.exe
    CommandLine|contains:
      - procdump
  condition: selection
"""
    print("Analysing Sigma rule for detection gaps...")
    result = analyse_sigma_rule(sigma)
    print("Analysis result:\n", result)
