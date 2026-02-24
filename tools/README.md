# Tools

Project management and utility scripts for the Wasden Watch trading system.

## notion_tickets.py

Connects to the Notion ticketing database for creating and managing project tickets.

### Setup

1. Copy `.env.example` to `.env` in the project root
2. Add your Notion API key and database ID
3. Ensure your Notion integration is connected to your database

### Usage

```python
from tools.notion_tickets import create_ticket, test_connection, get_database_schema

# Test connection
test_connection()

# View database schema
get_database_schema()

# Create a ticket
create_ticket(
    title="Implement XGBoost model",
    description="Train XGBoost classifier for 5-day forward return prediction",
    status="Not Started",
    priority="High",
    category="Feature",
    due_date="2026-03-15"
)
```

### Requirements

```
python-dotenv
requests
```
