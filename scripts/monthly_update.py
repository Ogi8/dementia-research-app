"""Monthly data fetch and translation script."""
import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import sys
import os

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.config import get_settings
from app.services.research import get_latest_research, get_latest_treatments
from app.services.translator import translate_text
from jinja2 import Environment, FileSystemLoader

settings = get_settings()


async def translate_articles(articles: List[Dict], target_lang: str) -> List[Dict]:
    """Translate all articles to target language in parallel batches."""
    translated = []
    
    if target_lang == "en":
        # No translation needed for English
        return articles
    
    print(f"  🔄 Translating {len(articles)} articles...")
    
    # Translate in parallel batches of 3 to avoid rate limits
    batch_size = 3
    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        tasks = []
        
        for article in batch:
            tasks.append(_translate_article(article, target_lang))
        
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in batch_results:
            if isinstance(result, Exception):
                print(f"  ✗ Error: {result}")
            else:
                translated.append(result)
        
        print(f"  ✓ Progress: {len(translated)}/{len(articles)} articles")
    
    return translated


async def _translate_article(article: Dict, target_lang: str) -> Dict:
    """Translate a single article."""
    try:
        # Translate title and summary in parallel
        title_task = translate_text(article["title"], target_lang, "en")
        summary_task = translate_text(article["summary"], target_lang, "en")
        
        title_result, summary_result = await asyncio.gather(title_task, summary_task)
        
        translated_article = article.copy()
        translated_article["title"] = title_result[0] if title_result else article["title"]
        translated_article["summary"] = summary_result[0] if summary_result else article["summary"]
        
        return translated_article
    except Exception as e:
        print(f"  ✗ Error translating: {e}")
        return article


async def translate_treatments(treatments: List[Dict], target_lang: str) -> List[Dict]:
    """Translate all treatments to target language in parallel batches."""
    translated = []
    
    if target_lang == "en":
        # No translation needed for English
        return treatments
    
    if not treatments:
        return []
    
    print(f"  🔄 Translating {len(treatments)} treatments...")
    
    # Translate in parallel batches
    batch_size = 3
    for i in range(0, len(treatments), batch_size):
        batch = treatments[i:i + batch_size]
        tasks = []
        
        for treatment in batch:
            tasks.append(_translate_treatment(treatment, target_lang))
        
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in batch_results:
            if isinstance(result, Exception):
                print(f"  ✗ Error: {result}")
            else:
                translated.append(result)
        
        print(f"  ✓ Progress: {len(translated)}/{len(treatments)} treatments")
    
    return translated


async def _translate_treatment(treatment: Dict, target_lang: str) -> Dict:
    """Translate a single treatment."""
    try:
        # Translate name and description in parallel
        name_task = translate_text(treatment["name"], target_lang, "en")
        desc_task = translate_text(treatment["description"], target_lang, "en")
        
        name_result, desc_result = await asyncio.gather(name_task, desc_task)
        
        translated_treatment = treatment.copy()
        translated_treatment["name"] = name_result[0] if name_result else treatment["name"]
        translated_treatment["description"] = desc_result[0] if desc_result else treatment["description"]
        
        return translated_treatment
    except Exception as e:
        print(f"  ✗ Error translating: {e}")
        return treatment


def format_date_for_language(date: datetime, lang: str) -> str:
    """Format date according to language conventions."""
    month_translations = {
        "en": ["January", "February", "March", "April", "May", "June", 
               "July", "August", "September", "October", "November", "December"],
        "de": ["Januar", "Februar", "März", "April", "Mai", "Juni",
               "Juli", "August", "September", "Oktober", "November", "Dezember"],
        "fr": ["janvier", "février", "mars", "avril", "mai", "juin",
               "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
        "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio",
               "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
        "it": ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
               "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"],
        "hr": ["siječnja", "veljače", "ožujka", "travnja", "svibnja", "lipnja",
               "srpnja", "kolovoza", "rujna", "listopada", "studenoga", "prosinca"]
    }
    
    months = month_translations.get(lang, month_translations["en"])
    month_name = months[date.month - 1]
    
    # Date format by language
    if lang == "en":
        return f"{month_name} {date.day}, {date.year}"
    elif lang == "de":
        return f"{date.day}. {month_name} {date.year}"
    elif lang == "fr":
        return f"{date.day} {month_name} {date.year}"
    elif lang == "es":
        return f"{date.day} de {month_name} de {date.year}"
    elif lang == "it":
        return f"{date.day} {month_name} {date.year}"
    elif lang == "hr":
        return f"{date.day}. {month_name} {date.year}."
    else:
        return f"{month_name} {date.day}, {date.year}"


