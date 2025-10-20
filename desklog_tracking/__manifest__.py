{
    "name": "Desklog Employee Tracking",
    "summary": "Employee activity tracking with screenshots (Ubuntu only)",
    "version": "18.0.1.0.0",
    "author": "Your Company",
    "category": "Productivity",
    "license": "LGPL-3",
    "depends": ["base", "web", "hr"],
    "data": [
        "security/desklog_security.xml",
        "security/ir.model.access.csv",
        "views/desklog_menus.xml",
        "views/desklog_views.xml",
        "data/desklog_cron.xml"
    ],
    "assets": {},
    "installable": True,
    "application": True
}
