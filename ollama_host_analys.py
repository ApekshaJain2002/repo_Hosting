import os
import requests
from datetime import datetime
from bs4 import BeautifulSoup

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import black, grey


########################################
# CONFIG
########################################

HTML_FILE = "linux_host_health_report.html"

OUTPUT_DIR = "output"

OLLAMA_URL = "http://localhost:11434/api/generate"

MODEL = "llama3"

os.makedirs(OUTPUT_DIR, exist_ok=True)


########################################
# STYLES
########################################

styles = getSampleStyleSheet()

title_style = styles["Heading1"]

section_style = styles["Heading2"]

body_style = ParagraphStyle(
    name="body",
    fontSize=10,
    leading=14
)

table_style = TableStyle([
    ("GRID", (0,0), (-1,-1), 0.5, black),
    ("BACKGROUND", (0,0), (-1,0), grey),
])


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
# BUILD PROMPT (STRICT ENTERPRISE)
########################################

def build_prompt(host):

    return f"""
You are a senior Linux Production Support Engineer.

Analyze host and generate report EXACTLY in this format:

HOST ANALYSIS: {host['hostname']}

1. QUICK HEALTH STATUS

2. SYSTEM METRICS

3. TOP CPU CONSUMERS

4. TOP MEMORY CONSUMERS

5. APPLICATION STACK SUMMARY

6. ISSUES & CONCERNS

7. ACTION PLAN

8. SUMMARY & KEY TAKEAWAYS


DATA:

CPU: {host['cpu']} %
MEM: {host['mem']} %
LOAD: {host['load']}

CPU BREACH: {host['cpu_breach']}
MEM BREACH: {host['mem_breach']}
LOAD BREACH: {host['load_breach']}

TOP CPU PROCESSES:
{host['top_cpu']}

TOP MEMORY PROCESSES:
{host['top_mem']}

DETAILS:
{host['details']}

Strict requirements:

Follow exact section headings.
Use professional production support tone.
Use structured analysis.
Do not skip sections.
"""


########################################
# CALL OLLAMA
########################################

def analyze_host(host):

    prompt = build_prompt(host)

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
# CREATE PDF
########################################

def create_pdf(hostname, analysis):

    filename = f"{OUTPUT_DIR}/{hostname}_analysis.pdf"

    doc = SimpleDocTemplate(filename)

    elements = []

    elements.append(Paragraph(f"HOST ANALYSIS: {hostname}", title_style))

    elements.append(Spacer(1,12))

    lines = analysis.split("\n")

    for line in lines:

        line=line.strip()

        if not line:
            continue

        if "|" in line:

            cols = line.split("|")

            table = Table([cols])

            table.setStyle(table_style)

            elements.append(table)

        elif line.startswith(tuple(str(i)+"." for i in range(1,10))):

            elements.append(Paragraph(line, section_style))

        else:

            elements.append(Paragraph(line, body_style))

        elements.append(Spacer(1,6))

    doc.build(elements)

    print("Generated:", filename)


########################################
# EMPTY PDF
########################################

def empty_pdf():

    filename = f"{OUTPUT_DIR}/No_Overloaded_Hosts.pdf"

    doc = SimpleDocTemplate(filename)

    elements=[]

    elements.append(Paragraph("Linux Host Health Report", title_style))

    elements.append(Spacer(1,12))

    elements.append(

        Paragraph(

            f"No overloaded hosts detected<br/>Timestamp: {datetime.now()}",

            body_style

        )

    )

    doc.build(elements)


########################################
# MAIN
########################################

def main():

    hosts = parse_html()

    if not hosts:

        empty_pdf()

        return

    for host in hosts:

        print("Analyzing:", host["hostname"])

        analysis = analyze_host(host)

        create_pdf(host["hostname"], analysis)

    print("All reports generated.")


if __name__ == "__main__":

    main()