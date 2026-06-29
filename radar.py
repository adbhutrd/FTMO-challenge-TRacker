#!/usr/bin/env python3
"""
🔍 Industry Research Radar — Security Job Scraper for Netherlands
===============================================================
Scrapes security research and cybersecurity job listings from top
Netherlands tech companies and sends SMS alerts when new matching
roles appear.

Supported companies:
  • ASML (Veldhoven)        — Chip fabrication security
  • Philips (Eindhoven)     — Medical device / IoT security
  • ING (Amsterdam)         — Financial / app security
  • Booking.com (Amsterdam) — Web security, infrastructure
  • Adyen (Amsterdam)       — Payment security
  • Elastic (Amsterdam)     — Search & observability security
  • Mollie (Amsterdam)      — Payment processing
  • KPN (Rotterdam)         — Telecom & network security
  • TomTom (Amsterdam)      — Navigation tech (Phase 2)
  • ABN AMRO (Amsterdam)    — Banking security (Phase 2)
  • NCSC (The Hague)        — Dutch gov cyber security (Phase 2)

Matching keywords: security, cybersecurity, infosec, researcher,
  vulnerability, pentest, threat, privacy, compliance, devsecops

Usage:
  python3 radar.py                         # Run full scan + SMS alerts
  python3 radar.py --dry-run               # Show matches without SMS
  python3 radar.py --list-companies        # Show available companies
  python3 radar.py --status                # Show last run stats
"""

import hashlib
import json
import os
import re
import sqlite3
import sys
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# For HTTP requests
import urllib.request
import urllib.error

# Note: web scraping for JS-rendered career sites (ASML, Booking.com)
# is a Phase 1 limitation. These companies return 0 results until
# a headless browser is added in Phase 2.
#
# Philips and ING use sitemap-based fetching (job URLs in sitemaps
# contain descriptive slugs that can be keyword-filtered).

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("radar")

# ── Config ──────────────────────────────────────────────────────────
DATA_DIR = Path.home() / "radar_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "radar.db"
LOG_PATH = DATA_DIR / "radar.log"
STATE_PATH = DATA_DIR / "state.json"

# Keywords that match security/research roles
# HIGH priority: must appear in TITLE to count
TITLE_KEYWORDS = [
    "security researcher", "security engineer", "security analyst",
    "security architect", "security consultant", "security manager",
    "security specialist", "security lead", "security expert",
    "security officer", "chief security", "cso", "ciso",
    "application security", "appsec",
    "penetration test", "pentest", "ethical hack",
    "vulnerability researcher", "vulnerability analyst",
    "threat analyst", "threat hunter", "threat intelligence",
    "incident responder", "incident response",
    "soc analyst", "soc manager", "security operations",
    "cybersecurity", "cyber security",
    "red team", "blue team", "purple team",
    "devsecops", "secure development",
    "cryptography", "cryptographer",
    "malware analyst", "reverse engineer", "exploit developer",
    "infosec", "information security",
    "cloud security", "network security",
    "identity security", "access management", "iam",
    "fraud analyst", "fraud investigator",
    "privacy engineer", "privacy analyst",
    "security audit", "security review",
]

# Exclusion keywords — roles that mention security but aren't the focus
EXCLUDE_KEYWORDS = [
    "security guard", "security patrol",
    "physical security", "security driver", "security agent",
    "security clearance", "warehouse security",
    "security assistant",
]

# Sitemap keywords — matched against URL slugs for sitemap-based companies
# These are broader since they match URL path components like 'risk', 'compliance', 'fraud'
SITEMAP_KEYWORDS = [
    # Core security
    "security", "cyber", "cybersecurity", "infosec",
    # Risk & compliance
    "risk", "compliance", "audit", "governance",
    # Threat & incident
    "threat", "incident", "hunt", "forensic",
    # Vulnerability & testing
    "vulnerability", "penetration", "pentest", "ethical",
    # Cryptography
    "cryptograph", "encrypt",
    # Privacy
    "privacy", "data-protection",
    # Fraud
    "fraud", "anti-fraud",
    # App security
    "application-security", "appsec", "devsecops",
    # Architecture
    "security-architect",
    # Identity & access
    "identity", "access-management", "iam",
    # Monitoring
    "soc", "siem", "monitoring",
    # Other security roles
    "information-security", "it-security", "network-security",
    "cloud-security", "product-security",
    "malware", "ransomware",
    # Research
    "researcher", "research-scientist",
]

