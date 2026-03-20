import os
from datetime import datetime

import google.generativeai as genai
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
# CONFIGURATION
########################################

HTML_FILE = "linux_host_health_report.html"

OUTPUT_DIR = "output"

MODEL = "gemini-pro"

API_KEY = "AIzaSyBSJZoxTcP2u_PxBSqROPxAO-crohQ0y-c"

if not API_KEY:
    raise Exception("Please set GEMINI_API_KEY in terminal")

genai.configure(api_key=API_KEY)

model = genai.GenerativeModel(MODEL)

os.makedirs(OUTPUT_DIR, exist_ok=True)


########################################
# PDF STYLES
########################################

styles = getSampleStyleSheet()

title_style = styles["Heading1"]

section_style = styles["Heading2"]

body_style = ParagraphStyle(
    name="BodyStyle",
    fontSize=10,
    leading=14
)

table_style = TableStyle([
    ("GRID", (0,0), (-1,-1), 0.5, black),
    ("BACKGROUND", (0,0), (-1,0), grey),
])


########################################
# PARSE HTML FILE
########################################

def parse_html():

    if not os.path.exists(HTML_FILE):

        raise FileNotFoundError(
            f"{HTML_FILE} not found in project folder"
        )

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

def build_prompt(host):

    return f"""
You are a senior Linux Production Support Engineer.

Generate report EXACTLY in this format:

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
Memory: {host['mem']} %
Load: {host['load']}

CPU Breach: {host['cpu_breach']}
Memory Breach: {host['mem_breach']}
Load Breach: {host['load_breach']}

Top CPU Processes:
{host['top_cpu']}

Top Memory Processes:
{host['top_mem']}

Details:
{host['details']}
"""


########################################
# GEMINI ANALYSIS
########################################

def analyze_host(host):

    try:

        prompt = build_prompt(host)

        response = model.generate_content(prompt)

        return response.text

    except Exception as e:

        return f"Analysis failed: {str(e)}"


########################################
# CREATE PDF
########################################

def create_pdf(hostname, analysis):

    filename = f"{OUTPUT_DIR}/{hostname}_analysis.pdf"

    doc = SimpleDocTemplate(filename)

    elements = []

    elements.append(
        Paragraph(f"HOST ANALYSIS: {hostname}", title_style)
    )

    elements.append(Spacer(1,12))

    lines = analysis.split("\n")

    for line in lines:

        line = line.strip()

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

    print(f"Generated PDF: {filename}")


########################################
# EMPTY REPORT
########################################

def create_empty_pdf():

    filename = f"{OUTPUT_DIR}/No_Overloaded_Hosts.pdf"

    doc = SimpleDocTemplate(filename)

    elements = []

    elements.append(
        Paragraph("Linux Host Health Report", title_style)
    )

    elements.append(Spacer(1,12))

    elements.append(

        Paragraph(
            f"No overloaded hosts<br/>{datetime.now()}",
            body_style
        )

    )

    doc.build(elements)


########################################
# MAIN
########################################

def main():

    print("Starting host analysis...")

    hosts = parse_html()

    if not hosts:

        create_empty_pdf()

        return

    for host in hosts:

        print(f"Analyzing: {host['hostname']}")

        analysis = analyze_host(host)

        create_pdf(host["hostname"], analysis)

    print("\nAll PDFs generated successfully.")


########################################

if __name__ == "__main__":

    main()