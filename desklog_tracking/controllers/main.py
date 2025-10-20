from odoo import http, fields
from odoo.http import request
from datetime import datetime
import base64
import json


def _get_agent_by_token(token):
    if not token:
        return None
    return request.env['desklog.agent'].sudo().search([('secret_token', '=', token), ('is_active', '=', True)], limit=1)


class DesklogController(http.Controller):

    @http.route(['/desklog/register'], type='json', auth='user', methods=['POST'])
    def register(self, system, hostname):
        user = request.env.user
        agent = request.env['desklog.agent'].sudo().search([('user_id', '=', user.id)], limit=1)
        vals = {
            'name': f"{user.name} - {hostname}",
            'user_id': user.id,
            'system': system,
            'hostname': hostname,
            'last_seen': fields.Datetime.now(),
            'is_active': True,
        }
        if agent:
            agent.write(vals)
        else:
            agent = request.env['desklog.agent'].sudo().create(vals)
        return {'token': agent.secret_token}

    @http.route(['/desklog/ping'], type='json', auth='none', methods=['POST'])
    def ping(self, token):
        agent = _get_agent_by_token(token)
        if not agent:
            return {'status': 'error', 'message': 'Invalid token'}
        agent.sudo().write({'last_seen': fields.Datetime.now()})
        return {'status': 'ok'}

    @http.route(['/desklog/activity'], type='json', auth='none', methods=['POST'])
    def activity(self, token, entries):
        agent = _get_agent_by_token(token)
        if not agent:
            return {'status': 'error', 'message': 'Invalid token'}
        Activity = request.env['desklog.activity'].sudo()
        for entry in entries:
            Activity.create({
                'agent_id': agent.id,
                'timestamp': entry.get('timestamp') or datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                'app_name': entry.get('app_name'),
                'window_title': entry.get('window_title'),
                'idle_seconds': entry.get('idle_seconds', 0),
                'activity_type': entry.get('activity_type', 'active'),
            })
        agent.write({'last_seen': fields.Datetime.now()})
        return {'status': 'ok'}

    @http.route(['/desklog/screenshot'], type='http', auth='none', methods=['POST'], csrf=False)
    def screenshot(self, **kwargs):
        token = kwargs.get('token')
        agent = _get_agent_by_token(token)
        if not agent:
            return request.make_json_response({'status': 'error', 'message': 'Invalid token'}, status=401)

        image_file = request.httprequest.files.get('image')
        mime = image_file.mimetype if image_file else kwargs.get('mime') or 'image/png'
        width = int(kwargs.get('width') or 0)
        height = int(kwargs.get('height') or 0)

        if not image_file:
            return request.make_json_response({'status': 'error', 'message': 'No image'}, status=400)

        image_b64 = base64.b64encode(image_file.read())
        request.env['desklog.screenshot'].sudo().create({
            'agent_id': agent.id,
            'image': image_b64,
            'image_mime': mime,
            'width': width,
            'height': height,
        })
        agent.sudo().write({'last_seen': fields.Datetime.now()})
        return request.make_json_response({'status': 'ok'})

    @http.route(['/desklog/config'], type='json', auth='none', methods=['POST'])
    def config(self, token):
        agent = _get_agent_by_token(token)
        if not agent:
            return {'status': 'error', 'message': 'Invalid token'}
        ICP = request.env['ir.config_parameter'].sudo()
        return {
            'status': 'ok',
            'screenshot_interval': int(ICP.get_param('desklog.screenshot_interval', 300)),
            'screenshot_quality': int(ICP.get_param('desklog.screenshot_quality', 80)),
            'retain_days': int(ICP.get_param('desklog.retain_days', 30)),
            'idle_threshold': int(ICP.get_param('desklog.idle_threshold', 300)),
        }
