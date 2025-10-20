# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from odoo import fields,models

class PosCreditDetails(models.TransientModel):
    _name = 'pos.credit.details'
    _description = 'Credit Details'

    date_start = fields.Date('Date Start', required=True,default = lambda *a: time.strftime('%Y-%m-%d') )
    date_end = fields.Date('Date End', required=True,default = lambda *a: time.strftime('%Y-%m-%d'))
    user_ids = fields.Many2many('res.users', 'pos_details_report_user_rel1', 'user_id', 'wizard_id', 'Salespeople')
    
    def print_report(self):
        if self._context is None:
            self._context = {}
        datas = {'ids': self._context.get('active_ids', [])}
        res = self.read(['date_start', 'date_end', 'user_ids'])
        res = res and res[0] or {}
        datas['form'] = res
        if res.get('id',False):
            datas['ids']=[res['id']]
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'pos.credit.details',
            'datas': datas,
        }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

