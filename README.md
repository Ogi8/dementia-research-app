# Dementia Research and Treatments Information

A modern, multilingual web application that presents the latest research papers and treatments related to dementia and Alzheimer's disease. Features pre-translated static pages in 6 languages with monthly automatic updates.

## 🌟 Features

- **Latest Research**: Curated dementia and Alzheimer's research papers
- **Treatment Information**: Up-to-date approved and experimental treatments
- **6 Languages**: English, German, French, Spanish, Italian, and Croatian
- **Static Pre-translated Pages**: Instant loading, no API calls per user
- **Monthly Auto-updates**: Content refreshes automatically once per month
- **Completely Free**: No API keys required, uses free Google Translate
- **SEO-Friendly**: Each language has its own URL
- **Production-Ready**: Scalable architecture for unlimited traffic

## 🏗️ Architecture

### Smart Pre-translation Approach

Instead of translating on every user request, the application:

1. **Monthly Background Job** fetches latest research
2. **Translates once** to all 6 languages using free Google Translate
3. **Generates static HTML pages** for each language
4. **Users load pre-translated pages** instantly - no waiting, no API costs

### Benefits

✅ **Zero cost** - No API charges per user  
✅ **Lightning fast** - Pre-generated pages load instantly  
✅ **Scalable** - Handle unlimited traffic without API limits  
✅ **SEO optimized** - Each language at `/languages/{lang}/`  
✅ **Offline-capable** - Static content works without APIs  

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager

No API keys needed! 🎉

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd dementia_page
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Generate multilingual pages** (first time setup)
   ```bash
   uv run python scripts/monthly_update.py
   ```

4. **Start the server**
   ```bash
   uv run uvicorn app.main:app --reload
   ```

The application will be available at:
- **Multilingual site**: http://localhost:8000/languages/en/
- **API docs**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health

## 📚 Available Languages

Access each language directly:

- 🇬🇧 English: `/languages/en/`
- 🇩🇪 German: `/languages/de/`
- 🇫🇷 French: `/languages/fr/`
- 🇪🇸 Spanish: `/languages/es/`
- 🇮🇹 Italian: `/languages/it/`
- 🇭🇷 Croatian: `/languages/hr/`

## 🔄 Monthly Updates

### Manual Update

Run the monthly update script anytime:

```bash
uv run python scripts/monthly_update.py
```

This will:
1. Fetch latest research and treatments
2. Translate to all 6 languages
3. Generate new HTML pages

### Automated Monthly Updates

Set up a cron job to run monthly:

```bash
# Edit crontab
crontab -e

# Add this line (runs on 1st of each month at 2 AM)
0 2 1 * * cd /path/to/dementia_page && uv run python scripts/monthly_update.py
```

Or use **Render.com Cron Jobs** (see deployment section).

## 🏗️ Project Structure

```
dementia_page/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── models.py            # Data models
│   └── services/
│       ├── cache.py         # Caching
│       ├── research.py      # Research data
│       └── translator.py    # Google Translate (free)
├── scripts/
│   └── monthly_update.py    # Monthly translation job
├── static/
│   ├── languages/           # Generated multilingual pages
│   │   ├── en/index.html
│   │   ├── de/index.html
│   │   ├── fr/index.html
│   │   ├── es/index.html
│   │   ├── it/index.html
│   │   └── hr/index.html
│   └── index_multilang.html # Root redirect
├── templates/
│   └── language_page.html   # Jinja2 template
├── Dockerfile
├── render.yaml
└── pyproject.toml
```

## 🚢 Deployment

### Render.com (Recommended)

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git push origin main
   ```

2. **Create Render Web Service**
   - Go to [render.com](https://render.com)
   - Connect your GitHub repo
   - Render auto-detects `render.yaml`
   - Deploy!

3. **Set up Monthly Cron Job** on Render
   - Go to Dashboard → Cron Jobs → New Cron Job
   - Command: `uv run python scripts/monthly_update.py`
   - Schedule: `0 2 1 * *` (monthly)

### Docker

```bash
# Build
docker build -t dementia-research-app .

# Run
docker run -p 8000:8000 dementia-research-app
```

## 📊 API Endpoints

The application also provides API endpoints:

### Research & Treatments
- `GET /api/news` - Latest research articles
- `GET /api/treatments` - Treatment information

### Translation (Real-time)
- `POST /api/translate` - Translate text on-demand
  ```json
  {
    "text": "Text to translate",
    "target_language": "de"
  }
  ```

### Health Check
- `GET /health` - Service status

API documentation: http://localhost:8000/docs

## 🔧 Configuration

### Environment Variables

Create a `.env` file (optional):

```env
APP_NAME=Dementia Research and Treatments Information
APP_VERSION=1.0.0
CACHE_TTL=3600
SUPPORTED_LANGUAGES=en,de,fr,es,it,hr
```

### Add More Languages

1. Edit `.env`:
   ```env
   SUPPORTED_LANGUAGES=en,de,fr,es,it,hr,pt,nl
   ```

2. Run update script:
   ```bash
   uv run python scripts/monthly_update.py
   ```

3. New language pages generated automatically!

## 🧪 Development

### Run with auto-reload

```bash
uv run uvicorn app.main:app --reload
```

### Update translations

```bash
uv run python scripts/monthly_update.py
```

### Add new research sources

Edit `app/services/research.py` to integrate with:
- PubMed API
- ClinicalTrials.gov API
- Europe PMC API
- Other research databases

## 📝 Roadmap

- [ ] Integrate with real PubMed API
- [ ] Add ClinicalTrials.gov integration
- [ ] RSS feed for updates
- [ ] Email notifications for new research
- [ ] Search functionality
- [ ] User bookmarks (with authentication)
- [ ] PDF export of research summaries
- [ ] Admin panel for content management

## 💡 Why This Architecture?

### Old Approach (API per user)
- User clicks language → API call → wait → translated
- **Cost**: $0.01 × 10,000 users = $100/month
- **Speed**: 2-3 seconds wait time
- **Scalability**: Limited by API rate limits

### New Approach (Pre-translation)
- Monthly job → translate once → serve static pages
- **Cost**: $0.00 (free tier covers monthly updates)
- **Speed**: Instant (static HTML)
- **Scalability**: Unlimited (just static files)

## 📄 License

This project is for educational purposes. Please ensure compliance with content sources' terms of service.

## 🤝 Contributing

Contributions welcome! Please submit a Pull Request.

## 📧 Support

For issues and questions, open an issue on GitHub.

---

**Powered by FastAPI, Google Translate (free), and smart architecture** 🚀