# Sitemap exclusion keywords — matched against URL slugs
SITEMAP_EXCLUDE = [
    "asset-securitisation",  # Financial securities, not security jobs
    "securities-settlement",
    "securities-operations",
]

# ── Company Configurations ──────────────────────────────────────────

COMPANIES: Dict[str, Dict] = {
    "ASML": {
        "name": "ASML",
        "location": "Veldhoven",
        "url": "https://www.asml.com/en/careers",
        "search_url": "https://www.asml.com/en/careers/find-your-job",
        "type": "web",
        "icon": "🔬",
    },
    "Philips": {
        "name": "Philips",
        "location": "Eindhoven",
        "url": "https://www.careers.philips.com",
        "search_url": "https://www.careers.philips.com/global/en/search-results",
        "type": "sitemap",
        "sitemap_urls": [
            "https://www.careers.philips.com/sitemap2.xml",
            "https://www.careers.philips.com/sitemap3.xml",
        ],
        "url_pattern": "/global/en/job/",
        "icon": "💡",
    },
    "ING": {
        "name": "ING",
        "location": "Amsterdam",
        "url": "https://ing.jobs",
        "search_url": "https://careers.ing.com/en/search-jobs",
        "type": "sitemap",
        "sitemap_urls": ["https://careers.ing.com/sitemap.xml"],
        "url_pattern": "/en/job/",
        "icon": "🏦",
    },
    "Booking.com": {
        "name": "Booking.com",
        "location": "Amsterdam",
        "url": "https://booking.com/careers",
        "search_url": "https://careers.booking.com/search",
        "type": "web",
        "icon": "🏨",
    },
    "Adyen": {
        "name": "Adyen",
        "location": "Amsterdam",
        "url": "https://www.adyen.com/careers",
        "api_url": "https://boards-api.greenhouse.io/v1/boards/adyen/jobs",
        "type": "greenhouse",
        "icon": "💳",
    },
    "Elastic": {
        "name": "Elastic",
        "location": "Amsterdam",
        "url": "https://www.elastic.co/careers",
        "api_url": "https://boards-api.greenhouse.io/v1/boards/elastic/jobs",
        "type": "greenhouse",
        "icon": "🔎",
    },
    "Mollie": {
        "name": "Mollie",
        "location": "Amsterdam",
        "url": "https://www.mollie.com/careers",
        "api_url": "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams",
        "graphql_query": '{"operationName":"ApiJobBoardWithTeams","variables":{"organizationHostedJobsPageName":"mollie"},"query":"query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) { jobBoard: jobBoardWithTeams(organizationHostedJobsPageName: $organizationHostedJobsPageName) { teams { id name } jobPostings { id title teamId locationId locationName workplaceType employmentType secondaryLocations { locationId locationName } } __typename } }"}',
        "type": "graphql",
        "icon": "💸",
    },
    "KPN": {
        "name": "KPN",
        "location": "Rotterdam",
        "url": "https://www.kpn.com/vacatures",
        "api_url": "https://api.smartrecruiters.com/v1/companies/kpn/postings",
        "type": "smartrecruiters",
        "icon": "📡",
    },
    "TomTom": {
        "name": "TomTom",
        "location": "Amsterdam",
        "url": "https://www.tomtom.com/careers",
        "search_url": "https://www.tomtom.com/careers/joboverview/",
        "type": "web",
        "icon": "🗺️",
    },
    "ABN AMRO": {
        "name": "ABN AMRO",
        "location": "Amsterdam",
        "url": "https://www.abnamro.nl/carriere",
        "search_url": "https://abnamro.wd3.myworkdayjobs.com/ABNAMRO",
        "type": "web",
        "icon": "🏛️",
    },
    "NCSC": {
        "name": "NCSC",
        "location": "The Hague",
        "url": "https://www.ncsc.nl/vacatures",
        "search_url": "https://www.werkenbijdeoverheid.nl/vacatures?q=NCSC+cyber+security",
        "type": "web",
        "icon": "🛡️",
    },
}


