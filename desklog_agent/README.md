# Desklog Agent (Ubuntu-only)

Python agent for Ubuntu (X11/Wayland) to track user activity and upload screenshots to the Odoo Desklog module (Odoo 18.0). Windows support is intentionally removed in this setup.

Features:
- Registers to Odoo and gets a token
- Sends periodic pings and activity logs (active/idle/locked)
- Captures screenshots on schedule and uploads with JPEG/PNG

## Usage
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python agent.py --server http://your-odoo:8069 --db yourdb -u youruser -p yourpass
```

Environment variables can be used instead of CLI flags.

## Wayland note (grim)
On Wayland sessions, install `grim` to enable screenshots (works on Sway/Hyprland/wlroots-based compositors):
```bash
sudo apt update && sudo apt install -y grim
```
On X11 sessions, screenshots work out of the box via `mss`.

GNOME Wayland caveat: non-interactive screenshots are generally blocked by design. For unattended capture, use an Xorg session (choose "Ubuntu on Xorg" at login) or use an xdg-desktop-portal flow that requires user approval.

## Run as a systemd user service (recommended)
Run the agent in your desktop user session so it can access the display for screenshots.

1) Install the agent code:
```bash
mkdir -p ~/.local/share/desklog_agent
cp -r desklog_agent/* ~/.local/share/desklog_agent/
cd ~/.local/share/desklog_agent
python3 -m venv .venv
~/.local/share/desklog_agent/.venv/bin/pip install -r requirements.txt
```

2) Create a user unit:
```bash
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/desklog-agent.service <<'UNIT'
[Unit]
Description=Desklog Agent (User)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
Environment=DESKLOG_USER=youruser
Environment=DESKLOG_PASS=yourpass
ExecStart=%h/.local/share/desklog_agent/.venv/bin/python %h/.local/share/desklog_agent/agent.py --server http://your-odoo:8069 --db yourdb
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
UNIT
```

3) Enable and start it:
```bash
systemctl --user enable desklog-agent.service
systemctl --user start desklog-agent.service
```

Tip: enable lingering to run on login: `sudo loginctl enable-linger "$USER"`.
