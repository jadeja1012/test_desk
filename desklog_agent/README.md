# Desklog Agent

Cross-platform Python agent for Ubuntu (X11/Wayland) and Windows to track user activity and upload screenshots to Odoo Desklog module.

Features:
- Registers to Odoo and gets a token
- Sends periodic pings and activity logs (active/idle/locked)
- Captures screenshots on schedule and uploads with JPEG/PNG

Usage:
```
python -m venv .venv
source .venv/bin/activate  # on Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python agent.py --server http://your-odoo:8069 --db yourdb -u youruser -p yourpass
```

Environment variables can be used instead of CLI flags.
