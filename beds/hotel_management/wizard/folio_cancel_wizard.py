from odoo import fields, models, api
import time
# from mx import DateTime
import datetime


class cancel_foilo_wizard(models.TransientModel):
    _name = 'cancel.foilo.wizard'

    _description = 'Cancel Wizard'

    desc = fields.Text('Description', readonly=True)

    def default_get(self, fields):
        if self._context is None:
            self._context = {}
        res = {}
        move_ids = self._context.get('active_ids')
        if not move_ids or not self._context.get('active_model') == 'hotel.folio':
            return res
        move_ids = self.env['hotel.folio'].browse(move_ids)
        today = time.strftime('%Y-%m-%d %H:%M:%S')
        if today > move_ids[0].checkin_date:
            desc = "Checkin time is Passed still want to cancel this folio."
        else:
            desc = "Do You want to continue ?"
        if 'desc' in fields:
            res.update(desc=desc)
        return res


    def cancel_wizard(self):
        return {'type': 'ir.actions.act_window_close'}

