import os
import subprocess
import glob
import requests
from bs4 import BeautifulSoup

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


########################################
# CONFIG
########################################

OVERLOAD_SCRIPT = "MSGHostOverload_v1_optimized.py"
PROMPT_FILE = "PROMPT.txt"

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"

OUTPUT_DIR = "output"

os.makedirs(OUTPUT_DIR, exist_ok=True)


########################################
# STYLES
########################################

styles = getSampleStyleSheet()

title_style = styles["Heading1"]

section_style = ParagraphStyle(
    name="SectionStyle",
    parent=styles["Heading2"],
    textColor=colors.HexColor("#1F4E79")
)

body_style = styles["Normal"]


########################################
# STEP 1 — RUN HOST OVERLOAD SCRIPT
########################################

def run_overload_script():

    print("Running host overload collector...")

    subprocess.run(["python3", OVERLOAD_SCRIPT], check=True)

    print("Host overload scan complete.")


########################################
# STEP 2 — FIND GENERATED HTML
########################################

def find_latest_html():

    files = glob.glob("*.html")

    if not files:
        raise Exception("No HTML report generated")

    latest = max(files, key=os.path.getctime)

    print("Using HTML report:", latest)

    return latest


########################################
# STEP 3 — PARSE HTML
########################################

def parse_html(html_file):

    with open(html_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    rows = soup.find_all("tr")

    hosts = []

    for row in rows[1:]:

        cols = row.find_all("td")

        if len(cols) < 4:
            continue

        hosts.append({
            "hostname": cols[0].text.strip(),
            "cpu": cols[1].text.strip(),
            "mem": cols[2].text.strip(),
            "load": cols[3].text.strip(),
        })

    return hosts


########################################
# LOAD PROMPT
########################################

def load_prompt():

    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()


########################################
# BUILD PROMPT
########################################

def build_prompt(base_prompt, host):

    return base_prompt + f"""

HOST DATA:
Hostname: {host['hostname']}
CPU: {host['cpu']}
Memory: {host['mem']}
Load: {host['load']}
"""


########################################
# CALL OLLAMA
########################################

def analyze_host(host, base_prompt):

    prompt = build_prompt(base_prompt, host)

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        }
    )

    return response.json()["response"]


########################################
# TABLE RENDERER
########################################

def render_table(table_data):

    table = Table(table_data, repeatRows=1)

    style = TableStyle([
        ("GRID",(0,0),(-1,-1),0.5,colors.grey),
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1F4E79")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
    ])

    table.setStyle(style)

    return table


########################################
# CREATE PDF
########################################

def create_pdf(hostname, analysis):

    filename = f"{OUTPUT_DIR}/{hostname}_analysis.pdf"

    doc = SimpleDocTemplate(filename)

    elements = []

    elements.append(Paragraph("Linux Host Health Analysis", title_style))
    elements.append(Spacer(1,12))
    elements.append(Paragraph(hostname, section_style))
    elements.append(Spacer(1,20))

    lines = analysis.split("\n")

    table_buffer = []

    for line in lines:

        line = line.strip()

        if not line:
            continue

        if line.startswith("|"):

            cols = [c.strip() for c in line.strip("|").split("|")]

            table_buffer.append(cols)

            continue

        if table_buffer:

            elements.append(render_table(table_buffer))
            elements.append(Spacer(1,16))

            table_buffer = []

        elements.append(Paragraph(line, body_style))
        elements.append(Spacer(1,6))

    if table_buffer:
        elements.append(render_table(table_buffer))

    doc.build(elements)

    print("PDF generated:", filename)


########################################
# MAIN PIPELINE
########################################

def main():

    run_overload_script()

    html_file = find_latest_html()

    hosts = parse_html(html_file)

    base_prompt = load_prompt()

    for host in hosts:

        print("Analyzing host:", host["hostname"])

        analysis = analyze_host(host, base_prompt)

        create_pdf(host["hostname"], analysis)

    print("Pipeline completed successfully.")


if __name__ == "__main__":
    main()