def generate_html_page(lang: str, articles: List[Dict], treatments: List[Dict], output_dir: Path, is_archived: bool = False, archive_date: str = None):
    """Generate static HTML page for a specific language."""
    # Language names for display
    lang_names = {
        "en": "English",
        "de": "Deutsch",
        "fr": "Français",
        "es": "Español",
        "it": "Italiano",
        "hr": "Hrvatski"
    }
    
    # UI translations for all text elements
    ui_translations = {
        "en": {
            "page_title": "Dementia Research and Treatments Information",
            "page_subtitle": "Latest Updates on Alzheimer's and Dementia Research",
            "language_label": "Language:",
            "last_updated": "Last updated:",
            "auto_update_note": "Content is automatically updated monthly",
            "next_update": "Next update in:",
            "updating": "Updating...",
            "view_archive": "View Archive",
            "archived_content": "Archived content from",
            "all_archives": "All Archives",
            "current_content": "Current Content",
            "archive_title": "Monthly Archives",
            "archive_subtitle": "Browse past research articles and treatments",
            "back_to_home": "Back to Home",
            "items": "items",
            "research_articles": "research articles",
            "treatments": "treatments",
            "no_archives": "No archived content available yet. Archives will be created after the first monthly update.",
            "latest_research": "Latest Research",
            "latest_treatments": "Latest Treatments",
            "read_more": "Read more",
            "learn_more": "Learn more",
            "source": "Source",
            "powered_by": "Powered by",
            "and": "and",
            "footer_copyright": "Dementia Research Information",
            "footer_note": "For educational purposes only.",
            "status_approved": "FDA Approved",
            "status_trial": "Clinical Trial",
            "status_research": "Research Stage"
        },
        "de": {
            "page_title": "Informationen zu Demenz-Forschung und -Behandlungen",
            "page_subtitle": "Neueste Updates zur Alzheimer- und Demenzforschung",
            "language_label": "Sprache:",
            "last_updated": "Zuletzt aktualisiert:",
            "auto_update_note": "Inhalte werden automatisch monatlich aktualisiert",
            "next_update": "Nächstes Update in:",
            "updating": "Aktualisierung...",
            "view_archive": "Archiv anzeigen",
            "archived_content": "Archivierter Inhalt vom",
            "all_archives": "Alle Archive",
            "current_content": "Aktueller Inhalt",
            "archive_title": "Monatsarchiv",
            "archive_subtitle": "Durchsuchen Sie frühere Forschungsartikel und Behandlungen",
            "back_to_home": "Zurück zur Startseite",
            "items": "Einträge",
            "research_articles": "Forschungsartikel",
            "treatments": "Behandlungen",
            "no_archives": "Noch keine archivierten Inhalte verfügbar. Archive werden nach dem ersten monatlichen Update erstellt.",
            "latest_research": "Neueste Forschung",
            "latest_treatments": "Neueste Behandlungen",
            "read_more": "Weiterlesen",
            "learn_more": "Mehr erfahren",
            "source": "Quelle",
            "powered_by": "Bereitgestellt von",
            "and": "und",
            "footer_copyright": "Demenz-Forschungsinformation",
            "footer_note": "Nur für Bildungszwecke.",
            "status_approved": "FDA-zugelassen",
            "status_trial": "Klinische Studie",
            "status_research": "Forschungsstadium"
        },
        "fr": {
            "page_title": "Informations sur la recherche et les traitements de la démence",
            "page_subtitle": "Dernières mises à jour sur la recherche sur Alzheimer et la démence",
            "language_label": "Langue :",
            "last_updated": "Dernière mise à jour :",
            "auto_update_note": "Le contenu est automatiquement mis à jour chaque mois",
            "next_update": "Prochaine mise à jour dans :",
            "updating": "Mise à jour...",
            "view_archive": "Voir les archives",
            "archived_content": "Contenu archivé du",
            "all_archives": "Toutes les archives",
            "current_content": "Contenu actuel",
            "archive_title": "Archives mensuelles",
            "archive_subtitle": "Parcourir les anciens articles de recherche et traitements",
            "back_to_home": "Retour à l'accueil",
            "items": "éléments",
            "research_articles": "articles de recherche",
            "treatments": "traitements",
            "no_archives": "Aucun contenu archivé disponible pour le moment. Les archives seront créées après la première mise à jour mensuelle.",
            "latest_research": "Dernières recherches",
            "latest_treatments": "Derniers traitements",
            "read_more": "En savoir plus",
            "learn_more": "En savoir plus",
            "source": "Source",
            "powered_by": "Propulsé par",
            "and": "et",
            "footer_copyright": "Information sur la recherche sur la démence",
            "footer_note": "À des fins éducatives uniquement.",
            "status_approved": "Approuvé par la FDA",
            "status_trial": "Essai clinique",
            "status_research": "Phase de recherche"
        },
        "es": {
            "page_title": "Información sobre investigación y tratamientos de demencia",
            "page_subtitle": "Últimas actualizaciones sobre la investigación de Alzheimer y demencia",
            "language_label": "Idioma:",
            "last_updated": "Última actualización:",
            "auto_update_note": "El contenido se actualiza automáticamente cada mes",
            "next_update": "Próxima actualización en:",
            "updating": "Actualizando...",
            "view_archive": "Ver archivo",
            "archived_content": "Contenido archivado del",
            "all_archives": "Todos los archivos",
            "current_content": "Contenido actual",
            "archive_title": "Archivos mensuales",
            "archive_subtitle": "Explorar artículos de investigación y tratamientos anteriores",
            "back_to_home": "Volver al inicio",
            "items": "elementos",
            "research_articles": "artículos de investigación",
            "treatments": "tratamientos",
            "no_archives": "Aún no hay contenido archivado disponible. Los archivos se crearán después de la primera actualización mensual.",
            "latest_research": "Últimas investigaciones",
            "latest_treatments": "Últimos tratamientos",
            "read_more": "Leer más",
            "learn_more": "Saber más",
            "source": "Fuente",
            "powered_by": "Desarrollado por",
            "and": "y",
            "footer_copyright": "Información sobre la investigación de la demencia",
            "footer_note": "Solo con fines educativos.",
            "status_approved": "Aprobado por la FDA",
            "status_trial": "Ensayo clínico",
            "status_research": "Fase de investigación"
        },
        "it": {
            "page_title": "Informazioni sulla ricerca e i trattamenti della demenza",
            "page_subtitle": "Ultimi aggiornamenti sulla ricerca su Alzheimer e demenza",
            "language_label": "Lingua:",
            "last_updated": "Ultimo aggiornamento:",
            "auto_update_note": "I contenuti vengono aggiornati automaticamente ogni mese",
            "next_update": "Prossimo aggiornamento tra:",
            "updating": "Aggiornamento...",
            "view_archive": "Visualizza archivio",
            "archived_content": "Contenuto archiviato del",
            "all_archives": "Tutti gli archivi",
            "current_content": "Contenuto corrente",
            "archive_title": "Archivi mensili",
            "archive_subtitle": "Sfoglia articoli di ricerca e trattamenti passati",
            "back_to_home": "Torna alla home",
            "items": "elementi",
            "research_articles": "articoli di ricerca",
            "treatments": "trattamenti",
            "no_archives": "Nessun contenuto archiviato ancora disponibile. Gli archivi verranno creati dopo il primo aggiornamento mensile.",
            "latest_research": "Ultime ricerche",
            "latest_treatments": "Ultimi trattamenti",
            "read_more": "Leggi di più",
            "learn_more": "Scopri di più",
            "source": "Fonte",
            "powered_by": "Offerto da",
            "and": "e",
            "footer_copyright": "Informazioni sulla ricerca sulla demenza",
            "footer_note": "Solo a scopo educativo.",
            "status_approved": "Approvato dalla FDA",
            "status_trial": "Sperimentazione clinica",
            "status_research": "Fase di ricerca"
        },
        "hr": {
            "page_title": "Informacije o istraživanjima i liječenju demencije",
            "page_subtitle": "Najnovija ažuriranja o istraživanju Alzheimerove bolesti i demencije",
            "language_label": "Jezik:",
            "last_updated": "Zadnje ažuriranje:",
            "auto_update_note": "Sadržaj se automatski ažurira mjesečno",
            "next_update": "Sljedeće ažuriranje za:",
            "updating": "Ažuriranje...",
            "view_archive": "Pogledaj arhivu",
            "archived_content": "Arhivirani sadržaj od",
            "all_archives": "Sve arhive",
            "current_content": "Trenutni sadržaj",
            "latest_research": "Najnovija istraživanja",
            "latest_treatments": "Najnoviji tretmani",
            "read_more": "Pročitaj više",
            "learn_more": "Saznaj više",
            "source": "Izvor",
            "powered_by": "Pokreće",
            "and": "i",
            "footer_copyright": "Informacije o istraživanju demencije",
            "footer_note": "Samo u obrazovne svrhe.",
            "status_approved": "FDA odobreno",
            "status_trial": "Klinička studija",
            "status_research": "Faza istraživanja"
        }
    }
    
    # Setup Jinja2 template environment
    template_dir = Path(__file__).parent.parent / "templates"
    template_dir.mkdir(exist_ok=True)
    
    # Create template if it doesn't exist
    template_file = template_dir / "language_page.html"
    if not template_file.exists():
        create_template(template_file)
    
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("language_page.html")
    
    # Get translations for current language
    ui = ui_translations.get(lang, ui_translations["en"])
    
    # Format date in the appropriate language
    formatted_date = format_date_for_language(datetime.now(), lang)
    
    # Render HTML
    html_content = template.render(
        lang=lang,
        lang_name=lang_names.get(lang, lang.upper()),
        all_languages=settings.languages_list,
        lang_names=lang_names,
        ui=ui,
        articles=articles,
        treatments=treatments,
        update_date=formatted_date,
        current_year=datetime.now().year,
        is_archived=is_archived,
        archive_date=archive_date if archive_date else formatted_date
    )
    
    # Save HTML file
    lang_dir = output_dir / lang
    lang_dir.mkdir(parents=True, exist_ok=True)
    
    html_file = lang_dir / "index.html"
    html_file.write_text(html_content, encoding="utf-8")
    
    print(f"  ✓ Generated: {html_file}")


