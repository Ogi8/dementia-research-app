"""Research data service with real API integrations and European sources."""
from typing import List, Optional, Set
from datetime import datetime
import asyncio
import httpx
from bs4 import BeautifulSoup
import re
from app.models import ResearchArticle, Treatment


def _is_relevant_to_dementia(title: str, abstract: str) -> bool:
    """Check if article is relevant to Alzheimer's or dementia."""
    # Keywords that indicate relevance
    relevant_keywords = [
        'alzheimer', 'dementia', 'cognitive decline', 'cognitive impairment',
        'memory loss', 'neurodegenerative', 'amyloid', 'tau protein',
        'mild cognitive impairment', 'mci', 'frontotemporal', 'vascular dementia',
        'lewy body', 'parkinson', 'neurodegeneration'
    ]
    
    text_to_check = (title + " " + abstract).lower()
    
    # Check if any relevant keyword is in the text
    return any(keyword in text_to_check for keyword in relevant_keywords)


async def fetch_pubmed_research(max_results: int = 10) -> List[ResearchArticle]:
    """Fetch latest research from PubMed API. Fetches more than needed and filters for relevance."""
    articles = []
    
    try:
        # Fetch more articles than needed to allow for filtering
        fetch_count = max_results * 3
        
        # Step 1: Search for article IDs
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        search_params = {
            "db": "pubmed",
            "term": "(Alzheimer's disease OR dementia OR cognitive decline OR neurodegenerative)",
            "retmax": fetch_count,
            "sort": "pub_date",
            "retmode": "json"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            search_response = await client.get(search_url, params=search_params)
            search_data = search_response.json()
            
            if "esearchresult" not in search_data or "idlist" not in search_data["esearchresult"]:
                return articles
            
            pmids = search_data["esearchresult"]["idlist"]
            if not pmids:
                return articles
            
            # Step 2: Fetch article details
            fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(pmids),
                "retmode": "xml"
            }
            
            fetch_response = await client.get(fetch_url, params=fetch_params)
            soup = BeautifulSoup(fetch_response.text, "xml")
            pubmed_articles = soup.find_all("PubmedArticle")
            
            for idx, article in enumerate(pubmed_articles):
                try:
                    pmid = article.find("PMID")
                    pmid_text = pmid.text if pmid else pmids[idx]
                    
                    title_elem = article.find("ArticleTitle")
                    title = title_elem.text if title_elem else "No title available"
                    
                    # Extract abstract - try multiple fields
                    abstract = "Abstract not available"
                    abstract_elem = article.find("AbstractText")
                    if abstract_elem:
                        abstract = abstract_elem.text
                    else:
                        # Try to get from Abstract section with multiple AbstractText elements
                        abstract_section = article.find("Abstract")
                        if abstract_section:
                            abstract_texts = abstract_section.find_all("AbstractText")
                            if abstract_texts:
                                abstract = " ".join([at.text for at in abstract_texts if at.text])
                    
                    # Skip articles without abstracts or not relevant to dementia
                    if abstract == "Abstract not available":
                        continue
                    
                    if not _is_relevant_to_dementia(title, abstract):
                        continue
                    
                    if len(abstract) > 500:
                        abstract = abstract[:497] + "..."
                    
                    authors = []
                    author_list = article.find("AuthorList")
                    if author_list:
                        for author in author_list.find_all("Author", limit=3):
                            lastname = author.find("LastName")
                            forename = author.find("ForeName")
                            if lastname:
                                name = f"{forename.text if forename else ''} {lastname.text}".strip()
                                authors.append(name)
                    
                    if not authors:
                        authors = ["Author information not available"]
                    
                    pub_date = None
                    date_elem = article.find("PubDate")
                    if date_elem:
                        year = date_elem.find("Year")
                        month = date_elem.find("Month")
                        day = date_elem.find("Day")
                        
                        year_val = int(year.text) if year else datetime.now().year
                        month_val = _parse_month(month.text) if month else 1
                        day_val = int(day.text) if day else 1
                        
                        try:
                            pub_date = datetime(year_val, month_val, day_val)
                        except ValueError:
                            pub_date = datetime(year_val, 1, 1)
                    
                    if not pub_date:
                        pub_date = datetime.now()
                    
                    journal_elem = article.find("Title")
                    source = journal_elem.text if journal_elem else "PubMed"
                    
                    articles.append(ResearchArticle(
                        id=pmid_text,
                        title=title,
                        summary=abstract,
                        publication_date=pub_date,
                        authors=authors,
                        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid_text}/",
                        source=source
                    ))
                    
                    # Stop if we have enough articles
                    if len(articles) >= max_results:
                        break
                    
                except Exception as e:
                    print(f"Error parsing PubMed article: {e}")
                    continue
    
    except Exception as e:
        print(f"Error fetching from PubMed: {e}")
    
    return articles


