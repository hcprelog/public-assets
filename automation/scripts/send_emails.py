import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]

SIG = """

Dennis Hunter
President, H&C Precise Logistics LLC
SDVOSB | HUBZone Certified | Durham, NC
919-275-0598
dennis@hcprelog.com
hcprelog.com"""

# Tri City Logistics removed — INTERESTED, Chad replied 2026-06-03, call (423) 502-0803
emails = [
    {
        "to": "eccconline@gmail.com",
        "subject": "VA Hospital Courier Contract - Partnership Opportunity in Hampton, VA",
        "body": "Hi,\n\nMy name is Dennis Hunter, President of H&C Precise Logistics - we're an SDVOSB (Service-Disabled Veteran-Owned Small Business) and HUBZone certified federal contractor based in Durham, NC.\n\nI'm reaching out because we've identified an active VA hospital contract for courier and delivery services in the Hampton, Virginia area. It's a federal set-aside contract - meaning it's reserved specifically for veteran-owned businesses like ours to prime.\n\nHere's the opportunity in plain terms:\n\n- H&C wins the prime contract and handles all compliance, billing, and government paperwork\n- East Coast Courier Company runs the local routes in the Hampton Roads corridor - exactly what you're already doing\n- We pay you Net 30 once the government pays us - guaranteed federal money\n- No government contracting overhead on your end whatsoever\n\nYou've been serving the Hampton Roads area since 1999 and already work with major healthcare clients in the region. This is a natural extension of what your team does every day - just with a federal customer and a steady, predictable payment stream.\n\nThe deadline on this one is tight (early June), so I'd love to connect this week if you're open to it.\n\nWould you have 15 minutes for a quick call?" + SIG,
    },
    {
        "to": "info@courierva.com",
        "subject": "VA Hospital Courier Contract - Veteran-to-Veteran Partnership Opportunity",
        "body": "Hi Bruce,\n\nMy name is Dennis Hunter - I'm a fellow veteran and President of H&C Precise Logistics LLC, an SDVOSB and HUBZone certified federal contractor based in Durham, NC.\n\nI'm reaching out veteran-to-veteran because we've identified an active VA hospital contract for courier services in the Hampton, Virginia area (Solicitation 36C24626Q0536). It's set aside for veteran-owned businesses - which means H&C has the certification to prime it, but we need a strong local execution partner in Hampton Roads to run the routes.\n\nHere's how it works:\n\n- H&C holds the prime contract - we handle all the compliance, billing, and government requirements\n- You run the routes locally, exactly as you do now for your current clients\n- We pay you Net 30 once the government pays us - steady, guaranteed income\n- If you're not SAM.gov registered yet, we walk you through it at no cost\n\nThe deadline on this solicitation is early June, so time is short. I'd love 15 minutes to walk you through the full picture - veteran to veteran.\n\nCan we connect this week?" + SIG,
    },
    {
        "to": "info@allstatecouriers.com",
        "subject": "SDVOSB Teaming Opportunity - Active VA Courier Solicitation in Bedford, MA",
        "body": "Hi,\n\nMy name is Dennis Hunter, President of H&C Precise Logistics - we're an SDVOSB and HUBZone certified federal contractor based in Durham, NC.\n\nI'm reaching out because we have an active VA solicitation for lab courier services in the Bedford, Massachusetts area (Solicitation 36C24126Q0174) that's set aside for SDVOSB-certified companies. I know Allstate Courier Systems is already federally certified with WOSB status - that puts you ahead of most competitors.\n\nThe gap is the SDVOSB set-aside. That's where we come in.\n\nTwo ways we can work together:\n\nOption 1 - Immediate Contract Revenue: We team as prime (H&C) and execution sub (Allstate). You run the routes in New England as you already do - we handle the federal compliance and billing, pay you Net 30.\n\nOption 2 - Build Your Own Pipeline: Our PRIME READY plan ($797/mo) gives you teaming access on every SDVOSB bid we pursue plus the full roadmap to build your own federal pipeline.\n\nEither way, the Bedford VA solicitation is a real opportunity with a June 15 deadline. I'd love a 15-minute call to lay it all out." + SIG,
    },
]

server = smtplib.SMTP("smtp.gmail.com", 587)
server.starttls()
server.login(GMAIL_USER, GMAIL_APP_PASSWORD)

for email in emails:
    msg = MIMEMultipart("alternative")
    msg["From"] = f"H&C Precise Logistics <{GMAIL_USER}>"
    msg["To"] = email["to"]
    msg["Subject"] = email["subject"]
    msg.attach(MIMEText(email["body"], "plain"))
    server.sendmail(GMAIL_USER, email["to"], msg.as_string())
    print(f"SENT: {email['subject']} -> {email['to']}")

server.quit()
print("All emails sent.")
