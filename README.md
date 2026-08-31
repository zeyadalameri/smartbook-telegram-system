# SmartBook Telegram Integration

A Python integration prototype that receives Telegram messages, displays operational activity in a Flask dashboard, and connects selected workflows to an external SmartBook API.

## Overview

The repository combines a Telegram client, a small local web dashboard, SmartBook authentication and API helpers, and JSON-based operational logs. It was built to explore message-driven integration and monitoring workflows; it is not a public Telegram bot service or a production-ready deployment.

## Key Features

- Telegram user-session connection with Telethon
- Incoming-message collection and local structured logging
- Flask dashboard for activity, status, and statistics
- SmartBook API sign-in and authenticated request helpers
- Configurable message filtering
- Windows-oriented launcher for starting the local components

## Tech Stack

- Python
- Flask and Flask-Cors
- Telethon
- Requests
- python-dotenv
- HTML templates and local JSON storage

## Architecture

The launcher coordinates the dashboard and Telegram receiver. Telethon handles the Telegram session, the Flask application exposes local monitoring routes, and dedicated modules wrap SmartBook authentication and API calls. Runtime logs, tokens, and Telegram session files are local-only and excluded from Git.

## Getting Started

1. Create and activate a Python virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a local `.env` containing your own Telegram application credentials and the required SmartBook API configuration.
4. Start the launcher on Windows:

```bash
python launcher.py
```

Use only accounts and messages you are authorized to access. Never commit Telegram sessions, API tokens, logs, or exported message data.

## My Role

I implemented the Telegram session workflow, message receiver, Flask monitoring dashboard, SmartBook API integration, authentication helpers, logging, and launcher coordination.

## Skills Demonstrated

Python integration development, Flask, external REST APIs, Telegram client automation, token handling, event-driven processing, operational logging, and local dashboard development.

## Project Status and Limitations

- Integration and automation prototype; not a production service
- Requires external SmartBook and Telegram credentials
- The external SmartBook API is not included in this repository
- Uses local JSON files rather than a transactional database
- Windows-focused launcher and no automated test suite
- Provider API or Telegram client changes may require maintenance

## Privacy

Screenshots containing account identifiers were intentionally removed from the public portfolio version. Runtime data is ignored by Git and should remain private.

## License

No open-source license has been declared.
