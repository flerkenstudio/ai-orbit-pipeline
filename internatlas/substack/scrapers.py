"""Multi-ATS Direct Career Portal Scrapers (Greenhouse, Lever, Ashby, SmartRecruiters, Workday)."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import yaml

from .config import COMPANIES_FILE, REQUEST_TIMEOUT, MAX_WORKERS
from .processor import (
    is_early_career,
    is_india_location,
    normalize_location_and_mode,
    classify_domain_section,
    compute_priority,
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def load_companies() -> dict:
    if not COMPANIES_FILE.exists():
        return {}
    with open(COMPANIES_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def scrape_greenhouse_board(comp: dict) -> list:
    name = comp["name"]
    slug = comp["slug"]
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return results
        jobs = resp.json().get("jobs", [])
        for j in jobs:
            title = (j.get("title") or "").strip()
            loc_raw = (j.get("location", {}) or {}).get("name", "")
            abs_url = (j.get("absolute_url") or "").strip()
            if not (title and abs_url):
                continue
            if is_early_career(title) and is_india_location(loc_raw):
                loc, mode = normalize_location_and_mode(loc_raw)
                results.append({
                    "company": name,
                    "role_title": title,
                    "location": loc,
                    "work_mode": mode,
                    "section": classify_domain_section(title),
                    "apply_url": abs_url,
                    "ats_source": "Greenhouse",
                    "priority_score": compute_priority(name, title, abs_url),
                })
    except Exception:
        pass
    return results


def scrape_lever_board(comp: dict) -> list:
    name = comp["name"]
    slug = comp["slug"]
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return results
        postings = resp.json()
        if not isinstance(postings, list):
            return results
        for p in postings:
            title = (p.get("text") or "").strip()
            cats = p.get("categories") or {}
            loc_raw = cats.get("location") or ""
            dept = cats.get("department") or cats.get("team") or ""
            workplace = p.get("workplaceType") or ""
            hosted_url = (p.get("hostedUrl") or "").strip()
            if not (title and hosted_url):
                continue
            if is_early_career(title) and is_india_location(loc_raw):
                loc, mode = normalize_location_and_mode(loc_raw, workplace)
                results.append({
                    "company": name,
                    "role_title": title,
                    "location": loc,
                    "work_mode": mode,
                    "section": classify_domain_section(title, dept),
                    "apply_url": hosted_url,
                    "ats_source": "Lever",
                    "priority_score": compute_priority(name, title, hosted_url),
                })
    except Exception:
        pass
    return results


def scrape_ashby_board(comp: dict) -> list:
    name = comp["name"]
    slug = comp["slug"]
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return results
        jobs = resp.json().get("jobs", [])
        for j in jobs:
            title = (j.get("title") or "").strip()
            loc_raw = j.get("location") or ""
            is_remote = j.get("isRemote")
            mode_hint = "Remote" if is_remote else (j.get("workplaceType") or "")
            dept = j.get("department") or j.get("team") or ""
            job_url = (j.get("jobUrl") or "").strip()
            if not job_url and j.get("id"):
                job_url = f"https://jobs.ashbyhq.com/{slug}/{j['id']}"
            if not (title and job_url):
                continue
            if is_early_career(title) and (is_india_location(loc_raw) or is_remote):
                loc, mode = normalize_location_and_mode(loc_raw, mode_hint)
                results.append({
                    "company": name,
                    "role_title": title,
                    "location": loc,
                    "work_mode": mode,
                    "section": classify_domain_section(title, dept),
                    "apply_url": job_url,
                    "ats_source": "Ashby",
                    "priority_score": compute_priority(name, title, job_url),
                })
    except Exception:
        pass
    return results


def scrape_smartrecruiters_board(comp: dict) -> list:
    name = comp["name"]
    slug = comp["slug"]
    url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, params={"limit": 100}, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return results
        postings = resp.json().get("content", [])
        for p in postings:
            title = (p.get("name") or "").strip()
            loc_obj = p.get("location") or {}
            city = loc_obj.get("city") or ""
            region = loc_obj.get("region") or ""
            country = loc_obj.get("country") or ""
            is_remote = loc_obj.get("remote")
            loc_raw = f"{city}, {region}, {country}".strip(", ")
            pid = p.get("id")
            if not (title and pid):
                continue
            apply_url = f"https://jobs.smartrecruiters.com/{slug}/{pid}"
            if is_early_career(title) and (country.lower() == "in" or is_india_location(loc_raw)):
                loc, mode = normalize_location_and_mode(loc_raw, "Remote" if is_remote else "")
                results.append({
                    "company": name,
                    "role_title": title,
                    "location": loc,
                    "work_mode": mode,
                    "section": classify_domain_section(title),
                    "apply_url": apply_url,
                    "ats_source": "SmartRecruiters",
                    "priority_score": compute_priority(name, title, apply_url),
                })
    except Exception:
        pass
    return results


def scrape_workday_board(comp: dict) -> list:
    name = comp["name"]
    tenant = comp["tenant"]
    wd = comp["wd"]
    site = comp["site"]
    api_url = f"https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
    base_url = f"https://{tenant}.{wd}.myworkdayjobs.com/{site}"
    results = []
    try:
        payload = {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": "Intern India"}
        resp = requests.post(api_url, json=payload, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return results
        postings = resp.json().get("jobPostings", [])
        for p in postings:
            title = (p.get("title") or "").strip()
            loc_raw = p.get("locationsText") or ""
            ext_path = p.get("externalPath") or ""
            if not (title and ext_path):
                continue
            apply_url = f"{base_url}{ext_path}"
            if is_early_career(title) and is_india_location(f"{loc_raw} {ext_path}"):
                loc, mode = normalize_location_and_mode(loc_raw)
                results.append({
                    "company": name,
                    "role_title": title,
                    "location": loc,
                    "work_mode": mode,
                    "section": classify_domain_section(title),
                    "apply_url": apply_url,
                    "ats_source": "Workday",
                    "priority_score": compute_priority(name, title, apply_url),
                })
    except Exception:
        pass
    return results


def get_verified_seed_roles() -> list:
    """Verified direct official career portal listings across Greenhouse, Lever, Ashby, SmartRecruiters & Workday."""
    raw_seed = [
        # Hottest New Opportunities - Apply Fast
        ("Thoughtworks", "Developer (Vapasi) - Intern", "Bengaluru, Karnataka", "In-Office", "https://www.thoughtworks.com/careers/jobs/8210384?gh_jid=8210384", "Greenhouse", 1),
        ("Stripe", "Software Engineer, Intern", "Bengaluru, Karnataka", "In-Office", "https://stripe.com/jobs/search?gh_jid=8031833", "Greenhouse", 1),
        ("NVIDIA", "PhD Intern, AI ML in Wireless L1/L2 - Fall 2026", "Bengaluru, Karnataka", "In-Office", "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite/job/India-Bengaluru/PhD-Intern--AI-ML-in-Wireless-L1-L2---Fall-2026_JR2024423", "Workday", 1),
        ("Walmart Global Tech", "Grad Intern - No Work Experience", "Bengaluru, Karnataka", "In-Office", "https://walmart.wd504.myworkdayjobs.com/WalmartExternal/job/IN-KA-BANGALORE-Home-Office-Building-10/XMLNAME--IND--Grad-Intern---No-Work-Experience_R-2557935", "Workday", 1),
        ("Groww", "Video Editor Intern", "Bengaluru, Karnataka", "In-Office", "https://job-boards.eu.greenhouse.io/groww/jobs/4956817101", "Greenhouse", 1),
        ("Smartsheet", "Product Management - Interns", "Bengaluru, Karnataka", "In-Office", "https://job-boards.greenhouse.io/smartsheet/jobs/8255581", "Greenhouse", 1),
        ("Marvell Technology", "Research Intern, Physical AI and GPU (PhD)", "Hyderabad, Telangana", "In-Office", "https://marvell.wd1.myworkdayjobs.com/MarvellCareers/job/Hyderabad/Research-Intern--Physical-AI-and-GPU--PhD-_2604253", "Workday", 1),
        ("Hewlett Packard Enterprise (HPE)", "External Intern", "Bengaluru, Karnataka", "In-Office", "https://hpe.wd5.myworkdayjobs.com/en-US/Jobsathpe/job/job/Bengaluru-Karntaka-India/External-Intern_1215491-3", "Workday", 1),
        ("Paytm", "Intern - Talent Acquisition", "Noida, Uttar Pradesh", "In-Office", "https://jobs.lever.co/paytm/9d497980-2032-440c-8bac-63fb53939acc", "Lever", 1),
        ("PhonePe", "Intern, Company Secretary & Governance", "Bengaluru, Karnataka", "In-Office", "https://jobs.smartrecruiters.com/PHONEPELIMITED/1000000000002543-intern-company-secretary", "SmartRecruiters", 1),

        # Latest Software Development & Core Engineering Opportunities
        ("Bosch Group", "Intern, Corporate Communications", "Bengaluru, Karnataka", "In-Office", "https://jobs.smartrecruiters.com/BoschGroup/744000143069809-intern-corporate-communications", "SmartRecruiters", 0),
        ("Dr. Reddy's Laboratories", "Digital & Process Excellence Intern", "Hyderabad, Telangana", "In-Office", "https://jobs.smartrecruiters.com/DrReddysLaboratoriesLimited/744000152345938-digital-process-excellence-intern", "SmartRecruiters", 0),
        ("Merkle Science", "Software Engineer - Intern (Frontend)", "Bengaluru, Karnataka", "In-Office", "https://jobs.lever.co/merklescience/20675d00-156c-4f3f-a9bf-4cacee176bc2", "Lever", 0),
        ("Zinnov", "Intern - Employer Branding", "Hyderabad, Telangana", "In-Office", "https://job-boards.greenhouse.io/zinnov/jobs/4412599009", "Greenhouse", 0),
        ("FamPay", "Security Engineer Intern", "Bengaluru, Karnataka", "In-Office", "https://jobs.lever.co/fampay/bbbbbfd2-1855-4991-82d5-84ef57607c24", "Lever", 0),
        ("HackerRank", "Software Development Engineer Intern", "Bengaluru, Karnataka", "In-Office", "https://job-boards.greenhouse.io/hackerrank/jobs/8229735", "Greenhouse", 0),
        ("CloudSEK", "Security Consultant Intern", "Bengaluru, Karnataka", "In-Office", "https://job-boards.greenhouse.io/cloudsek/jobs/6115382004", "Greenhouse", 0),
        ("TrueFoundry", "Intern - Founders Office and Alliances", "Bengaluru, Karnataka", "In-Office", "https://job-boards.greenhouse.io/truefoundry/jobs/5433840008", "Greenhouse", 0),
        ("Veradigm", "Contractor - Intern", "Pune, Maharashtra", "In-Office", "https://veradigm.wd12.myworkdayjobs.com/en-US/VR/job/Contractor---Intern_JR10512", "Workday", 0),
        ("66degrees", "IT Service Desk Intern", "Bengaluru, Karnataka", "In-Office", "https://job-boards.greenhouse.io/66degrees/jobs/6127315004", "Greenhouse", 0),
        ("AlphaGrep Securities", "Quantitative Trading Intern (2027 Cohort)", "Bengaluru, Karnataka", "In-Office", "https://job-boards.greenhouse.io/alphagrepsecurities/jobs/8769725002", "Greenhouse", 0),
        ("Apollo Global Management", "Intern", "Mumbai, Maharashtra", "In-Office", "https://athene.wd5.myworkdayjobs.com/apollononpubliccareersite/job/Mumbai-NESCO-India/Intern_R253646", "Workday", 0),
        ("Applus+ IDIADA", "Homologation- Intern", "Gurugram, Haryana", "In-Office", "https://jobs.smartrecruiters.com/ApplusIDIADA1/744000129136899-homologation-intern", "SmartRecruiters", 0),
        ("Centific", "Technical Intern", "Chennai, Tamil Nadu", "In-Office", "https://centific.wd1.myworkdayjobs.com/en-US/Centific_ECS_SEA/job/Technical-Intern_JR102803", "Workday", 0),
        ("Cushman & Wakefield", "EIC Intern - Hospitality / Facilities Management", "Hyderabad, Telangana", "In-Office", "https://cw.wd1.myworkdayjobs.com/External/job/Hyderabad-India/EIC-Intern---Hospitality---Facilities-Management--Hyderabad_R328210", "Workday", 0),
        ("Edwards Lifesciences", "IT Internship Program (Jan - June 2027)", "Pune, Maharashtra", "In-Office", "https://edwards.wd5.myworkdayjobs.com/en-US/edwardsCareers/job/India-Pune/IT-Internship-Program--January---June-2027-_Req-50762", "Workday", 0),
        ("GE Vernova", "Digital Technology Development Program Intern 2027", "Bengaluru, Karnataka", "In-Office", "https://gevernova.wd5.myworkdayjobs.com/en-US/Vernova_ExternalSite/job/Digital-Technology-Development-Program-Intern---India-2027_R5052743-1", "Workday", 0),
        ("Human Archive", "Founder's Office Intern - Partnerships", "Bengaluru, Karnataka", "In-Office", "https://jobs.ashbyhq.com/humanarchive/4c694746-a082-4ee9-9dcd-06a1b82f44ee", "Ashby", 0),
        ("Hyreo", "Udaan Intern - Catalog", "Bengaluru, Karnataka", "In-Office", "https://job-boards.greenhouse.io/hyreo/jobs/5334458004", "Greenhouse", 0),
        ("Invesco", "Early Career Intern - Fixed Income Global Technology", "Hyderabad, Telangana", "In-Office", "https://invesco.wd1.myworkdayjobs.com/en-US/IVZ/job/Early-Career-Intern---Fixed-Income-Global-Technology_R-15621-1", "Workday", 0),
        ("JBT Marel", "Sourcing Engineering Intern", "Pune, Maharashtra", "In-Office", "https://jbtm.wd108.myworkdayjobs.com/JBT_Marel_Career_Site/job/IN---Pune/Sourcing-Engineering-Intern_2025-13660", "Workday", 0),
        ("Josys", "IT Administrator (Intern)", "Bengaluru, Karnataka", "In-Office", "https://jobs.ashbyhq.com/josys/83229282-68cb-475c-8948-f293850e8657", "Ashby", 0),
        ("Kaleris", "Associate Software Engineer - Intern", "Chennai, Tamil Nadu", "In-Office", "https://kaleris.wd501.myworkdayjobs.com/en-US/kaleris_careers/job/Associate-Software-Engineer-Intern_R-100658", "Workday", 0),
        ("Keenfinity", "Software Engineering Intern", "Hyderabad, Telangana", "Remote", "https://jobs.smartrecruiters.com/Keenfinity/744000152241469-software-engineering-intern", "SmartRecruiters", 0),
        ("Kulfi Collective", "Intern - Culture & Experiences", "Mumbai, Maharashtra", "In-Office", "https://job-boards.greenhouse.io/kulficollective/jobs/5432982008", "Greenhouse", 0),
        ("Laminar", "Technical Intern", "India - Remote", "Remote", "https://jobs.ashbyhq.com/laminar-jobs/b8bf92af-a213-4f50-a22c-4a2413c4ab87", "Ashby", 0),
        ("MRI Software", "Software Intern - QA & Automation", "Bengaluru, Karnataka", "In-Office", "https://mrisoftware.wd501.myworkdayjobs.com/External_CareerSite/job/Bangalore-India-Office/Software-Intern---QA_R-103342", "Workday", 0),
        ("Micron Technology", "Technician Apprentice", "Sanand, Gujarat", "In-Office", "https://micron.wd1.myworkdayjobs.com/en-US/External/job/Sanand---303A---ATSSDMOD-India/Technician-Apprentice_JR107694", "Workday", 0),
        ("Nextracker", "Intern - Systems Engineering", "Hyderabad, Telangana", "In-Office", "https://nextracker.wd5.myworkdayjobs.com/nextpower_careers/job/Hyderabad-Telangana---IND/Intern--Systems-Engineering_NX-4026", "Workday", 0),
        ("Procter & Gamble (P&G)", "Information Technology Intern (Software Engineering)", "Mumbai, Maharashtra", "In-Office", "https://pg.wd5.myworkdayjobs.com/1000/job/MUMBAI-GENERAL-OFFICE/Information-Technology-Intern_R000160029", "Workday", 0),
        ("Vertical Software", "Java Developer Intern", "Pune, Maharashtra", "In-Office", "https://jobs.smartrecruiters.com/VerticalSoftware/743999681813542-java-developer-intern", "SmartRecruiters", 0),
        ("WNS Global Services", "Testing: Software Intern", "Bengaluru, Karnataka", "In-Office", "https://jobs.smartrecruiters.com/WNSGlobalServices144/744000129395279-testting-software-intern-kipi", "SmartRecruiters", 0),

        # Latest Artificial Intelligence & Machine Learning Opportunities
        ("Smiths Group", "Graduate Apprentice Trainee", "Pune, Maharashtra", "In-Office", "https://jobs.smartrecruiters.com/SmithsGroup2/744000152589129", "SmartRecruiters", 0),
        ("Konecranes", "Diploma Engineer Trainee", "Kolkata, West Bengal", "In-Office", "https://jobs.smartrecruiters.com/Konecranes/744000152591359", "SmartRecruiters", 0),
        ("Altera (An Intel Company)", "AI Automation Intern", "Bengaluru, Karnataka", "In-Office", "https://altera.wd1.myworkdayjobs.com/Altera/job/Bengaluru-Karnataka-India/AI-Automation-Intern_R03117", "Workday", 0),
        ("Merck & Co. (MSD)", "Intern - Global Complaint Operation", "Pune, Maharashtra", "In-Office", "https://msd.wd5.myworkdayjobs.com/SearchJobs/job/IND---Maharashtra---Pune-Wework/Intern---Global-Complaint-Operation_R420320", "Workday", 0),
        ("Wabtec Corporation", "Diploma Trainee", "Mysore, KA", "In-Office", "https://jobs.smartrecruiters.com/Wabtec/3743990015883565", "SmartRecruiters", 0),
        ("Sigmoid Analytics", "Industrial Trainee - Finance & Accounting", "Bengaluru, Karnataka", "In-Office", "https://job-boards.greenhouse.io/sigmoid/jobs/8713069002", "Greenhouse", 0),
        ("Fi Money", "DS/ML Intern", "Bengaluru, Karnataka", "In-Office", "https://jobs.lever.co/epifi/08fc1577-4593-4b94-b66b-08e638d29f37", "Lever", 0),
        ("Sarvam AI", "Marketing Intern", "Bengaluru, Karnataka", "In-Office", "https://jobs.ashbyhq.com/sarvam/ef7f079b-6a1f-4b27-9cfb-a5f68fe825c7", "Ashby", 0),
        ("AML RightSource", "Learning & Development - Intern", "Gurugram, Haryana", "In-Office", "https://amlrightsource.wd1.myworkdayjobs.com/en-US/amlrightsource/job/Gurgaon-India/Learning---Development---Intern---Gurugram--India_R-103236", "Workday", 0),
        ("Abstrabit Technologies", "AI Engineering Intern", "Bengaluru, Karnataka", "In-Office", "https://jobs.smartrecruiters.com/AbstrabitTechnologiesPvtLtd/744000150288970", "SmartRecruiters", 0),
        ("Airbound", "Mechanical Engineer - Internship", "Bengaluru, Karnataka", "In-Office", "https://jobs.ashbyhq.com/airbound/25b390f1-6cf8-4ea1-891b-75b9d3eb01dc", "Ashby", 0),
        ("Brainwonders", "International Research Intern", "India (Multiple Locations)", "In-Office", "https://jobs.smartrecruiters.com/Brainwonders/744000150908109", "SmartRecruiters", 0),
        ("Bringle Excellence", "Management Trainee", "Mumbai, Maharashtra", "In-Office", "https://jobs.smartrecruiters.com/BringleExcellence/743999650639636", "SmartRecruiters", 0),
        ("Cisco Systems", "Talent Acquisition Coordinator Trainee (Graduate Apprentice)", "Bengaluru, Karnataka", "In-Office", "https://cisco.wd5.myworkdayjobs.com/en-US/Cisco_Careers/job/IND-BANGALORE/Talent-Acquisition-Coordinator-Trainee-Non-Technical-Graduate-Apprentice---India-UHR_2013742", "Workday", 0),
        ("Ema", "AI/Data Resident (6-Month Internship)", "India - Remote", "Remote", "https://jobs.ashbyhq.com/ema/e0511c0c-998f-4079-b62c-d2f164bf2c86", "Ashby", 0),
        ("Endeavor IT Solution", "Java Developer Trainee in Indore", "Indore, Madhya Pradesh", "In-Office", "https://jobs.smartrecruiters.com/EndeavorITSolution/743999658931482", "SmartRecruiters", 0),
        ("Eurofins Scientific", "Trainee - Finance", "Bengaluru, Karnataka", "In-Office", "https://jobs.smartrecruiters.com/Eurofins/744000141900959-trainee-finance-", "SmartRecruiters", 0),
        ("Forma.ai", "Customer Operations Analyst Intern", "Pune, Maharashtra", "In-Office", "https://job-boards.greenhouse.io/formaaiinc3/jobs/4090129005", "Greenhouse", 0),
        ("IQVIA", "Software Engineer Intern - AIML Incubator", "Bengaluru, Karnataka", "In-Office", "https://iqvia.wd1.myworkdayjobs.com/en-GB/IQVIA/job/Bangalore-India/Intern_R1567860", "Workday", 0),
        ("Libra AI", "Founder's Office Intern", "Bengaluru, Karnataka", "In-Office", "https://jobs.ashbyhq.com/libra/b017c290-38d2-4e77-8d56-96f9dd60ff93", "Ashby", 0),
        ("Meesho", "Trainee - Recruitment Coordinator", "Bengaluru, Karnataka", "In-Office", "https://jobs.lever.co/meesho/1de2fc88-e203-4f1a-8046-55df700de4be", "Lever", 0),
        ("Meraki Labs", "AI Engineer Intern", "Bengaluru, Karnataka", "In-Office", "https://jobs.ashbyhq.com/Meraki-Labs/93ff65d2-f0cd-4fd1-b76f-b2e350f2d6c8", "Ashby", 0),
        ("Moving Picture Company (MPC)", "MPC Academy - Roto / Paint Trainee", "Bengaluru, Karnataka", "In-Office", "https://jobs.smartrecruiters.com/MovingPictureCompany/94087102-mpc-academy-roto", "SmartRecruiters", 0),
        ("Optimized Infotech", "Digital Marketing Trainee/Internship", "Pune, Maharashtra", "In-Office", "https://jobs.smartrecruiters.com/OptimizedInfotech/743999665634193-digital-marketing-trainee-internship", "SmartRecruiters", 0),
        ("Pitney Bowes", "Business Applications Intern - AI & LLMs", "Pune, Maharashtra", "In-Office", "https://pitneybowes.wd1.myworkdayjobs.com/en-US/PBCareers/job/Intern_R22155", "Workday", 0),
        ("Sika AG", "Management Trainee", "Kolkata, West Bengal", "In-Office", "https://jobs.smartrecruiters.com/SikaAG/744000153664779", "SmartRecruiters", 0),
        ("Stryker", "Intern Supply Chain", "Gurugram, Haryana", "In-Office", "https://stryker.wd1.myworkdayjobs.com/StrykerCareers/job/Gurugram-India/Intern-Supply-Chain_R569876", "Workday", 0),
        ("Tower Research Capital", "Intern - AI/ML", "Gurugram, Haryana", "In-Office", "https://job-boards.greenhouse.io/towerresearchcapital/jobs/8143756", "Greenhouse", 0),

        # Latest Data Analytics, Research & Intelligence Roles
        ("Karya", "Data Curation Intern", "Bengaluru, Karnataka", "In-Office", "https://job-boards.greenhouse.io/karya/jobs/5215559008", "Greenhouse", 0),
        ("Acceldata", "Finance Intern", "Bengaluru, Karnataka", "In-Office", "https://jobs.lever.co/acceldata/247b75d6-3829-4cfa-8ef1-34465ecf7a3d", "Lever", 0),
        ("Catenon", "Intern- International Market Research", "Pune, Maharashtra", "In-Office", "https://jobs.smartrecruiters.com/CatenonIndia1/82489181", "SmartRecruiters", 0),
        ("Clearwater Analytics", "Operations Intern", "Bengaluru, Karnataka", "In-Office", "https://clearwateranalytics.wd1.myworkdayjobs.com/Clearwater_Analytics_Careers/job/Office---Bengaluru/Operations-Intern_R12223", "Workday", 0),
        ("GE Aerospace", "Data Science Intern", "Bengaluru, Karnataka", "In-Office", "https://geaerospace.wd5.myworkdayjobs.com/GE_ExternalSite/job/Bengaluru/Data-Science-Intern_R5040691-1", "Workday", 0),
        ("SingleStore", "Software Engineer Intern (Database Engine)", "Bengaluru, Karnataka", "In-Office", "https://job-boards.greenhouse.io/singlestore/jobs/8154399", "Greenhouse", 0),

        # Latest Product Design, Media & Content Strategy Roles
        ("Scopely", "Intern - Game Design (Slot)", "Bengaluru, Karnataka", "In-Office", "https://job-boards.greenhouse.io/scopely/jobs/5256167008?gh_jid=5256167008", "Greenhouse", 0),
        ("Zynga", "Marketing Artist & Visual Design Intern", "Bengaluru, Karnataka", "In-Office", "https://job-boards.greenhouse.io/zyngaearlycareers/jobs/6194305004", "Greenhouse", 0),
        ("Hevo Data", "UX Design Intern", "Bengaluru, Karnataka", "In-Office", "https://jobs.lever.co/hevodata/433ffdef-3125-48ed-a131-52c697c321ee", "Lever", 0),
        ("Apna", "Visual Designer Intern", "Bengaluru, Karnataka", "In-Office", "https://careers.apna.co/_/j/76D9DBB425", "Direct Portal", 0),
        ("Headout", "Media & Research Intern", "Bengaluru, Karnataka", "Remote", "https://boards.greenhouse.io/headoutcareers/jobs/4672452006?gh_jid=4672452006", "Greenhouse", 0),
        ("Blueberry Labs", "Web Content Writer- Intern", "India (Multiple Locations)", "In-Office", "https://jobs.smartrecruiters.com/BlueberryLabsPrivateLimited/91846460", "SmartRecruiters", 0),
        ("Cadence Design Systems", "Intern in Photonics Flow", "Bengaluru, Karnataka", "In-Office", "https://cadence.wd1.myworkdayjobs.com/External_Careers/job/MEYLAN-01/Intern-in-Photonics-flow_R55241-2", "Workday", 0),
        ("Glance", "UX Design - Intern", "Bengaluru, Karnataka", "In-Office", "https://job-boards.greenhouse.io/glance/jobs/7916115", "Greenhouse", 0),
        ("InMobi", "People Team Intern - Creative & Communications", "Bengaluru, Karnataka", "In-Office", "https://job-boards.greenhouse.io/inmobi/jobs/8207429", "Greenhouse", 0),
        ("Prodigal", "Content Marketing Intern", "Mumbai, Maharashtra", "In-Office", "https://job-boards.greenhouse.io/prodigal/jobs/5227267007", "Greenhouse", 0),
        ("Sociokix", "Social Media Marketing Intern", "Hyderabad, Telangana", "In-Office", "https://jobs.smartrecruiters.com/Sociokix/743999753517575", "SmartRecruiters", 0),

        # Latest Business Operations, HR, Marketing & Strategy Roles
        ("Vegrow", "HR Intern", "Bengaluru, Karnataka", "In-Office", "https://jobs.smartrecruiters.com/Vegrow/743999786023287", "SmartRecruiters", 0),
        ("Interview Kickstart", "Intern, Talent Acquisition", "India - Remote", "Remote", "https://jobs.ashbyhq.com/interview-kickstart/7653eff0-a253-4165-b4a4-17c2cd0cbfa2", "Ashby", 0),
        ("Atlys", "Talent Acquisition Intern", "Gurugram, Haryana", "In-Office", "https://jobs.ashbyhq.com/atlys/26a24c85-dfe5-448d-a5e2-a0c004bc6fc7", "Ashby", 0),
        ("Instawork", "HR Intern", "Bengaluru, Karnataka", "In-Office", "https://job-boards.greenhouse.io/instawork/jobs/4686783006", "Greenhouse", 0),
        ("5ine Web Solutions", "Digital Marketing Internship Offer", "Bengaluru, Karnataka", "In-Office", "https://jobs.smartrecruiters.com/5ineWebSolutionsPvtLtd/102729588", "SmartRecruiters", 0),
        ("Autodesk", "Apprentice, Talent Acquisition & People Experience", "Bengaluru, Karnataka", "In-Office", "https://autodesk.wd1.myworkdayjobs.com/en-US/Ext/job/job/Bengaluru-IND/Apprentice--Talent-Acquisition---People-Experience_23WD73769-1", "Workday", 0),
        ("Avery Dennison", "Human Resources (HR) Intern", "Bengaluru, Karnataka", "In-Office", "https://jobs.smartrecruiters.com/AveryDennison/744000152902219", "SmartRecruiters", 0),
        ("Baker Hughes", "Emerging Talent Engineering & Technology Intern 2027", "Bengaluru, Karnataka", "In-Office", "https://bakerhughes.wd5.myworkdayjobs.com/en-US/BakerHughes/job/Emerging-Talent--Engineering---Technology-Intern--India--2027-Opportunities_R164188", "Workday", 0),
        ("DocBoyz (ZapFin)", "Sales Intern", "Pune, Maharashtra", "In-Office", "https://jobs.smartrecruiters.com/ZapFinTeknologiesPvtLtdDocBoyz/743999995140986", "SmartRecruiters", 0),
        ("Lokal", "HR Operations Intern", "India (Multiple Locations)", "In-Office", "https://jobs.smartrecruiters.com/Lokal/744000096104605", "SmartRecruiters", 0),
        ("Prometteur Solutions", "Field Sales Intern", "Pune, Maharashtra", "In-Office", "https://jobs.smartrecruiters.com/PrometteurSolutionsPvtLtd/744000139226380", "SmartRecruiters", 0),
        ("SPAN", "HR Intern", "Bengaluru, Karnataka", "In-Office", "https://jobs.ashbyhq.com/span/1a44454a-c4eb-4a73-8f5b-7d3b921c0c1f", "Ashby", 0),
        ("Salesforce", "Summer 2027 Intern - Software Engineer", "Bengaluru, Karnataka", "In-Office", "https://salesforce.wd12.myworkdayjobs.com/en-US/External_Career_Site/job/Summer-2027-Intern---Software-Engineer_JR337715", "Workday", 0),
    ]

    seed_jobs = []
    for comp, role, loc, mode, url, ats, is_hot in raw_seed:
        sec = (
            "Hottest New Opportunities - Apply Fast"
            if is_hot
            else classify_domain_section(role)
        )
        seed_jobs.append({
            "company": comp,
            "role_title": role,
            "location": loc,
            "work_mode": mode,
            "section": sec,
            "is_hot": is_hot,
            "apply_url": url,
            "ats_source": ats,
            "priority_score": compute_priority(comp, role, url) + (15 if is_hot else 0),
        })
    return seed_jobs


def scrape_all_ats_portals(include_seed: bool = True, progress_cb=None) -> list:
    """Scrapes all configured Greenhouse, Lever, Ashby, SmartRecruiters, and Workday portals concurrently."""
    cfg = load_companies()
    tasks = []
    for c in cfg.get("greenhouse", []):
        tasks.append((scrape_greenhouse_board, c))
    for c in cfg.get("lever", []):
        tasks.append((scrape_lever_board, c))
    for c in cfg.get("ashby", []):
        tasks.append((scrape_ashby_board, c))
    for c in cfg.get("smartrecruiters", []):
        tasks.append((scrape_smartrecruiters_board, c))
    for c in cfg.get("workday", []):
        tasks.append((scrape_workday_board, c))

    live_jobs = []
    total_tasks = len(tasks)
    completed = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        future_map = {pool.submit(fn, comp): comp["name"] for fn, comp in tasks}
        for fut in as_completed(future_map):
            comp_name = future_map[fut]
            completed += 1
            try:
                items = fut.result()
                if items:
                    live_jobs.extend(items)
            except Exception:
                pass
            if progress_cb:
                progress_cb({
                    "completed": completed,
                    "total": total_tasks,
                    "last_company": comp_name,
                    "found": len(live_jobs),
                })

    if include_seed:
        seed_jobs = get_verified_seed_roles()
        seen_urls = {j["apply_url"].lower().strip() for j in live_jobs}
        for sj in seed_jobs:
            if sj["apply_url"].lower().strip() not in seen_urls:
                live_jobs.append(sj)

    return live_jobs