# ═══════════════════════════════════════════════════════════════════════
#  DATABASE — Track seen jobs
# ═══════════════════════════════════════════════════════════════════════

def init_db():
    """Initialize the SQLite database for tracking jobs."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT,
            location TEXT,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            active INTEGER DEFAULT 1
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scan_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_time TEXT NOT NULL,
            company TEXT,
            jobs_found INTEGER,
            new_matches INTEGER,
            alerts_sent INTEGER
        )
    """)
    conn.commit()
    return conn


def is_job_seen(conn, job_id: str) -> bool:
    """Check if a job has been seen before."""
    cur = conn.execute("SELECT 1 FROM jobs WHERE id = ?", (job_id,))
    return cur.fetchone() is not None


def mark_job_seen(conn, job_id: str, company: str, title: str, url: str = "", location: str = ""):
    """Record a job as seen in the database."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT OR REPLACE INTO jobs (id, company, title, url, location, first_seen, last_seen, active)
        VALUES (?, ?, ?, ?, ?, 
            COALESCE((SELECT first_seen FROM jobs WHERE id = ?), ?),
            ?, 1)
    """, (job_id, company, title, url, location, job_id, now, now))
    conn.commit()


def log_scan(conn, company: str = None, jobs_found: int = 0, new_matches: int = 0, alerts_sent: int = 0):
    """Log a scan run."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO scan_log (scan_time, company, jobs_found, new_matches, alerts_sent) VALUES (?, ?, ?, ?, ?)",
        (now, company or "ALL", jobs_found, new_matches, alerts_sent),
    )
    conn.commit()


def get_stats(conn) -> dict:
    """Get scan statistics."""
    total_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    active_jobs = conn.execute("SELECT COUNT(*) FROM jobs WHERE active = 1").fetchone()[0]
    total_scans = conn.execute("SELECT COUNT(*) FROM scan_log").fetchone()[0]
    last_scan = conn.execute(
        "SELECT scan_time FROM scan_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    by_company = conn.execute(
        "SELECT company, COUNT(*) FROM jobs WHERE active = 1 GROUP BY company ORDER BY COUNT(*) DESC"
    ).fetchall()
    return {
        "total_jobs": total_jobs,
        "active_jobs": active_jobs,
        "total_scans": total_scans,
        "last_scan": last_scan[0] if last_scan else "Never",
        "by_company": dict(by_company),
    }


# ═══════════════════════════════════════════════════════════════════════
#  MATCHING ENGINE
# ═══════════════════════════════════════════════════════════════════════

def matches_keywords(title: str, body: str = "") -> Tuple[bool, List[str]]:
    """
    Check if a job matches security/research keywords.
    
    Matching is done against the job TITLE only (not the full description body)
    to prevent false positives from job descriptions that mention "security"
    in passing (e.g., "Account Manager" whose description discusses security policy).
    """
    title_lower = title.lower()
    body_lower = body.lower() if body else ""
    matched = []
    
    # Check exclusion first
    for ex in EXCLUDE_KEYWORDS:
        if ex.lower() in title_lower or (body and ex.lower() in body_lower):
            return False, []
    
    # Check title keywords (strong signal - must match in title)
    for kw in TITLE_KEYWORDS:
        # Only match against the title, not the body
        # This prevents false positives from job descriptions mentioning "security"
        if kw.lower() in title_lower:
            matched.append(kw)
    
    # Check if at least one TITLE_KEYWORD matched
    has_strong_match = len(matched) > 0
    
    return has_strong_match, matched


# ═══════════════════════════════════════════════════════════════════════
#  FETCHERS — Get jobs from each company
# ═══════════════════════════════════════════════════════════════════════

def _fetch_json(url: str, timeout: int = 15) -> Optional[dict]:
    """Fetch JSON from a URL with error handling."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        logger.warning(f"  ⚠️ Fetch failed: {e}")
        return None


