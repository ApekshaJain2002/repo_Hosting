import os
import requests
from bs4 import BeautifulSoup

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


########################################
# CONFIG
########################################

HTML_FILE = "linux_host_health_report.html"
PROMPT_FILE = "PROMPT.txt"
OUTPUT_DIR = "output"

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"

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

body_style = ParagraphStyle(
    name="BodyStyle",
    parent=styles["Normal"],
    fontSize=10,
    leading=14
)


########################################
# LOAD PROMPT
########################################

def load_prompt():
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()


########################################
# PARSE HTML
########################################

def parse_html():
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    rows = soup.find_all("tr")[1:]
    hosts = []

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 10:
            continue

        hosts.append({
            "hostname": cols[0].text.strip(),
            "cpu": cols[1].text.strip(),
            "mem": cols[2].text.strip(),
            "load": cols[3].text.strip(),
            "cpu_breach": cols[4].text.strip(),
            "mem_breach": cols[5].text.strip(),
            "load_breach": cols[6].text.strip(),
            "top_cpu": cols[7].text.strip(),
            "top_mem": cols[8].text.strip(),
            "details": cols[9].text.strip()
        })

    return hosts


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
CPU Breach: {host['cpu_breach']}
Memory Breach: {host['mem_breach']}
Load Breach: {host['load_breach']}

TOP CPU:
{host['top_cpu']}

TOP MEMORY:
{host['top_mem']}

DETAILS:
{host['details']}
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
# STRICT TABLE RENDERER
########################################

def render_table(table_lines):

    table_data = []

    for line in table_lines:

        line = line.strip()

        # skip markdown separator row like |----|----|
        if set(line.replace("|","").strip()) == {"-"}:
            continue

        cols = [c.strip() for c in line.strip("|").split("|")]
        table_data.append(cols)

    table = Table(table_data, repeatRows=1)

    style = TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1F4E79")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ])

    # alternate row colors
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            style.add("BACKGROUND", (0,i), (-1,i), colors.whitesmoke)

    table.setStyle(style)

    return table


########################################
# CREATE PROFESSIONAL PDF
########################################

def create_pdf(hostname, analysis):

    filename = f"{OUTPUT_DIR}/{hostname}_analysis.pdf"
    doc = SimpleDocTemplate(filename)

    elements = []

    elements.append(Paragraph("Linux Host Health Analysis", title_style))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(hostname, section_style))
    elements.append(Spacer(1, 20))

    lines = analysis.split("\n")

    table_buffer = []
    inside_table = False

    for line in lines:

        stripped = line.strip()

        if not stripped:
            continue

        # Detect pipe table
        if stripped.startswith("|"):
            table_buffer.append(stripped)
            inside_table = True
            continue

        if inside_table:
            elements.append(render_table(table_buffer))
            elements.append(Spacer(1, 18))
            table_buffer = []
            inside_table = False

        # Section headings
        if stripped.startswith("1.") or stripped.startswith("2.") \
           or stripped.startswith("3.") or stripped.startswith("4.") \
           or stripped.startswith("5.") or stripped.startswith("6.") \
           or stripped.startswith("7.") or stripped.startswith("8."):

            elements.append(Spacer(1, 12))
            elements.append(Paragraph(stripped, section_style))
            elements.append(Spacer(1, 10))
        else:
            elements.append(Paragraph(stripped, body_style))
            elements.append(Spacer(1, 5))

    if table_buffer:
        elements.append(render_table(table_buffer))

    doc.build(elements)

    print(f"✔ Enterprise PDF generated: {filename}")


########################################
# MAIN
########################################

def main():

    base_prompt = load_prompt()
    hosts = parse_html()

    for host in hosts:
        print("Analyzing:", host["hostname"])
        analysis = analyze_host(host, base_prompt)
        create_pdf(host["hostname"], analysis)

    print("All PDFs generated successfully.")


if __name__ == "__main__":
    main()