def generate_archive_index(lang: str, output_dir: Path):
    """Generate archive index page showing all archived months."""
    from datetime import datetime
    import os
    
    # Language names for display
    lang_names = {
        "en": "English",
        "de": "Deutsch",
        "fr": "Français",
        "es": "Español",
        "it": "Italiano",
        "hr": "Hrvatski"
    }
    
    # UI translations (simplified for archive page)
    ui_translations = {
        "en": {
            "page_title": "Dementia Research and Treatments Information",
            "page_subtitle": "Latest Updates on Alzheimer's and Dementia Research",
            "language_label": "Language:",
            "archive_title": "Monthly Archives",
            "archive_subtitle": "Browse past research articles and treatments",
            "back_to_home": "Back to Home",
            "items": "items",
            "research_articles": "research articles",
            "treatments": "treatments",
            "no_archives": "No archived content available yet. Archives will be created after the first monthly update.",
            "footer_copyright": "Dementia Research Information",
            "footer_note": "For educational purposes only."
        },
        "de": {
            "page_title": "Informationen zu Demenz-Forschung und -Behandlungen",
            "page_subtitle": "Neueste Updates zur Alzheimer- und Demenzforschung",
            "language_label": "Sprache:",
            "archive_title": "Monatsarchiv",
            "archive_subtitle": "Durchsuchen Sie frühere Forschungsartikel und Behandlungen",
            "back_to_home": "Zurück zur Startseite",
            "items": "Einträge",
            "research_articles": "Forschungsartikel",
            "treatments": "Behandlungen",
            "no_archives": "Noch keine archivierten Inhalte verfügbar. Archive werden nach dem ersten monatlichen Update erstellt.",
            "footer_copyright": "Demenz-Forschungsinformation",
            "footer_note": "Nur für Bildungszwecke."
        },
        "fr": {
            "page_title": "Informations sur la recherche et les traitements de la démence",
            "page_subtitle": "Dernières mises à jour sur la recherche sur Alzheimer et la démence",
            "language_label": "Langue :",
            "archive_title": "Archives mensuelles",
            "archive_subtitle": "Parcourir les anciens articles de recherche et traitements",
            "back_to_home": "Retour à l'accueil",
            "items": "éléments",
            "research_articles": "articles de recherche",
            "treatments": "traitements",
            "no_archives": "Aucun contenu archivé disponible pour le moment. Les archives seront créées après la première mise à jour mensuelle.",
            "footer_copyright": "Information sur la recherche sur la démence",
            "footer_note": "À des fins éducatives uniquement."
        },
        "es": {
            "page_title": "Información sobre investigación y tratamientos de demencia",
            "page_subtitle": "Últimas actualizaciones sobre la investigación de Alzheimer y demencia",
            "language_label": "Idioma:",
            "archive_title": "Archivos mensuales",
            "archive_subtitle": "Explorar artículos de investigación y tratamientos anteriores",
            "back_to_home": "Volver al inicio",
            "items": "elementos",
            "research_articles": "artículos de investigación",
            "treatments": "tratamientos",
            "no_archives": "Aún no hay contenido archivado disponible. Los archivos se crearán después de la primera actualización mensual.",
            "footer_copyright": "Información sobre la investigación de la demencia",
            "footer_note": "Solo con fines educativos."
        },
        "it": {
            "page_title": "Informazioni sulla ricerca e i trattamenti della demenza",
            "page_subtitle": "Ultimi aggiornamenti sulla ricerca su Alzheimer e demenza",
            "language_label": "Lingua:",
            "archive_title": "Archivi mensili",
            "archive_subtitle": "Sfoglia articoli di ricerca e trattamenti passati",
            "back_to_home": "Torna alla home",
            "items": "elementi",
            "research_articles": "articoli di ricerca",
            "treatments": "trattamenti",
            "no_archives": "Nessun contenuto archiviato ancora disponibile. Gli archivi verranno creati dopo il primo aggiornamento mensile.",
            "footer_copyright": "Informazioni sulla ricerca sulla demenza",
            "footer_note": "Solo a scopo educativo."
        },
        "hr": {
            "page_title": "Informacije o istraživanjima i liječenju demencije",
            "page_subtitle": "Najnovija ažuriranja o istraživanju Alzheimerove bolesti i demencije",
            "language_label": "Jezik:",
            "archive_title": "Mjesečna arhiva",
            "archive_subtitle": "Pregledaj prošle istraživačke članke i tretmane",
            "back_to_home": "Natrag na početnu",
            "items": "stavki",
            "research_articles": "istraživačkih članaka",
            "treatments": "tretmana",
            "no_archives": "Još nema arhiviranog sadržaja. Arhiva će biti stvorena nakon prvog mjesečnog ažuriranja.",
            "footer_copyright": "Informacije o istraživanju demencije",
            "footer_note": "Samo u obrazovne svrhe."
        }
    }
    
    # Month name translations for displaying archive dates
    month_names = {
        "en": ["January", "February", "March", "April", "May", "June", 
               "July", "August", "September", "October", "November", "December"],
        "de": ["Januar", "Februar", "März", "April", "Mai", "Juni",
               "Juli", "August", "September", "Oktober", "November", "Dezember"],
        "fr": ["janvier", "février", "mars", "avril", "mai", "juin",
               "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
        "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio",
               "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
        "it": ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
               "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"],
        "hr": ["siječnja", "veljače", "ožujka", "travnja", "svibnja", "lipnja",
               "srpnja", "kolovoza", "rujna", "listopada", "studenoga", "prosinca"]
    }
    
    # Get archive directories
    lang_dir = output_dir / lang
    archive_base = lang_dir / "archive"
    
    archive_months = []
    if archive_base.exists():
        for month_folder in sorted(archive_base.iterdir(), reverse=True):
            if month_folder.is_dir() and (month_folder / "index.html").exists():
                # Parse YYYY-MM format
                try:
                    year, month = month_folder.name.split("-")
                    month_num = int(month)
                    
                    # Get localized month name
                    months = month_names.get(lang, month_names["en"])
                    month_name = months[month_num - 1]
                    
                    # Format display name by language
                    if lang == "en":
                        display_name = f"{month_name} {year}"
                    elif lang == "de":
                        display_name = f"{month_name} {year}"
                    elif lang == "fr":
                        display_name = f"{month_name} {year}"
                    elif lang == "es":
                        display_name = f"{month_name} de {year}"
                    elif lang == "it":
                        display_name = f"{month_name} {year}"
                    elif lang == "hr":
                        display_name = f"{month_name} {year}."
                    else:
                        display_name = f"{month_name} {year}"
                    
                    archive_months.append({
                        "folder": month_folder.name,
                        "display_name": display_name,
                        "item_count": 18,  # 8 research + 10 treatments
                        "research_count": 8,
                        "treatment_count": 10
                    })
                except (ValueError, IndexError):
                    continue
    
    # Setup Jinja2 template environment
    template_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("archive_page.html")
    
    # Get translations for current language
    ui = ui_translations.get(lang, ui_translations["en"])
    
    # Render HTML
    html_content = template.render(
        lang=lang,
        lang_name=lang_names.get(lang, lang.upper()),
        all_languages=settings.languages_list,
        lang_names=lang_names,
        ui=ui,
        archive_months=archive_months,
        current_year=datetime.now().year
    )
    
    # Save archive index page
    archive_index_dir = lang_dir / "archive"
    archive_index_dir.mkdir(parents=True, exist_ok=True)
    archive_index_file = archive_index_dir / "index.html"
    archive_index_file.write_text(html_content, encoding="utf-8")
    print(f"    ✓ Archive index: {archive_index_file}")


