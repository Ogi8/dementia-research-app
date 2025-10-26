"""Research data service with real API integrations."""
from typing import List, Optional
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
import re
from app.models import ResearchArticle, Treatment


async def fetch_pubmed_research(max_results: int = 10) -> List[ResearchArticle]:
    """
    Fetch latest research from PubMed API.
    Searches for Alzheimer's and dementia-related papers.
    """
    articles = []
    
    try:
        # Step 1: Search for article IDs
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        search_params = {
            "db": "pubmed",
            "term": "(Alzheimer's disease OR dementia) AND (treatment OR therapy OR biomarker OR diagnosis)",
            "retmax": max_results,
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
            
            # Parse XML response
            soup = BeautifulSoup(fetch_response.text, "xml")
            pubmed_articles = soup.find_all("PubmedArticle")
            
            for idx, article in enumerate(pubmed_articles):
                try:
                    # Extract PMID
                    pmid = article.find("PMID")
                    pmid_text = pmid.text if pmid else pmids[idx]
                    
                    # Extract title
                    title_elem = article.find("ArticleTitle")
                    title = title_elem.text if title_elem else "No title available"
                    
                    # Extract abstract
                    abstract_elem = article.find("AbstractText")
                    abstract = abstract_elem.text if abstract_elem else "Abstract not available"
                    
                    # Limit abstract length
                    if len(abstract) > 500:
                        abstract = abstract[:497] + "..."
                    
                    # Extract authors
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
                    
                    # Extract publication date
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
                    
                    # Extract journal
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
                    
                except Exception as e:
                    print(f"Error parsing PubMed article: {e}")
                    continue
    
    except Exception as e:
        print(f"Error fetching from PubMed: {e}")
    
    return articles


async def fetch_clinical_trials(max_results: int = 10) -> List[Treatment]:
    """
    Fetch clinical trials from ClinicalTrials.gov API.
    """
    treatments = []
    
    try:
        api_url = "https://clinicaltrials.gov/api/v2/studies"
        params = {
            "query.cond": "Alzheimer Disease OR Dementia",
            "filter.overallStatus": "RECRUITING,ACTIVE_NOT_RECRUITING,COMPLETED",
            "pageSize": max_results,
            "sort": "@relevance"
        }
        
        headers = {
            "Accept": "application/json",
            "User-Agent": "DementiaResearchApp/1.0"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(api_url, params=params, headers=headers)
            
            # Check if response is HTML (error page)
            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type:
                print(f"ClinicalTrials.gov returned HTML instead of JSON - Status: {response.status_code}")
                print(f"URL attempted: {response.url}")
                return treatments
            
            # Check status code
            if response.status_code != 200:
                print(f"ClinicalTrials.gov API error - Status: {response.status_code}")
                print(f"Response: {response.text[:200]}")
                return treatments
            
            try:
                data = response.json()
            except Exception as json_err:
                print(f"Failed to parse JSON from ClinicalTrials.gov: {json_err}")
                print(f"Response text: {response.text[:200]}")
                return treatments
            
            if "studies" not in data:
                print(f"No studies found in ClinicalTrials.gov response. Keys: {list(data.keys())}")
                return treatments
            
            for study in data["studies"]:
                try:
                    protocol = study.get("protocolSection", {})
                    
                    # Extract identification
                    id_module = protocol.get("identificationModule", {})
                    nct_id = id_module.get("nctId", "")
                    title = id_module.get("briefTitle", "No title available")
                    
                    # Extract description
                    desc_module = protocol.get("descriptionModule", {})
                    brief_summary = desc_module.get("briefSummary", "")
                    
                    # Limit description length
                    if len(brief_summary) > 400:
                        brief_summary = brief_summary[:397] + "..."
                    
                    # Extract status
                    status_module = protocol.get("statusModule", {})
                    overall_status = status_module.get("overallStatus", "").upper()
                    
                    # Map status
                    if overall_status == "COMPLETED":
                        status = "approved"
                    elif overall_status in ["RECRUITING", "ACTIVE_NOT_RECRUITING"]:
                        status = "clinical_trial"
                    else:
                        status = "research"
                    
                    # Extract dates
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
                    
                    # Extract interventions as treatment name
                    arms_module = protocol.get("armsInterventionsModule", {})
                    interventions = arms_module.get("interventions", [])
                    intervention_name = title
                    if interventions:
                        first_intervention = interventions[0]
                        intervention_name = first_intervention.get("name", title)
                    
                    treatments.append(Treatment(
                        id=nct_id,
                        name=intervention_name,
                        description=brief_summary or "Description not available",
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


async def scrape_brightfocus() -> List[ResearchArticle]:
    """
    Scrape latest research from BrightFocus website.
    """
    articles = []
    
    try:
        url = "https://www.brightfocus.org/alzheimers/alzheimers-disease-research/"
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Look for research articles (this may need adjustment based on actual HTML structure)
            # Trying multiple selectors to find articles
            article_containers = soup.find_all("article", limit=5)
            if not article_containers:
                article_containers = soup.find_all(class_=re.compile("research|article|post"), limit=5)
            
            for idx, container in enumerate(article_containers):
                try:
                    # Extract title
                    title_elem = container.find(["h1", "h2", "h3", "h4"])
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    
                    # Extract link
                    link_elem = container.find("a", href=True)
                    article_url = link_elem["href"] if link_elem else url
                    if article_url.startswith("/"):
                        article_url = f"https://www.brightfocus.org{article_url}"
                    
                    # Extract summary/description
                    summary_elem = container.find(["p", "div"], class_=re.compile("summary|excerpt|description"))
                    if not summary_elem:
                        summary_elem = container.find("p")
                    
                    summary = summary_elem.get_text(strip=True) if summary_elem else "Summary not available"
                    
                    # Limit summary length
                    if len(summary) > 400:
                        summary = summary[:397] + "..."
                    
                    # Extract date if available
                    date_elem = container.find(class_=re.compile("date|time|published"))
                    pub_date = datetime.now()
                    if date_elem:
                        date_text = date_elem.get_text(strip=True)
                        # Try to parse date (format may vary)
                        for fmt in ["%B %d, %Y", "%Y-%m-%d", "%m/%d/%Y"]:
                            try:
                                pub_date = datetime.strptime(date_text, fmt)
                                break
                            except ValueError:
                                continue
                    
                    articles.append(ResearchArticle(
                        id=f"brightfocus_{idx+1}",
                        title=title,
                        summary=summary,
                        publication_date=pub_date,
                        authors=["BrightFocus Foundation"],
                        url=article_url,
                        source="BrightFocus Foundation"
                    ))
                    
                except Exception as e:
                    print(f"Error parsing BrightFocus article: {e}")
                    continue
    
    except Exception as e:
        print(f"Error scraping BrightFocus: {e}")
    
    return articles


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
    Combines PubMed and BrightFocus data.
    """
    all_articles = []
    
    try:
        # Fetch from PubMed
        pubmed_articles = await fetch_pubmed_research(max_results=7)
        all_articles.extend(pubmed_articles)
        
        # Fetch from BrightFocus
        brightfocus_articles = await scrape_brightfocus()
        all_articles.extend(brightfocus_articles)
        
        # Sort by publication date (newest first)
        all_articles.sort(key=lambda x: x.publication_date, reverse=True)
        
        # Return top 10
        return all_articles[:10]
        
    except Exception as e:
        print(f"Error in get_latest_research: {e}")
        # Return empty list on error - caller can handle fallback
        return []


async def get_latest_treatments() -> List[Treatment]:
    """
    Fetch latest treatments from ClinicalTrials.gov.
    Returns only real API data - no fallback.
    """
    try:
        treatments = await fetch_clinical_trials(max_results=10)
        return treatments
    except Exception as e:
        print(f"Error in get_latest_treatments: {e}")
        # Return empty list - show only real data
        return []
