# Scent Australia Lead Generation AI Backend

A Python Flask backend for AI-powered lead generation and analysis for Scent Australia.

## Features

- **Web Scraping**: Automated scraping from Google Search, Yellow Pages, and business directories
- **AI Analysis**: OpenAI/Azure OpenAI powered lead scoring and analysis
- **Lead Management**: Full CRUD operations for lead management
- **Data Export**: Export leads to Excel, CSV, and JSON formats
- **RESTful API**: Clean API endpoints for frontend integration

## Project Structure

```
backend/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration settings
│   ├── models/
│   │   ├── __init__.py
│   │   └── lead.py          # Lead data model
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── health.py        # Health check endpoints
│   │   ├── leads.py         # Lead management endpoints
│   │   ├── scraper.py       # Web scraping endpoints
│   │   └── export.py        # Data export endpoints
│   └── services/
│       ├── __init__.py
│       ├── lead_manager.py  # Lead storage and management
│       ├── scraper_service.py   # Web scraping service
│       ├── ai_analyzer.py   # AI-powered analysis
│       └── export_service.py    # Data export service
├── data/                    # Data storage directory
├── exports/                 # Exported files directory
├── logs/                    # Application logs
├── requirements.txt         # Python dependencies
├── run.py                   # Application entry point
└── env.example             # Environment variables template
```

## Installation

### Prerequisites

- Python 3.10+
- pip (Python package manager)

### Setup

1. **Create virtual environment:**
   ```bash
   cd backend
   python -m venv venv
   ```

2. **Activate virtual environment:**
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp env.example .env
   ```
   Edit `.env` and add your API keys:
   - `OPENAI_API_KEY`: Your OpenAI API key (or Azure OpenAI credentials)
   - `SECRET_KEY`: A secure secret key for Flask

5. **Run the application:**
   ```bash
   python run.py
   ```

The server will start at `http://localhost:5000`

## API Endpoints

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/` | API information |

### Leads

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/leads` | List all leads (with filtering) |
| GET | `/api/leads/<id>` | Get single lead |
| POST | `/api/leads` | Create new lead |
| PUT | `/api/leads/<id>` | Update lead |
| DELETE | `/api/leads/<id>` | Delete lead |
| POST | `/api/leads/<id>/analyze` | AI analyze lead |
| POST | `/api/leads/bulk-analyze` | Bulk AI analysis |
| GET | `/api/leads/stats` | Get lead statistics |

### Scraper

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/scraper/start` | Start scraping job |
| GET | `/api/scraper/status/<job_id>` | Get job status |
| GET | `/api/scraper/jobs` | List all jobs |
| POST | `/api/scraper/stop/<job_id>` | Stop job |
| POST | `/api/scraper/preview` | Preview scraping |
| GET | `/api/scraper/config` | Get scraper config |

### Export

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/export/excel` | Export to Excel |
| POST | `/api/export/csv` | Export to CSV |
| GET | `/api/export/download/<filename>` | Download file |
| GET | `/api/export/files` | List exported files |
| DELETE | `/api/export/delete/<filename>` | Delete file |

## Query Parameters (GET /api/leads)

- `status`: Filter by status (new, contacted, qualified, converted, lost)
- `priority`: Filter by priority (high, medium, low)
- `industry`: Filter by industry
- `location`: Filter by location
- `search`: Search term
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20)

## Example Usage

### Start a Scraping Job

```bash
curl -X POST http://localhost:5000/api/scraper/start \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["fragrance retail", "spa wellness"],
    "locations": ["Sydney, NSW", "Melbourne, VIC"],
    "max_leads": 50,
    "analyze_with_ai": true
  }'
```

### Get Leads

```bash
curl http://localhost:5000/api/leads?status=new&priority=high&page=1
```

### Export to Excel

```bash
curl -X POST http://localhost:5000/api/export/excel \
  -H "Content-Type: application/json" \
  -d '{"status": "new"}'
```

## Configuration

Key configuration options in `config.py`:

- **TARGET_INDUSTRIES**: Industries to target for lead generation
- **TARGET_LOCATIONS**: Australian locations to search
- **MAX_LEADS_PER_RUN**: Maximum leads per scraping job
- **SCRAPING_DELAY**: Delay between requests (seconds)

## AI Analysis

The AI analyzer provides:

- **Lead Scoring** (0-100): Based on fit with Scent Australia's target market
- **Priority Assignment**: High, Medium, or Low
- **Fit Assessment**: Excellent, Good, Moderate, or Poor
- **Industry Relevance Score**
- **Recommended Products**: Based on industry
- **Talking Points**: Customized sales talking points
- **Next Steps**: Suggested follow-up actions
- **Risk Factors**: Potential concerns

### Fallback Analysis

If OpenAI is not configured, a fallback analysis system provides basic scoring based on:
- Available contact information
- Industry relevance
- Location (major city bonus)

## Development

### Running Tests

```bash
pytest tests/
```

### Code Structure

- **Models**: Data classes for lead representation
- **Routes**: API endpoint handlers
- **Services**: Business logic and external integrations

## Future Enhancements

- [ ] Database integration (PostgreSQL/MongoDB)
- [ ] Selenium for JavaScript-heavy sites
- [ ] LinkedIn scraping (with proper authentication)
- [ ] Automation King integration
- [ ] Scheduled scraping jobs
- [ ] Email verification service
- [ ] CRM export integrations

## License

Proprietary - Scent Australia