def generate_archived_page(lang: str, articles: List[Dict], treatments: List[Dict], archive_month: str, base_output_dir: Path):
    """Generate an archived page with special styling and navigation."""
    from jinja2 import Environment, FileSystemLoader
    from datetime import datetime
    
    # Calculate archive directory
    lang_dir = base_output_dir / lang
    archive_dir = lang_dir / "archive" / archive_month
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    # Use the same template but with is_archived=True
    template_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("language_page.html")
    
    # Get UI translations (reuse from generate_html_page)
    lang_names = {
        "en": "English",
        "de": "Deutsch",
        "fr": "Français",
        "es": "Español",
        "it": "Italiano",
        "hr": "Hrvatski"
    }
    
    # Simplified UI translations for archived pages
    ui_translations = {
        "en": {"archived_content": "Archived content from", "all_archives": "All Archives", "current_content": "Current Content", 
               "latest_research": "Latest Research", "latest_treatments": "Latest Treatments", "read_more": "Read more", 
               "learn_more": "Learn more", "source": "Source", "footer_copyright": "Dementia Research Information",
               "footer_note": "For educational purposes only.", "language_label": "Language:", "status_approved": "FDA Approved",
               "status_trial": "Clinical Trial", "status_research": "Research Stage"},
        "de": {"archived_content": "Archivierter Inhalt vom", "all_archives": "Alle Archive", "current_content": "Aktueller Inhalt",
               "latest_research": "Neueste Forschung", "latest_treatments": "Neueste Behandlungen", "read_more": "Weiterlesen",
               "learn_more": "Mehr erfahren", "source": "Quelle", "footer_copyright": "Demenz-Forschungsinformation",
               "footer_note": "Nur für Bildungszwecke.", "language_label": "Sprache:", "status_approved": "FDA-zugelassen",
               "status_trial": "Klinische Studie", "status_research": "Forschungsstadium"},
        "fr": {"archived_content": "Contenu archivé du", "all_archives": "Toutes les archives", "current_content": "Contenu actuel",
               "latest_research": "Dernières recherches", "latest_treatments": "Derniers traitements", "read_more": "En savoir plus",
               "learn_more": "En savoir plus", "source": "Source", "footer_copyright": "Information sur la recherche sur la démence",
               "footer_note": "À des fins éducatives uniquement.", "language_label": "Langue :", "status_approved": "Approuvé par la FDA",
               "status_trial": "Essai clinique", "status_research": "Phase de recherche"},
        "es": {"archived_content": "Contenido archivado del", "all_archives": "Todos los archivos", "current_content": "Contenido actual",
               "latest_research": "Últimas investigaciones", "latest_treatments": "Últimos tratamientos", "read_more": "Leer más",
               "learn_more": "Saber más", "source": "Fuente", "footer_copyright": "Información sobre la investigación de la demencia",
               "footer_note": "Solo con fines educativos.", "language_label": "Idioma:", "status_approved": "Aprobado por la FDA",
               "status_trial": "Ensayo clínico", "status_research": "Fase de investigación"},
        "it": {"archived_content": "Contenuto archiviato del", "all_archives": "Tutti gli archivi", "current_content": "Contenuto corrente",
               "latest_research": "Ultime ricerche", "latest_treatments": "Ultimi trattamenti", "read_more": "Leggi di più",
               "learn_more": "Scopri di più", "source": "Fonte", "footer_copyright": "Informazioni sulla ricerca sulla demenza",
               "footer_note": "Solo a scopo educativo.", "language_label": "Lingua:", "status_approved": "Approvato dalla FDA",
               "status_trial": "Sperimentazione clinica", "status_research": "Fase di ricerca"},
        "hr": {"archived_content": "Arhivirani sadržaj od", "all_archives": "Sve arhive", "current_content": "Trenutni sadržaj",
               "latest_research": "Najnovija istraživanja", "latest_treatments": "Najnoviji tretmani", "read_more": "Pročitaj više",
               "learn_more": "Saznaj više", "source": "Izvor", "footer_copyright": "Informacije o istraživanju demencije",
               "footer_note": "Samo u obrazovne svrhe.", "language_label": "Jezik:", "status_approved": "FDA odobreno",
               "status_trial": "Klinička studija", "status_research": "Faza istraživanja"}
    }
    
    ui = ui_translations.get(lang, ui_translations["en"])
    formatted_archive_date = format_date_for_language(datetime.now(), lang)
    
    # Render HTML with is_archived=True
    html_content = template.render(
        lang=lang,
        lang_name=lang_names.get(lang, lang.upper()),
        all_languages=settings.languages_list,
        lang_names=lang_names,
        ui=ui,
        articles=articles,
        treatments=treatments,
        update_date=formatted_archive_date,
        current_year=datetime.now().year,
        is_archived=True,
        archive_date=formatted_archive_date
    )
    
    # Save archived page
    archive_file = archive_dir / "index.html"
    archive_file.write_text(html_content, encoding="utf-8")
    return archive_file


