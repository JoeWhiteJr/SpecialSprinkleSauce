"""
Notion Ticket Management for Wasden Watch
Creates and manages tickets in the Notion database.
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

NOTION_VERSION = "2022-06-28"
NOTION_BASE_URL = "https://api.notion.com/v1"

headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION,
}


def test_connection():
    """Test the Notion API connection by fetching database info."""
    url = f"{NOTION_BASE_URL}/databases/{NOTION_DATABASE_ID}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        print("Connection successful!")
        print(f"Database title: {data.get('title', [{}])[0].get('plain_text', 'Unknown')}")
        print(f"Properties found: {list(data.get('properties', {}).keys())}")
        return data
    else:
        print(f"Connection failed: {response.status_code}")
        print(f"Error: {response.json()}")
        return None


def get_database_schema():
    """Get the database schema to understand available properties."""
    url = f"{NOTION_BASE_URL}/databases/{NOTION_DATABASE_ID}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        properties = data.get("properties", {})

        print("\n--- Database Schema ---")
        for prop_name, prop_info in properties.items():
            prop_type = prop_info.get("type", "unknown")
            print(f"  {prop_name}: {prop_type}")

        return properties
    else:
        print(f"Failed to get schema: {response.status_code}")
        print(f"Error: {response.json()}")
        return None


def create_ticket(
    title,
    description="",
    status="Not Started",
    priority="Medium",
    category="Feature",
    due_date=None
):
    """
    Create a new ticket in the Notion database.

    Args:
        title: Ticket title (required)
        description: Detailed description (added as page content)
        status: "Not Started", "In Progress", "Blocked", "Done" (adjust to your options)
        priority: "Low", "Medium", "High", "Critical" (adjust to your options)
        category: "Feature", "Bug", "Task", etc. (adjust to your options)
        due_date: Due date in YYYY-MM-DD format
    """
    url = f"{NOTION_BASE_URL}/pages"

    # Build properties based on actual database schema
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Title": {
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ]
            }
        }
    }

    # Add optional properties if provided
    if status:
        payload["properties"]["Status"] = {
            "select": {"name": status}
        }

    if priority:
        payload["properties"]["Priority"] = {
            "select": {"name": priority}
        }

    if category:
        payload["properties"]["Category/Type"] = {
            "select": {"name": category}
        }

    if due_date:
        payload["properties"]["Due Date"] = {
            "date": {"start": due_date}
        }

    # Add description as page content if provided
    if description:
        payload["children"] = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": description}
                        }
                    ]
                }
            }
        ]

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        data = response.json()
        print(f"Ticket created successfully!")
        print(f"Page ID: {data.get('id')}")
        print(f"URL: {data.get('url')}")
        return data
    else:
        print(f"Failed to create ticket: {response.status_code}")
        print(f"Error: {response.json()}")
        return None


if __name__ == "__main__":
    print("=== Notion Ticket System Test ===\n")

    # Test 1: Check connection
    print("1. Testing connection...")
    result = test_connection()

    if result:
        # Test 2: Get schema
        print("\n2. Fetching database schema...")
        schema = get_database_schema()

        # Test 3: Create a test ticket
        print("\n3. Creating test ticket...")
        create_ticket(
            title="[TEST] Notion Integration Working",
            description="This is a test ticket created by the SpecialSprinkleSauce project to verify Notion API integration is working correctly.",
            status="Not Started",
            priority="Low",
            category="Task"
        )