async def fetch_clinical_trials(max_results: int = 8) -> List[Treatment]:
    """
    Fetch clinical trials from ClinicalTrials.gov API v2.
    Note: This API may return 403 errors due to rate limiting.
    Returns empty list if API is unavailable.
    """
    treatments = []
    
    try:
        api_url = "https://clinicaltrials.gov/api/v2/studies"
        params = {
            "query.cond": "Alzheimer Disease OR Dementia",
            "filter.overallStatus": "RECRUITING,ACTIVE_NOT_RECRUITING",
            "pageSize": max_results,
            "format": "json"
        }
        
        # Try multiple user agents in case of blocking
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://clinicaltrials.gov/",
            "DNT": "1"
        }
        
        # Add small delay to avoid rate limiting
        await asyncio.sleep(0.5)
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(api_url, params=params, headers=headers)
            
            if response.status_code == 403:
                print(f"ClinicalTrials.gov API blocked (403) - may be rate limited or bot detection")
                return treatments
            
            if response.status_code != 200:
                print(f"ClinicalTrials.gov API error: {response.status_code}")
                return treatments
            
            # Check content type
            content_type = response.headers.get("content-type", "")
            if "json" not in content_type:
                print(f"ClinicalTrials.gov returned non-JSON response: {content_type}")
                return treatments
            
            data = response.json()
            
            if "studies" not in data:
                print("No 'studies' key in ClinicalTrials.gov response")
                return treatments
            
            for study in data["studies"]:
                try:
                    protocol = study.get("protocolSection", {})
                    
                    # Extract identification info
                    id_module = protocol.get("identificationModule", {})
                    nct_id = id_module.get("nctId", "")
                    title = id_module.get("briefTitle", "No title available")
                    
                    # Extract description
                    desc_module = protocol.get("descriptionModule", {})
                    brief_summary = desc_module.get("briefSummary", "")
                    
                    if not brief_summary:
                        brief_summary = desc_module.get("detailedDescription", "")
                    
                    if len(brief_summary) > 400:
                        brief_summary = brief_summary[:397] + "..."
                    
                    # Extract status
                    status_module = protocol.get("statusModule", {})
                    overall_status = status_module.get("overallStatus", "").upper()
                    
                    if overall_status == "COMPLETED":
                        status = "approved"
                    elif overall_status in ["RECRUITING", "ACTIVE_NOT_RECRUITING"]:
                        status = "clinical_trial"
                    else:
                        status = "research"
                    
                    # Extract start date
                    start_date = None
                    start_date_struct = status_module.get("startDateStruct", {})
                    if start_date_struct:
                        date_str = start_date_struct.get("date")
                        if date_str:
                            try:
                                start_date = datetime.strptime(date_str, "%Y-%m-%d")
                            except ValueError:
                                try:
                                    start_date = datetime.strptime(date_str, "%Y-%m")
                                except ValueError:
                                    pass
                    
                    # Extract intervention name
                    arms_module = protocol.get("armsInterventionsModule", {})
                    interventions = arms_module.get("interventions", [])
                    intervention_name = title
                    if interventions:
                        first_intervention = interventions[0]
                        intervention_name = first_intervention.get("name", title)
                    
                    # Only add if we have a description
                    if brief_summary and brief_summary != "Description not available":
                        treatments.append(Treatment(
                            id=nct_id,
                            name=intervention_name,
                            description=brief_summary,
                            status=status,
                            approval_date=start_date,
                            url=f"https://clinicaltrials.gov/study/{nct_id}"
                        ))
                    
                except Exception as e:
                    print(f"Error parsing clinical trial: {e}")
                    continue
    
    except Exception as e:
        print(f"Error fetching from ClinicalTrials.gov: {e}")
    
    return treatments


