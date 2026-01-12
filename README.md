# Scent Australia Lead Generation Backend

AI-powered lead generation backend using Apollo.io integration for finding and managing potential business leads.

## Features

- **Apollo.io Integration**: Access 275M+ contacts and 73M+ companies
- **AI-Powered Analysis**: GPT-4 analyzes leads for fit, priority, and recommendations
- **Lead Management**: Full CRUD operations with status tracking
- **Data Export**: Export leads to Excel or CSV
- **Real-time Job Tracking**: Monitor lead generation progress

## Quick Start

### Prerequisites

- Python 3.9+
- Apollo.io API Key with **People Search** access (get from [Apollo Settings](https://app.apollo.io/#/settings/integrations/api))
  - **Note**: Not all Apollo.io plans include People Search API access. You may need a paid plan.
  - If you get a 403 error, your API key may not have access to the People Search endpoint.
  - You can still use Organization Search which may be available on lower-tier plans.
- OpenAI API Key (for AI analysis)

### Installation

```bash
# Clone and navigate to backend
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file and configure
cp env.example .env
# Edit .env with your API keys
```

### Configuration

Create a `.env` file with the following:

```env
# Required
APOLLO_API_KEY=your-apollo-api-key-here
OPENAI_API_KEY=your-openai-api-key-here

# Optional
FLASK_DEBUG=1
OPENAI_MODEL=gpt-4-turbo-preview
```

### Run the Server

```bash
python run.py
```

The server will start at `http://localhost:5000`

## API Endpoints

### Apollo.io Lead Generation

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/apollo/search/people` | POST | Search for people/contacts |
| `/api/apollo/search/organizations` | POST | Search for organizations |
| `/api/apollo/generate` | POST | Generate and save leads with AI analysis |
| `/api/apollo/status/<job_id>` | GET | Get job status |
| `/api/apollo/jobs` | GET | List all jobs |
| `/api/apollo/enrich` | POST | Enrich a contact |
| `/api/apollo/config` | GET | Get Apollo configuration |

### Lead Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/leads` | GET | Get all leads |
| `/api/leads` | POST | Create new lead |
| `/api/leads/<id>` | GET | Get single lead |
| `/api/leads/<id>` | PUT | Update lead |
| `/api/leads/<id>` | DELETE | Delete lead |
| `/api/leads/<id>/analyze` | POST | AI analyze lead |
| `/api/leads/bulk-analyze` | POST | Bulk AI analysis |
| `/api/leads/stats` | GET | Get lead statistics |

### Export

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/export/excel` | POST | Export to Excel |
| `/api/export/csv` | POST | Export to CSV |
| `/api/export/download/<filename>` | GET | Download file |

## Example: Generate Leads

```bash
curl -X POST http://localhost:5000/api/apollo/generate \
  -H "Content-Type: application/json" \
  -d '{
    "search_type": "people",
    "person_titles": ["CEO", "Director", "Owner"],
    "person_locations": ["Sydney, Australia", "Melbourne, Australia"],
    "organization_industries": ["hospitality", "retail"],
    "max_leads": 25,
    "analyze_with_ai": true,
    "save_leads": true
  }'
```

## Project Structure

```
backend/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration
│   ├── models/
│   │   └── lead.py          # Lead model
│   ├── routes/
│   │   ├── apollo.py        # Apollo.io endpoints
│   │   ├── leads.py         # Lead management
│   │   ├── export.py        # Export functionality
│   │   └── health.py        # Health check
│   └── services/
│       ├── apollo_service.py    # Apollo.io API client
│       ├── ai_analyzer.py       # AI analysis
│       ├── lead_manager.py      # Lead management
│       └── export_service.py    # Export service
├── requirements.txt
├── run.py
└── README.md
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `APOLLO_API_KEY` | Yes | Apollo.io API key |
| `OPENAI_API_KEY` | Yes* | OpenAI API key (*for AI features) |
| `OPENAI_MODEL` | No | OpenAI model (default: gpt-4-turbo-preview) |
| `FLASK_DEBUG` | No | Enable debug mode (default: 1) |
| `EXPORT_FOLDER` | No | Export directory (default: exports) |

## License

MIT
