# SmartBook Telegram Integration System

A Python-based backend automation system that receives Telegram messages, filters and validates them, integrates with the SmartBook API, and provides a monitoring dashboard for logs, authentication, and message processing.

## Project Overview

This project was built as a real-world backend automation system. It demonstrates practical experience with Python, Flask, Telegram integration, REST APIs, authentication/token handling, logging, and dashboard-based monitoring.

## Key Features

- Receive and process Telegram messages
- Filter allowed and blocked numbers
- Validate and structure message content
- Integrate with the SmartBook API
- Handle authentication and token management
- Monitor messages through a Flask dashboard
- Store and display logs/statistics
- Manage sessions and launcher workflow

## Tech Stack

- **Language:** Python
- **Backend:** Flask
- **Telegram integration:** Telethon / Telegram API workflow
- **API communication:** REST APIs
- **Storage:** JSON-based local storage/logging
- **Dashboard:** Flask templates

## System Workflow

```text
Telegram Messages
      ↓
Telegram Receiver
      ↓
Filtering & Validation
      ↓
SmartBook Authentication
      ↓
SmartBook API Integration
      ↓
Dashboard / Logs / Statistics
```

## Main Components

- `telegram_receiver.py` — receives and processes Telegram messages
- `api_integration.py` — handles API communication
- `smartbook_auth.py` — manages authentication/token workflow
- `dashboard.py` — Flask-based monitoring dashboard
- `logger.py` — logging and statistics support
- `session_manager.py` — session handling
- `launcher.py` — project launcher

## My Role

- Designed the backend automation workflow
- Implemented Telegram message receiving and processing logic
- Integrated the system with SmartBook API endpoints
- Implemented authentication and token handling
- Built dashboard and logging features for monitoring

## Screenshots

### Login
![Login](https://raw.githubusercontent.com/zeyadalameri/smartbook-telegram-system/main/screenshots/login.png)

### Smart API
![Smart API](https://raw.githubusercontent.com/zeyadalameri/smartbook-telegram-system/main/screenshots/login-smart-api.png)

### Dashboard
![Dashboard](https://raw.githubusercontent.com/zeyadalameri/smartbook-telegram-system/main/screenshots/dashboard.png)

### Logs
![Logs](https://raw.githubusercontent.com/zeyadalameri/smartbook-telegram-system/main/screenshots/log.png)

### Numbers
![Numbers](https://raw.githubusercontent.com/zeyadalameri/smartbook-telegram-system/main/screenshots/number.png)

### Launcher
![Launcher](https://raw.githubusercontent.com/zeyadalameri/smartbook-telegram-system/main/screenshots/launcher.png)

## Getting Started

```bash
pip install -r requirements.txt
python launcher.py
```

> Note: API credentials, Telegram session settings, and environment-specific configuration may be required before running the project.

## Skills Demonstrated

- Backend development
- API integration
- Authentication/token handling
- Automation workflows
- Logging and monitoring
- Python/Flask application structure

## What I Learned

- Building backend automation around external APIs
- Managing authentication tokens and sessions
- Designing monitoring dashboards for operational visibility
- Structuring Python projects for real-world automation
- Handling logs and message-processing workflows

## Author

**Zeyad Alameri**  
Information Technology Graduate | Full-Stack Developer  
GitHub: [@zeyadalameri](https://github.com/zeyadalameri)
