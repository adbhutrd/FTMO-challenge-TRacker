#!/usr/bin/env python3
"""
Portfolio builder - creates files for freelance platforms
"""
import os

BASE = os.path.expanduser("~/income")

# FIVERR GIG TEMPLATE
fiverr_gig = """# Basic Web App Security Check - $100

I will perform reconnaissance and vulnerability scanning on your web application:
- Subdomain enumeration
- Open port scan
- Common vulnerability check (XSS, SQLi, misconfig)
- PDF report with findings

Timeline: 24 hours
Revisions: 2"""

# UPWORK PROPOSAL
upwork_prop = """Hi, I'm Adbhut with MSc Cyber Security (Distinction). I can:
- Run reconnaissance and find attack surface
- Check for OWASP Top 10 vulnerabilities
- Provide actionable remediation steps
- Deliver report within 3 days

Available for immediate start. Let's discuss scope."""

# BUG BOUNTY REPORT TEMPLATE
report = """# Security Assessment Report

## Executive Summary
{findings} vulnerabilities identified across {scope} application.

## Technical Findings
### {vuln_name} - {severity}
- Description: {desc}
- Evidence: {evidence}
- Remediation: {remediation}

## Scope
- Target: {target}
- Date: {date}
  
## Tester
Adbhut Ram Das - MSc Cyber Security (Distinction)"""

for name, content in [
    ("fiverr_gig.txt", fiverr_gig),
    ("upwork_proposal.txt", upwork_prop),
    ("report_template.md", report)
]:
    with open(f"{BASE}/{name}", "w") as f:
        f.write(content)
    print(f"Created: {BASE}/{name}")

print("\nReady for platform upload")