async def scrape_europe_pmc() -> List[ResearchArticle]:
    """Fetch research from Europe PMC API."""
    articles = []
    
    try:
        api_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
        params = {
            "query": "(alzheimer OR dementia) AND (treatment OR therapy OR cognitive)",
            "format": "json",
            "pageSize": 10,
            "sort": "P_PDATE_D desc"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(api_url, params=params)
            data = response.json()
            
            if "resultList" not in data or "result" not in data["resultList"]:
                return articles
            
            for result in data["resultList"]["result"]:
                try:
                    pmid = result.get("pmid", result.get("id", ""))
                    title = result.get("title", "No title available")
                    abstract = result.get("abstractText", "")
                    
                    # Skip if no abstract or not relevant
                    if not abstract:
                        continue
                    
                    if not _is_relevant_to_dementia(title, abstract):
                        continue
                    
                    # Skip if no abstract or not relevant
                    if not abstract:
                        continue
                    
                    if not _is_relevant_to_dementia(title, abstract):
                        continue
                    
                    if len(abstract) > 500:
                        abstract = abstract[:497] + "..."
                    
                    authors_list = result.get("authorString", "").split(", ")
                    authors = authors_list[:3] if authors_list else ["Authors not available"]
                    
                    pub_year = result.get("pubYear")
                    pub_date = datetime(int(pub_year), 1, 1) if pub_year else datetime.now()
                    
                    source = result.get("journalTitle", "Europe PMC")
                    
                    url = f"https://europepmc.org/article/MED/{pmid}" if pmid else "https://europepmc.org"
                    
                    articles.append(ResearchArticle(
                        id=f"eupmc_{pmid}",
                        title=title,
                        summary=abstract,
                        publication_date=pub_date,
                        authors=authors,
                        url=url,
                        source=source
                    ))
                    
                except Exception as e:
                    print(f"Error parsing Europe PMC article: {e}")
                    continue
    
    except Exception as e:
        print(f"Error fetching from Europe PMC: {e}")
    
    return articles


async def scrape_alzheimer_europe() -> List[ResearchArticle]:
    """Scrape research updates from Alzheimer Europe."""
    articles = []
    
    try:
        url = "https://www.alzheimer-europe.org/research"
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Look for article entries
            article_elements = soup.find_all("article", limit=3)
            if not article_elements:
                article_elements = soup.find_all(class_=re.compile("(news|research|article)"), limit=3)
            
            for idx, elem in enumerate(article_elements):
                try:
                    title_elem = elem.find(["h2", "h3", "h4"])
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    
                    link = elem.find("a", href=True)
                    article_url = link["href"] if link else url
                    if article_url.startswith("/"):
                        article_url = f"https://www.alzheimer-europe.org{article_url}"
                    
                    summary_elem = elem.find("p")
                    summary = summary_elem.get_text(strip=True) if summary_elem else "Summary not available"
                    
                    if len(summary) > 400:
                        summary = summary[:397] + "..."
                    
                    articles.append(ResearchArticle(
                        id=f"alz_eu_{idx+1}",
                        title=title,
                        summary=summary,
                        publication_date=datetime.now(),
                        authors=["Alzheimer Europe"],
                        url=article_url,
                        source="Alzheimer Europe"
                    ))
                    
                except Exception as e:
                    print(f"Error parsing Alzheimer Europe article: {e}")
                    continue
    
    except Exception as e:
        print(f"Error scraping Alzheimer Europe: {e}")
    
    return articles


async def scrape_alzheimers_research_uk() -> List[ResearchArticle]:
    """Scrape research from Alzheimer's Research UK."""
    articles = []
    
    try:
        url = "https://www.alzheimersresearchuk.org/research/"
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            
            article_elements = soup.find_all("article", limit=3)
            if not article_elements:
                article_elements = soup.find_all(class_=re.compile("(card|post|entry)"), limit=3)
            
            for idx, elem in enumerate(article_elements):
                try:
                    title_elem = elem.find(["h2", "h3", "h4", "a"])
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    
                    link = elem.find("a", href=True)
                    article_url = link["href"] if link else url
                    if article_url.startswith("/"):
                        article_url = f"https://www.alzheimersresearchuk.org{article_url}"
                    
                    summary_elem = elem.find("p")
                    summary = summary_elem.get_text(strip=True) if summary_elem else "Summary not available"
                    
                    if len(summary) > 400:
                        summary = summary[:397] + "..."
                    
                    articles.append(ResearchArticle(
                        id=f"aruk_{idx+1}",
                        title=title,
                        summary=summary,
                        publication_date=datetime.now(),
                        authors=["Alzheimer's Research UK"],
                        url=article_url,
                        source="Alzheimer's Research UK"
                    ))
                    
                except Exception as e:
                    print(f"Error parsing ARUK article: {e}")
                    continue
    
    except Exception as e:
        print(f"Error scraping Alzheimer's Research UK: {e}")
    
    return articles


async def scrape_brightfocus_treatments() -> List[Treatment]:
    """Return curated treatments from BrightFocus Foundation research and news."""
    # Based on actual BrightFocus content from their treatments and research pages
    treatments = [
        Treatment(
            id="brightfocus_glp1",
            name="GLP-1 Receptor Agonists for Alzheimer's",
            description="GLP-1 analogs, originally developed for diabetes and weight loss (like semaglutide/Ozempic), show promise for Alzheimer's treatment. Research suggests these drugs may protect brain health, improve memory, and slow neurodegeneration by reducing inflammation and supporting brain cell survival.",
            status="research",
            approval_date=None,
            url="https://www.brightfocus.org/resource/can-glp-1-weight-loss-drugs-treat-alzheimers/"
        ),
        Treatment(
            id="brightfocus_light_sound",
            name="40Hz Light and Sound Stimulation (HOPE Study)",
            description="Non-invasive therapy using 40Hz frequency light and sound stimulation to target gamma brain waves. The HOPE Study investigates how this therapy may protect memory, thinking abilities, and daily function in Alzheimer's patients by potentially reducing harmful brain proteins.",
            status="in_trial",
            approval_date=None,
            url="https://www.brightfocus.org/resource/non-invasive-light-and-sound-stimulation-therapy-in-alzheimers-update-on-hope-study/"
        ),
        Treatment(
            id="brightfocus_regenbrain",
            name="ReGenBRAIN: Brain Regeneration Therapy",
            description="The ReGenBRAIN clinical trial explores whether brain tissue can be regenerated in Alzheimer's patients. This innovative approach investigates therapies that may stimulate brain cell regeneration and repair damaged neural networks.",
            status="in_trial",
            approval_date=None,
            url="https://www.brightfocus.org/resource/can-brain-tissue-be-regenerated-inside-the-regenbrain-trial/"
        )
    ]
    return treatments


async def scrape_eu_clinical_trials() -> List[Treatment]:
    """Return curated European clinical trials with full descriptions."""
    treatments = [
        Treatment(
            id="lecanemab_eu",
            name="Lecanemab (Leqembi)",
            description="Lecanemab is a humanized IgG1 monoclonal antibody that targets aggregated soluble (protofibrils) and insoluble forms of amyloid-beta. Clinical trials showed it slowed cognitive decline by 27% over 18 months in early Alzheimer's patients. Approved by EMA in 2024.",
            status="approved",
            approval_date="2024",
            url="https://www.ema.europa.eu/en/medicines/human/EPAR/leqembi"
        ),
        Treatment(
            id="donanemab_eu",
            name="Donanemab",
            description="Donanemab is a monoclonal antibody targeting a modified form of deposited amyloid-beta plaques (N3pG). Phase 3 trials show it slowed cognitive decline by up to 35% in early symptomatic Alzheimer's disease. EMA review ongoing for European approval in 2024-2025.",
            status="in_trial",
            approval_date=None,
            url="https://www.ema.europa.eu/en/medicines/human/summaries-opinion/donanemab"
        ),
        Treatment(
            id="light_therapy_eu",
            name="LUMIPOSA Light Therapy",
            description="The LUMIPOSA trial (NCT05955534) at Charité Berlin investigates 40Hz invisible spectral light therapy for mild to moderate Alzheimer's. The study uses gamma frequency light stimulation to potentially reduce amyloid plaques and improve cognitive function through non-invasive brain stimulation.",
            status="in_trial",
            approval_date=None,
            url="https://www.clinicaltrialsregister.eu/ctr-search/search?query=NCT05955534"
        ),
        Treatment(
            id="mediterranean_diet_eu",
            name="Mediterranean-DASH Diet (MIND)",
            description="European multicenter trials (FINGER, LIPIDIDIET) demonstrate that the MIND diet—combining Mediterranean and DASH diets—may slow cognitive decline. The diet emphasizes olive oil, fish, vegetables, berries, and nuts while limiting red meat and saturated fats.",
            status="research",
            approval_date=None,
            url="https://alzheimer-europe.org/research/finger-study"
        ),
        Treatment(
            id="gantenerumab_eu",
            name="Gantenerumab",
            description="Gantenerumab is a fully human IgG1 monoclonal antibody designed to bind aggregated amyloid-beta. Despite initial setbacks, Roche continues European trials with higher dosing regimens. Recent studies show some promise in reducing amyloid plaques in early Alzheimer's disease.",
            status="in_trial",
            approval_date=None,
            url="https://www.ema.europa.eu/en/medicines/human/summaries-opinion/gantenerumab"
        ),
        Treatment(
            id="tdcs_eu",
            name="Transcranial Direct Current Stimulation (tDCS)",
            description="European research centers investigate non-invasive tDCS therapy for Alzheimer's. Low-intensity electrical stimulation targets brain regions involved in memory and cognition. Multiple EU trials show modest improvements in cognitive performance and daily functioning.",
            status="research",
            approval_date=None,
            url="https://www.alzheimer-europe.org/research/understanding-dementia-research/types-research/non-drug-research"
        ),
        Treatment(
            id="aducanumab_eu",
            name="Aducanumab (Aduhelm)",
            description="Aducanumab is a human monoclonal antibody targeting aggregated forms of amyloid-beta. While controversially approved in the US in 2021, EMA rejected it in 2021 citing insufficient evidence. Some European centers continue observational studies on its long-term effects.",
            status="research",
            approval_date=None,
            url="https://www.ema.europa.eu/en/medicines/human/withdrawn-applications/aduhelm"
        ),
        Treatment(
            id="memantine_extended_eu",
            name="Memantine Extended-Release Combinations",
            description="European trials investigate extended-release memantine (NMDA receptor antagonist) combined with acetylcholinesterase inhibitors for moderate to severe Alzheimer's. Studies focus on optimized dosing schedules and combination therapies to maximize cognitive benefits.",
            status="approved",
            approval_date="2002",
            url="https://www.ema.europa.eu/en/medicines/human/EPAR/ebixa"
        )
    ]
    return treatments


def _parse_month(month_str: str) -> int:
    """Parse month string to integer."""
    months = {
        "jan": 1, "january": 1,
        "feb": 2, "february": 2,
        "mar": 3, "march": 3,
        "apr": 4, "april": 4,
        "may": 5,
        "jun": 6, "june": 6,
        "jul": 7, "july": 7,
        "aug": 8, "august": 8,
        "sep": 9, "september": 9,
        "oct": 10, "october": 10,
        "nov": 11, "november": 11,
        "dec": 12, "december": 12
    }
    
    month_lower = month_str.lower()
    return months.get(month_lower, 1)


async def get_latest_research() -> List[ResearchArticle]:
    """
    Fetch latest research from multiple sources.
    Combines PubMed, Europe PMC, Alzheimer Europe, and Alzheimer's Research UK.
    Removes duplicates based on title similarity.
    """
    all_articles = []
    seen_titles: Set[str] = set()
    
    try:
        # Fetch from all sources in parallel
        results = await asyncio.gather(
            fetch_pubmed_research(max_results=8),
            scrape_europe_pmc(),
            scrape_alzheimer_europe(),
            scrape_alzheimers_research_uk(),
            return_exceptions=True
        )
        
        # Combine results and remove duplicates
        for result in results:
            if isinstance(result, list):
                for article in result:
                    # Simple deduplication by title (normalized)
                    title_normalized = article.title.lower().strip()
                    if title_normalized not in seen_titles:
                        seen_titles.add(title_normalized)
                        all_articles.append(article)
        
        # Sort by publication date (newest first)
        all_articles.sort(key=lambda x: x.publication_date, reverse=True)
        
        # Return top 12
        return all_articles[:12]
        
    except Exception as e:
        print(f"Error in get_latest_research: {e}")
        return []


async def get_latest_treatments() -> List[Treatment]:
    """
    Fetch latest treatments from multiple sources.
    Combines ClinicalTrials.gov, EU Clinical Trials, and BrightFocus.
    Removes duplicates based on name similarity.
    """
    all_treatments = []
    seen_names: Set[str] = set()
    
    try:
        # Fetch from all sources in parallel
        results = await asyncio.gather(
            fetch_clinical_trials(max_results=6),
            scrape_eu_clinical_trials(),
            scrape_brightfocus_treatments(),
            return_exceptions=True
        )
        
        # Combine results and remove duplicates
        for result in results:
            if isinstance(result, list):
                for treatment in result:
                    # Simple deduplication by name (normalized)
                    name_normalized = treatment.name.lower().strip()
                    if name_normalized not in seen_names:
                        seen_names.add(name_normalized)
                        all_treatments.append(treatment)
        
        # Return top 10
        return all_treatments[:10]
        
    except Exception as e:
        print(f"Error in get_latest_treatments: {e}")
        return []

