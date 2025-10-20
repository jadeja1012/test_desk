# -*- encoding: utf-8 -*-


from odoo import api, fields, models
from odoo.exceptions import UserError
import datetime
import time
from datetime import datetime


class product_category(models.Model):
    _inherit = "product.category"
    isactivitytype = fields.Boolean('Is Activity Type')


class hotel_housekeeping_activity_type(models.Model):
    _name = 'hotel.housekeeping.activity.type'
    _description = 'Activity Type'
    _inherits = {'product.category': 'activity_id'}

    activity_id = fields.Many2one(
        'product.category', 'category', required=True, ondelete="cascade")
    isactivitytype = fields.Boolean('Is Activity Type', default=True)


class product_product(models.Model):
    _inherit = "product.product"
    isact = fields.Boolean('Is Activity')


class h_activity(models.Model):

    _name = 'h.activity'
    _inherits = {'product.product': 'h_id'}

    _description = 'Housekeeping Activity'

    h_id = fields.Many2one(
        'product.product', 'Product_id', required=True, ondelete="cascade")
    isact = fields.Boolean(
        'Is Activity', related='h_id.isact', inherited=True, default=True)

    def action_compute_bom_days(self):
        return True


    @api.onchange('type')
    def onchange_type(self):
        res = {}
        if self.type in ('consu', 'service'):
            res = {'value': {'valuation': 'manual_periodic'}}
        return res


class hotel_housekeeping(models.Model):
    _name = "hotel.housekeeping"
    _description = "Reservation"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    current_date = fields.Datetime("Start Date", required=True, default=lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),tracking=True)
    end_date = fields.Datetime("Expected End Date", required=True,tracking=True)
    clean_type = fields.Selection([('daily', 'Daily'), ('checkin', 'Checkin'), ('checkout', 'Checkout')], 'Clean Type', required=True,tracking=True)
    room_no = fields.Many2one('hotel.room', 'Room No', required=True,tracking=True)
    activity_lines = fields.One2many('hotel.housekeeping.activities', 'a_list', 'Activities housekeeping')
    room_no = fields.Many2one('product.product', 'Room No', required=True,tracking=True)
    inspector = fields.Many2one('res.users', 'Inspector', required=True,tracking=True)
    inspect_date_time = fields.Datetime('Inspect Date Time', required=True,tracking=True)
    quality = fields.Selection([('clean', 'Cleaning'), ('maintenance', 'Maintenance')], 'Housekeeping Type', required=True,tracking=True)
    state = fields.Selection([('dirty', 'Dirty'), ('clean', 'Clean'), ('inspect', 'Inspect'), ('done', 'Done'), (
        'cancel', 'Cancelled')], 'state', default="dirty", index=True, required=True, readonly=True,tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id,tracking=True)

    @api.model
    def room_inspector(self, partnerId):
        room_browse = self.env['hotel.housekeeping'].browse(partnerId)
        inspector = room_browse.inspector.name
        return inspector

    @api.onchange('current_date', 'end_date')
    def onchange_current_date(self):
        if self.end_date and self.current_date > self.end_date:
            raise UserError('End date must be greater than Start Date')

    def action_set_to_dirty(self):
        self.write({'state': 'dirty'})
        return True

    def room_cancel(self):
        self.write({'state': 'cancel'})
        return True

    def room_done(self):
        now = datetime.now()
        self.write({'state': 'done','end_date':now,'inspect_date_time':now})
        return True

    def room_inspect(self):
        self.write({'state': 'inspect'})
        return True

    def room_clean(self):
        self.write({'state': 'clean'})
        return True


class hotel_housekeeping_activities(models.Model):
    _name = "hotel.housekeeping.activities"
    _description = "Housekeeping Activities "
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    a_list = fields.Many2one('hotel.housekeeping',tracking=True)
    activity_name = fields.Many2one('h.activity', 'Housekeeping Activity',tracking=True)
    housekeeper = fields.Many2one('res.users', 'Housekeeper', required=True,tracking=True)
    clean_start_time = fields.Datetime('Clean Start Time', required=True,tracking=True)
    clean_end_time = fields.Datetime('Clean End Time', required=True,tracking=True)
    dirty = fields.Boolean('Dirty',tracking=True)
    clean = fields.Boolean('Clean',tracking=True)
    activity_id = fields.Many2one('activity.housekeeping', 'Housekeeping activity', required=True)


class activity_type(models.Model):
    _name = 'activity.type'
    _description = 'Activity Type'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char('Name', required=True)
    parent_id = fields.Many2one('activity.type', 'Parent Category',tracking=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 domain="[('id', 'in', [current_company_id])]",
                                 required=True,tracking=True)


class activity_housekeeping(models.Model):
    _name = 'activity.housekeeping'
    _description = 'Activity'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char('Name', required=True)
    categ_id = fields.Many2one('activity.type', 'Category',domain="[('company_id', 'in', [current_company_id])]", required=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 domain="[('id', 'in', [current_company_id])]")


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