def create_template(template_file: Path):
    """Create the Jinja2 HTML template."""
    template_content = """<!DOCTYPE html>
<html lang="{{ lang }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dementia Research and Treatments Information</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body class="bg-gray-50 min-h-screen">
    <!-- Header -->
    <header class="bg-blue-600 text-white shadow-lg">
        <div class="container mx-auto px-4 py-6">
            <div class="flex flex-col md:flex-row justify-between items-center">
                <div class="flex items-center mb-4 md:mb-0">
                    <i class="fas fa-brain text-4xl mr-4"></i>
                    <div>
                        <h1 class="text-3xl font-bold">Dementia Research and Treatments Information</h1>
                        <p class="text-blue-100 text-sm mt-1">Latest Updates on Alzheimer's and Dementia Research</p>
                    </div>
                </div>
                
                <!-- Language Selector -->
                <div class="flex items-center">
                    <label for="language" class="mr-2 text-sm">
                        <i class="fas fa-globe mr-1"></i> Language:
                    </label>
                    <select id="language" onchange="changeLanguage(this.value)" class="bg-white text-gray-800 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-300">
                        {% for l in all_languages %}
                        <option value="{{ l }}" {% if l == lang %}selected{% endif %}>{{ lang_names.get(l, l.upper()) }}</option>
                        {% endfor %}
                    </select>
                </div>
            </div>
        </div>
    </header>

    <!-- Main Content -->
    <main class="container mx-auto px-4 py-8">
        <!-- Update Notice -->
        <div class="bg-blue-50 border-l-4 border-blue-400 p-4 mb-8">
            <div class="flex">
                <div class="flex-shrink-0">
                    <i class="fas fa-info-circle text-blue-400"></i>
                </div>
                <div class="ml-3">
                    <p class="text-sm text-blue-700">
                        Last updated: {{ update_date }} | Content is automatically updated monthly
                    </p>
                </div>
            </div>
        </div>

        <!-- Latest Research Section -->
        <section class="mb-12">
            <div class="flex items-center mb-6">
                <i class="fas fa-microscope text-3xl text-blue-600 mr-3"></i>
                <h2 class="text-3xl font-bold text-gray-800">Latest Research</h2>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {% for article in articles %}
                <div class="bg-white rounded-lg shadow-md p-6 hover:shadow-xl transition-shadow duration-300">
                    <div class="flex items-start justify-between mb-3">
                        <span class="text-xs font-semibold text-blue-600 bg-blue-100 px-2 py-1 rounded">{{ article.source }}</span>
                        <span class="text-xs text-gray-500">{{ article.publication_date[:10] }}</span>
                    </div>
                    <h3 class="text-xl font-bold text-gray-800 mb-3">{{ article.title }}</h3>
                    <p class="text-gray-600 mb-4">{{ article.summary }}</p>
                    <div class="flex items-center justify-between">
                        <div class="text-xs text-gray-500">
                            <i class="fas fa-user mr-1"></i>
                            {{ article.authors[:2]|join(', ') }}{% if article.authors|length > 2 %} et al.{% endif %}
                        </div>
                        {% if article.url %}
                        <a href="{{ article.url }}" target="_blank" class="text-blue-600 hover:text-blue-800 text-sm font-semibold">
                            Read more <i class="fas fa-external-link-alt ml-1"></i>
                        </a>
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </section>

        <!-- Latest Treatments Section -->
        <section class="mb-12">
            <div class="flex items-center mb-6">
                <i class="fas fa-pills text-3xl text-green-600 mr-3"></i>
                <h2 class="text-3xl font-bold text-gray-800">Latest Treatments</h2>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {% for treatment in treatments %}
                <div class="bg-white rounded-lg shadow-md p-6 hover:shadow-xl transition-shadow duration-300">
                    <div class="flex items-start justify-between mb-3">
                        {% if treatment.status == 'approved' %}
                        <span class="text-xs font-semibold px-2 py-1 rounded bg-green-100 text-green-800">FDA Approved</span>
                        {% elif treatment.status == 'clinical_trial' %}
                        <span class="text-xs font-semibold px-2 py-1 rounded bg-yellow-100 text-yellow-800">Clinical Trial</span>
                        {% else %}
                        <span class="text-xs font-semibold px-2 py-1 rounded bg-blue-100 text-blue-800">Research Stage</span>
                        {% endif %}
                        {% if treatment.approval_date %}
                        <span class="text-xs text-gray-500">{{ treatment.approval_date[:4] }}</span>
                        {% endif %}
                    </div>
                    <h3 class="text-xl font-bold text-gray-800 mb-3">{{ treatment.name }}</h3>
                    <p class="text-gray-600 mb-4">{{ treatment.description }}</p>
                    {% if treatment.url %}
                    <a href="{{ treatment.url }}" target="_blank" class="text-green-600 hover:text-green-800 text-sm font-semibold">
                        Learn more <i class="fas fa-external-link-alt ml-1"></i>
                    </a>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
        </section>
    </main>

    <!-- Footer -->
    <footer class="bg-gray-800 text-white py-6 mt-12">
        <div class="container mx-auto px-4 text-center">
            <p class="text-sm">
                <i class="fas fa-code mr-2"></i>
                Powered by <span class="font-semibold">FastAPI</span> and 
                <span class="font-semibold">Google Translate</span>
            </p>
            <p class="text-xs text-gray-400 mt-2">
                &copy; 2024 Dementia Research Information. For educational purposes only.
            </p>
        </div>
    </footer>

    <script>
        function changeLanguage(lang) {
            window.location.href = '/' + lang + '/';
        }
    </script>
</body>
</html>
"""
    template_file.write_text(template_content, encoding="utf-8")
    print(f"  ✓ Created template: {template_file}")


