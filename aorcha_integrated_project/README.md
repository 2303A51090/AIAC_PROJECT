# AORCHA Integrated Project

This is the enhanced primary project with useful features integrated from the secondary NexusOrch project.

## What was integrated

- Added a new **Agent Lab** navbar section.
- Integrated a custom agent sandbox:
  - Add custom agents
  - Set priority from 1 to 10
  - Set CPU requirement
  - Run local priority-weighted bidding
  - View ephemeral containers
  - Track execution history
  - View a secure message-bus style terminal log
- Kept the original AORCHA design, layout, and dark interface.
- Preserved the original backend-powered **Live Orchestrator** using Flask + Server-Sent Events.

## Project Structure

```text
aorcha_integrated_project/
├── app.py
├── requirements.txt
├── README.md
└── static/
    └── index.html
```

## Run

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

Mac/Linux:

```bash
source venv/bin/activate
```

Install packages:

```bash
pip install -r requirements.txt
```

Start server:

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Pages

- **Home** — project overview
- **Dashboard** — live-style system metrics
- **Orchestrator** — backend-powered multi-agent workflow
- **Agent Lab** — newly integrated custom agent simulation section
- **Architecture** — system layers and comparison