def _fetch_html(url: str, timeout: int = 15) -> Optional[str]:
    """Fetch HTML from a URL."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        logger.warning(f"  ⚠️ Fetch failed: {e}")
        return None


def _simple_extract_jobs(html: str, company: str) -> List[Dict]:
    """
    Simple job extraction from HTML.
    Looks for common patterns in career page HTML.
    Returns list of dicts with keys: id, title, url, location
    """
    jobs = []
    # Try to find job listings in HTML
    # Patterns: <a href=...job...>Title</a>, data-job-id, job-title classes
    text_lower = html.lower()
    
    # Look for job-related sections
    lines = html.split("\n")
    for i, line in enumerate(lines):
        # Look for anchor tags with job-related href
        if 'href=' in line and ('job' in line.lower() or 'career' in line.lower() or 'vacancy' in line.lower()):
            # Try to extract title from nearby text
            href_start = line.find('href="')
            if href_start == -1:
                href_start = line.find("href='")
                quote = "'"
            else:
                quote = '"'
            
            if href_start >= 0:
                href_start += 6
                href_end = line.find(quote, href_start)
                if href_end > href_start:
                    url = line[href_start:href_end]
                    # Look for title in the same line or next few
                    title = ""
                    # Check if there's text after the link
                    text_after = line[href_end + 1:]
                    # Look for >Text</a> pattern
                    gt_pos = text_after.find(">")
                    if gt_pos >= 0:
                        lt_pos = text_after.find("</a>", gt_pos)
                        if lt_pos > gt_pos:
                            title = text_after[gt_pos + 1:lt_pos].strip()
                    
                    if title and url:
                        job_id = f"{company}_{hashlib.md5(url.encode()).hexdigest()[:12]}"
                        jobs.append({
                            "id": job_id,
                            "title": title,
                            "url": url if url.startswith("http") else f"https://www.{company.lower()}.com{url}",
                            "location": "",
                        })
    
    # Deduplicate by title
    seen = set()
    unique = []
    for j in jobs:
        key = j["title"].lower().strip()
        if key and key not in seen and len(key) > 5:
            seen.add(key)
            unique.append(j)
    
    return unique


def _slug_to_title(slug: str) -> str:
    """Convert a URL slug to a human-readable job title.
    
    E.g., 'senior-information-security-manager' -> 'Senior Information Security Manager'
    """
    # Remove leading numbers (e.g., job IDs)
    slug = re.sub(r'^\d+-', '', slug)
    # Split on hyphens and capitalize each word
    words = slug.replace('-', ' ').replace('_', ' ').split()
    # Capitalize properly (keep acronyms like IAM, SOC uppercase)
    result = []
    for w in words:
        if w.upper() == w and len(w) <= 4:
            result.append(w.upper())
        else:
            result.append(w.capitalize())
    return ' '.join(result)


def _fetch_sitemap_jobs(sitemap_urls: List[str], url_pattern: str, company: str) -> List[Dict]:
    """
    Parse sitemap XML files to find job URLs matching security keywords.
    
    For companies that serve job listings via SPAs (JS-rendered), the sitemap
    contains all job URLs with descriptive slugs. We filter by keywords in
    the URL path and extract the job title from the slug.
    """
    jobs = []
    seen_slugs = set()
    
    for sitemap_url in sitemap_urls:
        xml = _fetch_html(sitemap_url)
        if not xml:
            continue
        
        # Use regex to extract URLs (works reliably with and without namespaces)
        urls = re.findall(r'<loc>([^<]+)</loc>', xml)
        
        for url in urls:
            try:
                if url_pattern not in url:
                    continue
                
                # Extract the slug from the URL (last path component before any ID)
                path = url.split('?')[0]
                parts = [p for p in path.rstrip('/').split('/') if p]
                
                # Find the best slug - look for the job title in the URL
                slug = None
                for part in reversed(parts):
                    if any(kw.replace(' ', '-') in part.lower() for kw in SITEMAP_KEYWORDS):
                        slug = part
                        break
                
                # If no keyword found in any part, use the last non-numeric segment
                if not slug:
                    for part in reversed(parts):
                        if not part.isdigit():
                            slug = part
                            break
                
                if not slug:
                    continue
                
                # Skip excluded slugs
                slug_lower = slug.lower()
                if any(ex in slug_lower for ex in SITEMAP_EXCLUDE):
                    continue
                
                # Check if slug matches any security keyword
                matched_kw = []
                for kw in SITEMAP_KEYWORDS:
                    if kw.lower() in slug_lower:
                        matched_kw.append(kw)
                
                if not matched_kw:
                    continue
                
                # Deduplicate by slug
                if slug_lower in seen_slugs:
                    continue
                seen_slugs.add(slug_lower)
                
                title = _slug_to_title(slug)
                job_id = f"{company.lower()}_{slug_lower[:50]}_{hashlib.md5(url.encode()).hexdigest()[:10]}"
                
                jobs.append({
                    "id": job_id,
                    "title": title,
                    "url": url,
                    "location": "",
                    "keywords": matched_kw[:5],
                })
            except Exception as e:
                logger.warning(f"  ⚠️ Error processing sitemap URL: {e}")
                continue
    
    return jobs


def fetch_booking(company: str) -> List[Dict]:
    """Fetch jobs from Booking.com.
    
    Note: Booking.com's career site is behind Cloudflare. The autocomplete API
    works via browser but not curl. Uses web scraping for now. Returns 0 results
    until a headless browser is added in Phase 2.
    """
    config = COMPANIES[company]
    html = _fetch_html(config["search_url"])
    if not html:
        return []
    
    jobs = _simple_extract_jobs(html, company)
    result = []
    for j in jobs:
        is_match, keywords = matches_keywords(j["title"], "")
        if is_match:
            j["keywords"] = keywords
            result.append(j)
    return result


def fetch_adyen(company: str) -> List[Dict]:
    """Fetch jobs from Adyen via Greenhouse API."""
    config = COMPANIES[company]
    data = _fetch_json(config["api_url"] + "?content=true&per_page=100")
    if not data:
        return []
    
    jobs = []
    for job in data.get("jobs", []):
        title = job.get("title", "")
        body = job.get("content", "")
        locs = job.get("offices", [])
        location = ", ".join([f"{o.get('city', '')}, {o.get('country', '')}" for o in locs]) if locs else ""
        
        is_match, keywords = matches_keywords(title, body)
        if not is_match:
            continue
        
        job_id = f"adyen_{job.get('id', hashlib.md5(title.encode()).hexdigest()[:8])}"
        jobs.append({
            "id": str(job_id),
            "title": title,
            "url": job.get("absolute_url", config["url"]),
            "location": location,
            "keywords": keywords,
        })
    
    return jobs


def fetch_asml(company: str) -> List[Dict]:
    """Fetch jobs from ASML.
    
    ASML uses a Next.js SPA for its careers site. Job listings are loaded
    dynamically via API calls. sitemap-*.xml and job_posting-sitemap.xml don't
    contain job URLs. Requires a headless browser in Phase 2.
    """
    config = COMPANIES[company]
    html = _fetch_html(config["url"])
    if not html:
        return []
    
    # Try to extract jobs from the HTML anyway
    jobs = _simple_extract_jobs(html, company)
    result = []
    for j in jobs:
        is_match, keywords = matches_keywords(j["title"], "")
        if is_match:
            j["keywords"] = keywords
            result.append(j)
    return result


def fetch_philips(company: str) -> List[Dict]:
    """Fetch jobs from Philips via sitemap parsing.
    
    Philips' careers site (Phenom platform) is JS-rendered. We use their
    sitemap2.xml and sitemap3.xml which contain all job URLs with descriptive
    slugs. Filter by security keywords in the URL path.
    """
    config = COMPANIES[company]
    return _fetch_sitemap_jobs(config["sitemap_urls"], config["url_pattern"], company)


def fetch_ing(company: str) -> List[Dict]:
    """Fetch jobs from ING via sitemap parsing.
    
    ING's careers site (Radancy/TalentBrew) uses server-side rendering but
    job data isn't easily parseable. We use their sitemap.xml which contains
    all job URLs with descriptive slugs (e.g., 'senior-security-engineer').
    Filter by security keywords in the URL slug.
    """
    config = COMPANIES[company]
    return _fetch_sitemap_jobs(config["sitemap_urls"], config["url_pattern"], company)


def fetch_elastic(company: str) -> List[Dict]:
    """Fetch jobs from Elastic via Greenhouse API."""
    config = COMPANIES[company]
    data = _fetch_json(config["api_url"] + "?content=true&per_page=100")
    if not data:
        return []
    
    jobs = []
    for job in data.get("jobs", []):
        title = job.get("title", "")
        body = job.get("content", "")
        locs = job.get("offices", [])
        location = ", ".join([f"{o.get('city', '')}, {o.get('country', '')}" for o in locs]) if locs else ""
        
        is_match, keywords = matches_keywords(title, body)
        if not is_match:
            continue
        
        job_id = f"elastic_{job.get('id', hashlib.md5(title.encode()).hexdigest()[:8])}"
        jobs.append({
            "id": str(job_id),
            "title": title,
            "url": job.get("absolute_url", config["url"]),
            "location": location,
            "keywords": keywords,
        })
    
    return jobs


def _fetch_graphql(url: str, query_body: str, timeout: int = 15) -> Optional[dict]:
    """Fetch data from a GraphQL endpoint."""
    try:
        data = json.loads(query_body) if isinstance(query_body, str) else query_body
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Content-Type": "application/json",
        })
        req.data = json.dumps(data).encode()
        req.method = "POST"
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        logger.warning(f"  ⚠️ GraphQL fetch failed: {e}")
        return None


def fetch_mollie(company: str) -> List[Dict]:
    """Fetch jobs from Mollie via Ashby GraphQL API."""
    config = COMPANIES[company]
    data = _fetch_graphql(config["api_url"], config["graphql_query"])
    if not data or "data" not in data:
        return []
    
    board = data["data"].get("jobBoard", {})
    postings = board.get("jobPostings", [])
    
    jobs = []
    for job in postings:
        title = job.get("title", "")
        location = job.get("locationName", "") or ""
        url = f"https://jobs.ashbyhq.com/mollie"  # Ashby doesn't provide per-job URLs in API
        
        is_match, keywords = matches_keywords(title, "")
        if not is_match:
            continue
        
        job_id = f"mollie_{job.get('id', hashlib.md5(title.encode()).hexdigest()[:8])}"
        jobs.append({
            "id": str(job_id),
            "title": title,
            "url": url,
            "location": location,
            "keywords": keywords,
        })
    
    return jobs


def fetch_kpn(company: str) -> List[Dict]:
    """Fetch jobs from KPN via SmartRecruiters API."""
    config = COMPANIES[company]
    data = _fetch_json(config["api_url"] + "?limit=100")
    if not data:
        return []
    
    jobs = []
    for job in data.get("content", []):
        title = job.get("name", "")
        location = job.get("location", {}).get("city", "") or ""
        url = job.get("applyUrl", "") or job.get("ref", "")
        if url and not url.startswith("http"):
            url = f"https://jobs.smartrecruiters.com/kpn/{url}"
        
        is_match, keywords = matches_keywords(title, "")
        if not is_match:
            continue
        
        job_id = f"kpn_{job.get('id', hashlib.md5(title.encode()).hexdigest()[:8])}"
        jobs.append({
            "id": str(job_id),
            "title": title,
            "url": url if url else config["url"],
            "location": location,
            "keywords": keywords,
        })
    
    return jobs


def fetch_tomtom(company: str) -> List[Dict]:
    """Fetch jobs from TomTom.
    
    TomTom uses a JS-rendered career site. No public API or sitemap found.
    Requires a headless browser in Phase 2.
    """
    config = COMPANIES[company]
    html = _fetch_html(config["search_url"])
    if not html:
        return []
    
    jobs = _simple_extract_jobs(html, company)
    result = []
    for j in jobs:
        is_match, keywords = matches_keywords(j["title"], "")
        if is_match:
            j["keywords"] = keywords
            result.append(j)
    return result


def fetch_abnamro(company: str) -> List[Dict]:
    """Fetch jobs from ABN AMRO.
    
    ABN AMRO uses Workday which was in maintenance mode during investigation.
    Requires a headless browser or Workday API in Phase 2.
    """
    config = COMPANIES[company]
    html = _fetch_html(config["search_url"])
    if not html:
        return []
    
    jobs = _simple_extract_jobs(html, company)
    result = []
    for j in jobs:
        is_match, keywords = matches_keywords(j["title"], "")
        if is_match:
            j["keywords"] = keywords
            result.append(j)
    return result


def fetch_ncsc(company: str) -> List[Dict]:
    """Fetch jobs from NCSC.
    
    NCSC vacancies are listed on the Dutch government portal (werkenbijdeoverheid.nl).
    No public API available. Requires a headless browser in Phase 2.
    """
    config = COMPANIES[company]
    html = _fetch_html(config["search_url"])
    if not html:
        return []
    
    jobs = _simple_extract_jobs(html, company)
    result = []
    for j in jobs:
        is_match, keywords = matches_keywords(j["title"], "")
        if is_match:
            j["keywords"] = keywords
            result.append(j)
    return result


# ── Fetcher registry ────────────────────────────────────────────────

FETCHERS = {
    "ASML": fetch_asml,
    "Philips": fetch_philips,
    "ING": fetch_ing,
    "Booking.com": fetch_booking,
    "Adyen": fetch_adyen,
    "Elastic": fetch_elastic,
    "Mollie": fetch_mollie,
    "KPN": fetch_kpn,
    "TomTom": fetch_tomtom,
    "ABN AMRO": fetch_abnamro,
    "NCSC": fetch_ncsc,
}


# ═══════════════════════════════════════════════════════════════════════
#  SMS ALERTS
# ═══════════════════════════════════════════════════════════════════════

def load_env_sms_config() -> dict:
    """Load SMS config from .env.sms if available."""
    env_path = Path.home() / ".env.sms"
    config = {"phone": "", "provider": "twilio"}
    if env_path.exists():
        for line in env_path.read_text().split("\n"):
            if "=" in line:
                k, v = line.strip().split("=", 1)
                if k == "SMS_DEFAULT_PHONE":
                    config["phone"] = v.strip('"').strip("'")
                elif k == "SMS_PROVIDER":
                    config["provider"] = v.strip('"').strip("'")
    return config


def send_sms_alert(phone: str, company: str, job: dict) -> bool:
    """Send an SMS alert about a new matching job."""
    title = job["title"][:80]
    location = job.get("location", "") or ""
    url = job.get("url", "")
    keywords = ", ".join(job.get("keywords", [])[:3])
    
    message = (
        f"🔍 NEW: {company}\n"
        f"{title}\n"
        f"{location}\n"
        f"🔑 {keywords}\n"
        f"{url}"
    )
    
    try:
        import urllib.parse
        params = urllib.parse.urlencode({
            "phone": phone,
            "message": message[:160],
            "immediate": "true",
        })
        
        # Try the SMS gateway first
        req = urllib.request.Request(
            f"http://localhost:8765/send?{params}",
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5):
                logger.info(f"  ✅ SMS alert sent for: {title[:50]}")
                return True
        except urllib.error.URLError:
            # Gateway offline — use Twilio directly if available
            logger.info("  ⚠️ SMS gateway offline, skipping SMS")
            # Log the alert
            log_dir = DATA_DIR / "alerts"
            log_dir.mkdir(parents=True, exist_ok=True)
            alert_file = log_dir / f"alerts_{datetime.now().strftime('%Y%m%d')}.log"
            with open(alert_file, "a") as f:
                f.write(f"{datetime.now().isoformat()} | {company} | {title} | {url}\n")
            logger.info(f"  📝 Alert logged to {alert_file}")
            return False
    except Exception as e:
        logger.warning(f"  ⚠️ SMS send failed: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════
#  MAIN SCAN LOOP
# ═══════════════════════════════════════════════════════════════════════

def run_scan(dry_run: bool = False, companies: Optional[List[str]] = None):
    """Run a full scan of all companies."""
    conn = init_db()
    sms_config = load_env_sms_config()
    phone = sms_config.get("phone", "")
    
    logger.info(f"{'─' * 50}")
    logger.info("🔍 INDUSTRY RESEARCH RADAR — Scan Starting")
    logger.info(f"{'─' * 50}")
    logger.info(f"  SMS alerts: {'✅ ON' if phone and not dry_run else '⏸️ OFF'}")
    logger.info(f"  Dry run: {'✅' if dry_run else '❌'}")
    logger.info(f"  Phone: {phone or 'Not configured'}")
    logger.info("")
    
    total_new = 0
    total_alerts = 0
    total_jobs = 0
    
    target_companies = companies or list(COMPANIES.keys())
    
    for company_name in target_companies:
        if company_name not in FETCHERS:
            logger.warning(f"  ⚠️ No fetcher for {company_name}")
            continue
        
        fetcher = FETCHERS[company_name]
        config = COMPANIES[company_name]
        
        logger.info(f"{config['icon']} {company_name} ({config['location']})...")
        
        try:
            jobs = fetcher(company_name)
        except Exception as e:
            logger.error(f"  ❌ Fetcher failed: {e}")
            log_scan(conn, company_name, 0, 0, 0)
            continue
        
        total_jobs += len(jobs)
        logger.info(f"  📋 {len(jobs)} matching jobs found")
        
        for job in jobs:
            job_id = job["id"]
            
            if not is_job_seen(conn, job_id):
                total_new += 1
                mark_job_seen(conn, job_id, company_name, job["title"], job.get("url", ""), job.get("location", ""))
                
                kw_display = ", ".join(job.get("keywords", [])[:3])
                logger.info(f"  🆕 NEW: {job['title'][:70]}")
                logger.info(f"        {kw_display} | {job.get('url', '')[:60]}")
                
                if phone and not dry_run:
                    send_sms_alert(phone, company_name, job)
                    total_alerts += 1
        
        # Count how many of these jobs are actually new (not seen before)
        new_this_company = sum(1 for j in jobs if not is_job_seen(conn, j["id"]))
        log_scan(conn, company_name, len(jobs), new_this_company, 0)
        print()
    
    # Summary
    logger.info(f"{'─' * 50}")
    logger.info(f"📊 SCAN SUMMARY")
    logger.info(f"  Companies scanned: {len(target_companies)}")
    logger.info(f"  Total matching jobs found: {total_jobs}")
    logger.info(f"  New jobs discovered: {total_new}")
    logger.info(f"  SMS alerts sent: {total_alerts}")
    logger.info(f"{'─' * 50}")
    
    # Log overall scan
    log_scan(conn, None, total_jobs, total_new, total_alerts)
    
    # Save state
    state = {
        "last_scan": datetime.now(timezone.utc).isoformat(),
        "total_jobs_tracked": conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],
        "new_last_scan": total_new,
        "alerts_sent": total_alerts,
    }
    with open(STATE_PATH, "w") as f:
        json.dump(state, f)
    
    conn.close()
    return total_new, total_alerts


# ═══════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════

def main():
    """CLI entry point."""
    args = sys.argv[1:]
    
    if "--list-companies" in args:
        print("\n🔍 Available Companies:\n")
        for key, cfg in COMPANIES.items():
            print(f"  {cfg['icon']} {key:15s} — {cfg['location']:15s} ({cfg['type']})")
        print()
        return
    
    if "--status" in args:
        conn = init_db()
        stats = get_stats(conn)
        conn.close()
        print(f"\n📊 Radar Status\n")
        print(f"  Total jobs tracked: {stats['total_jobs']}")
        print(f"  Active jobs:        {stats['active_jobs']}")
        print(f"  Total scans run:    {stats['total_scans']}")
        print(f"  Last scan:          {stats['last_scan']}")
        print(f"\n  Jobs by company:")
        for company, count in stats['by_company'].items():
            print(f"    {COMPANIES.get(company, {}).get('icon', '•')} {company}: {count}")
        print()
        return
    
    dry_run = "--dry-run" in args
    
    # Extract specific company if provided
    companies = None
    for arg in args:
        if arg.upper() in {k.upper() for k in COMPANIES}:
            companies = [k for k in COMPANIES if k.upper() == arg.upper()]
    
    run_scan(dry_run=dry_run, companies=companies)


if __name__ == "__main__":
    main()