async def main():
    """Main function to fetch, translate, and generate pages."""
    print("🚀 Starting monthly update process...")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Fetch latest data
    print("📊 Fetching latest research and treatments...")
    articles_raw = await get_latest_research()
    treatments_raw = await get_latest_treatments()
    
    # Convert to dictionaries for easier handling
    articles = [article.model_dump() for article in articles_raw]
    treatments = [treatment.model_dump() for treatment in treatments_raw]
    
    # Convert datetime objects to strings
    for article in articles:
        if isinstance(article['publication_date'], datetime):
            article['publication_date'] = article['publication_date'].isoformat()
    
    for treatment in treatments:
        if treatment.get('approval_date') and isinstance(treatment['approval_date'], datetime):
            treatment['approval_date'] = treatment['approval_date'].isoformat()
    
    print(f"  ✓ Found {len(articles)} research articles")
    print(f"  ✓ Found {len(treatments)} treatments")
    print()
    
    # Output directory
    output_dir = Path(__file__).parent.parent / "static" / "languages"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Archive current content before updating (if exists)
    current_month = datetime.now().strftime("%Y-%m")
    print(f"💾 Archiving current content for {current_month}...")
    
    # Store current articles and treatments for archiving
    archived_articles = {}
    archived_treatments = {}
    
    for lang in settings.languages_list:
        lang_dir = output_dir / lang
        current_page = lang_dir / "index.html"
        
        if current_page.exists():
            # We'll regenerate the archive pages after we translate new content
            # For now, just note that we need to archive this language
            archived_articles[lang] = articles.copy()
            archived_treatments[lang] = treatments.copy()
    
    if archived_articles:
        print(f"  ✓ Marked {len(archived_articles)} languages for archiving")
    print()
    
    # Process each language
    for lang in settings.languages_list:
        print(f"🌐 Processing language: {lang.upper()}")
        
        # Translate content
        print(f"  🔄 Translating articles...")
        translated_articles = await translate_articles(articles, lang)
        
        print(f"  🔄 Translating treatments...")
        translated_treatments = await translate_treatments(treatments, lang)
        
        # Generate HTML page
        print(f"  📄 Generating HTML page...")
        generate_html_page(lang, translated_articles, translated_treatments, output_dir)
        
        # Generate archived version if this language had existing content
        if lang in archived_articles:
            print(f"  📦 Generating archived page for {current_month}...")
            # Translate the old articles/treatments for archiving
            archived_translated_articles = await translate_articles(archived_articles[lang], lang)
            archived_translated_treatments = await translate_treatments(archived_treatments[lang], lang)
            
            # Generate archived page with proper metadata
            archive_file = generate_archived_page(lang, archived_translated_articles, archived_translated_treatments, 
                                                  current_month, output_dir)
            print(f"    ✓ Archived: {archive_file}")
        
        # Generate archive index
        print(f"  📚 Generating archive index...")
        generate_archive_index(lang, output_dir)
        
        print()
    
    # Create redirect for root URL
    print("📝 Creating root redirect...")
    root_html = output_dir.parent / "index_multilang.html"
    root_html.write_text("""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="0; url=/languages/en/">
    <title>Redirecting...</title>
</head>
<body>
    <p>Redirecting to English version...</p>
    <p>If you are not redirected, <a href="/languages/en/">click here</a>.</p>
</body>
</html>
""", encoding="utf-8")
    print(f"  ✓ Created: {root_html}")
    print()
    
    print("✅ Monthly update completed successfully!")
    print(f"📁 Generated pages in: {output_dir}")
    print()
    print("Next steps:")
    print("  1. Pages are ready to serve at: http://localhost:8000/languages/<lang>/")
    print("  2. Set up a cron job to run this script monthly")
    print("  3. Deploy to production!")


if __name__ == "__main__":
    asyncio.run(main())
