from odoo import api, fields, models, tools
from odoo.exceptions import ValidationError
import base64


class DesklogAgent(models.Model):
    _name = 'desklog.agent'
    _description = 'Desklog Agent'
    _rec_name = 'name'

    name = fields.Char(required=True)
    user_id = fields.Many2one('res.users', required=True, ondelete='cascade', string='User')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    system = fields.Selection([('linux', 'Linux'), ('windows', 'Windows')], required=True)
    hostname = fields.Char()
    last_seen = fields.Datetime(readonly=True)
    is_active = fields.Boolean(default=True)
    secret_token = fields.Char(readonly=True, copy=False)

    _sql_constraints = [
        ('user_unique', 'unique(user_id)', 'Each user can have only one agent.'),
    ]

    @api.model
    def create(self, vals):
        if not vals.get('secret_token'):
            vals['secret_token'] = tools.generate_random_password(length=40)
        return super().create(vals)


class DesklogActivity(models.Model):
    _name = 'desklog.activity'
    _description = 'Desklog Activity Log'
    _order = 'timestamp desc'

    agent_id = fields.Many2one('desklog.agent', required=True, ondelete='cascade')
    user_id = fields.Many2one(related='agent_id.user_id', store=True)
    employee_id = fields.Many2one(related='agent_id.employee_id', store=True)
    timestamp = fields.Datetime(required=True, default=fields.Datetime.now)
    app_name = fields.Char()
    window_title = fields.Char()
    idle_seconds = fields.Integer()
    activity_type = fields.Selection([
        ('active', 'Active'),
        ('idle', 'Idle'),
        ('locked', 'Locked'),
    ], default='active', required=True)


class DesklogScreenshot(models.Model):
    _name = 'desklog.screenshot'
    _description = 'Desklog Screenshot'
    _order = 'captured_at desc'

    agent_id = fields.Many2one('desklog.agent', required=True, ondelete='cascade')
    captured_at = fields.Datetime(required=True, default=fields.Datetime.now)
    image = fields.Binary(attachment=True, required=True)
    image_mime = fields.Selection([
        ('image/png', 'PNG'),
        ('image/jpeg', 'JPEG'),
    ], default='image/png', required=True)
    width = fields.Integer()
    height = fields.Integer()

    @api.model
    def _cron_cleanup(self):
        params = self.env['ir.config_parameter'].sudo()
        retain_days = int(params.get_param('desklog.retain_days', 30))
        if retain_days <= 0:
            return
        # delete older than retain_days
        cutoff = fields.Datetime.subtract(fields.Datetime.now(), days=retain_days)
        old = self.search([('captured_at', '<', cutoff)])
        old.unlink()


class DesklogSettings(models.TransientModel):
    _name = 'desklog.settings'
    _inherit = 'res.config.settings'

    screenshot_interval = fields.Integer(default=300, string='Screenshot Interval (sec)')
    screenshot_quality = fields.Integer(default=80, string='JPEG Quality (1-100)')
    retain_days = fields.Integer(default=30, string='Retention (days)')
    idle_threshold = fields.Integer(default=300, string='Idle Threshold (sec)')

    def set_values(self):
        res = super().set_values()
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('desklog.screenshot_interval', self.screenshot_interval)
        params.set_param('desklog.screenshot_quality', self.screenshot_quality)
        params.set_param('desklog.retain_days', self.retain_days)
        params.set_param('desklog.idle_threshold', self.idle_threshold)
        return res

    @api.model
    def get_values(self):
        res = super().get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(
            screenshot_interval=int(params.get_param('desklog.screenshot_interval', 300)),
            screenshot_quality=int(params.get_param('desklog.screenshot_quality', 80)),
            retain_days=int(params.get_param('desklog.retain_days', 30)),
            idle_threshold=int(params.get_param('desklog.idle_threshold', 300)),
        )
        return res
