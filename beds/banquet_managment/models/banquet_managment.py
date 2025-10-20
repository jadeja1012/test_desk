from email.policy import default
import re
from odoo import fields, models, api
import time
import datetime
from datetime import datetime, timedelta
from odoo.tools import config
from odoo.addons import decimal_precision as dp
from odoo.tools.translate import _
# from dateutil import relativedelta
import calendar
from odoo import exceptions, _
# from odoo.exceptions import except_orm, UserError
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from dateutil.parser import *
import pytz
import math
import logging

_logger = logging.getLogger(__name__)


def get_price(self, pricelist_ids, price):
    price_amt = 0.0
    pricelist_item_ids = []
    if self._context is None:
        self._context = {}

    date = time.strftime('%Y-%m-%d')
    if 'date' in self._context:
        date = self._context['date']

    currency_obj = self.env['res.currency']
    product_pricelist_version_obj = self.env['product.pricelist.item']
    user_browse = self.env['res.users'].browse()
    company_obj = self.env['res.company']
    company_id = company_obj.browse(user_browse.company_id.id)
    pricelist_obj = self.env['product.pricelist'].browse(pricelist_ids)
    if pricelist_ids:
        pricelist_item_ids.append(pricelist_ids)
        pricelist_obj = self.env['product.pricelist'].browse(pricelist_ids)

    pricelist_item_ids = list(set(pricelist_item_ids))
    plversions_search_args = [
        ('pricelist_id', 'in', pricelist_item_ids),
        '|',
        ('date_start', '=', False),
        ('date_start', '<=', date),
        '|',
        ('date_end', '=', False),
        ('date_end', '>=', date),
    ]

    plversion_ids = product_pricelist_version_obj.search(
        plversions_search_args)

    if not plversion_ids:
        msg = "At least one pricelist item has not declared !\nPlease create pricelist item."
        raise exceptions.UserError(_('Warning !'+ msg))

    self._cr.execute(
        'SELECT i.* '
        'FROM product_pricelist_item AS i '
        'WHERE id = ' + str(plversion_ids[0].id) + '')

    res1 = self._cr.dictfetchall()
    if pricelist_obj:
        price = currency_obj._convert(price, pricelist_obj.currency_id, round)
    for res in res1:
        if res:
            price_limit = price
            x = (1.0 + (res['price_discount'] or 0.0))
            price = price * (1.0 + (res['price_discount'] or 0.0))
            price += (res['price_surcharge'] or 0.0)
            if res['price_min_margin']:
                price = max(price, price_limit + res['price_min_margin'])
            if res['price_max_margin']:
                price = min(price, price_limit + res['price_max_margin'])
            break

    price_amt = price
    return price_amt


class CrmLead2OpportunityPartner(models.TransientModel):
    _inherit = 'crm.lead2opportunity.partner'
    _description = 'Lead To Opportunity Partner'

    @api.model_create_multi
    def create(self, vals):
        for rec in vals:
            rec.update({'lead_id': self._context.get('active_id')})
        res = super(CrmLead2OpportunityPartner, self).create(vals)
        return res

    @api.model
    def default_get(self, fields):
        res = {}
        if 'action' in fields:
            res.update({'action': 'create'})
        if 'name' in fields:
            res.update({'name': 'convert'})
        result = super(CrmLead2OpportunityPartner, self).default_get(fields)
        if not result.get('lead_id') and self.env.context.get('active_id'):
            result['lead_id'] = self.env.context.get('active_id')
        return res

    def action_apply(self):
        ctx = dict(self._context)

        if 'banquet_id' in self._context:
            banq_browse = self.env['banquet.quotation'].browse(
                self._context['banquet_id'])

            ctx['active_id'] = banq_browse.lead.id
            ctx['active_ids'] = [banq_browse.lead.id]

        lead = self.env['crm.lead'].search([('id', '=', ctx['active_id'])])
        lead_ids = ctx['active_ids']
        if lead:
            lead.convert_opportunity(self.partner_id.id)
        res = super(CrmLead2OpportunityPartner, self).action_apply()
        return res


class CrmLead(models.Model):
    _name = 'crm.lead'
    _inherit = 'crm.lead'
    _description = 'User Modification'

    via = fields.Selection(
        [('direct', 'Direct'), ('agent', 'Agent')], 'Via', default=lambda *a: 'direct')
    agent_id = fields.Many2one('res.partner', 'Agent')
    lead_sequence = fields.Char('Lead Number', readonly=True)
    banquets_ids = fields.One2many(
        'banquet.quotation.lead.history', 'ref_id', 'Banquet Quotation History')
    shop_id = fields.Many2one('sale.shop', 'Hotel', required=True,
                              help="Will show only open leads for the selected shop.")

    def name_get(self):
        if not len(self._ids):
            return []
        res = [(r['id'], r['lead_sequence'])
               for r in self.read(fields=['lead_sequence'])]
        return res

    @api.model_create_multi
    def create(self, vals):
        req_no = self.env['ir.sequence'].next_by_code('crm.lead') or 'New'
        for rec in vals:
            rec['lead_sequence'] = req_no
        return super(CrmLead, self).create(vals)

    def unlink(self):
        for rec in self.browse():
            raise exceptions.UserError(
                _('Invalid action! Cannot delete these Lead.!'))
        return super(CrmLead, self).unlink()

    @api.onchange('shop_id')
    def on_change_shop_id(self):
        if not self.shop_id:
            return {'value': {}}
        temp = self.env['sale.shop'].browse(self.shop_id.id)
        return {'value': {'company_id': temp.company_id.id}}


class DepositPaymentPolicy(models.Model):
    _name = "deposit.payment.policy"
    _description = "Deposit Payment Policy"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    start_date = fields.Date("From Date", required=True,tracking=True)
    name = fields.Char('Policy Name', required=True,tracking=True)
    percentage = fields.Float("Percentage", required=True,tracking=True)
    min_amount = fields.Float("Minimum Deposit Amount", required=True,tracking=True)
    shop_id = fields.Many2one('sale.shop', 'Hotel', required=True,
                              help="Will show list of shop that belongs to allowed companies of logged-in user. \n -Assign a shop to configure shop-wise deposit  policy.")
    company_id = fields.Many2one(
        related='shop_id.company_id', string='Company', store=True)


class ThemePlan(models.Model):
    _name = "theme.plan"
    _description = "Theme Plan"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char('Theme Name', required=True,tracking=True)
    code = fields.Char('Code',tracking=True )



class SeatingPlan(models.Model):
    _name = "seating.plan"
    _description = "Seating Plan"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char('Name', required=True,tracking=True)
    code = fields.Char('Code',tracking=True)


class BanquetQuotation(models.Model):
    _name = "banquet.quotation"
    _description = "Banquet Quotation"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    def unlink(self):
        for rec in self.browse():
            raise exceptions.UserError(_('Invalid action! Cannot delete these Quotation.!'))
        return super(BanquetQuotation, self).unlink()

    @api.onchange('pricelist_id')
    @api.depends('room_ids', 'food_items_ids', 'other_items_ids')
    def onchange_pricelist_id(self):
    
        if not self.pricelist_id:
            return {}
        temp = 0
        if self.pricelist_id:
            if not self.room_ids == [(6, 0, [])] and len(self.room_ids) != 1:
                temp = 1
            if not self.food_items_ids == [(6, 0, [])] and len(self.food_items_ids) != 1:
                temp = 1
            if not self.other_items_ids == [(6, 0, [])] and len(self.other_items_ids) != 1:
                temp = 1
        if temp == 0:
            return {}
            
    @api.onchange('lead')
    @api.depends('lead')
    def onchange_lead_id(self):
        if self.lead:
            self.contact_name = self.lead.partner_id.id


    @api.model_create_multi
    def create(self, vals):
        # function overwrites create method and auto generate request no.
        req_no = self.env['ir.sequence'].next_by_code(
            'banquet.quotation') or 'New'
        for rec in vals:
            rec['name'] = req_no
        return super(BanquetQuotation, self).create(vals)

    def _get_total_amt_pur(self):
        res = {}
        for obj in self:
            obj.pur_total_amt = obj.pur_untax_amt + obj.pur_tax_amt

    def _amount_line_tax_pur(self, line):
        val = 0.0
        taxes = line.pur_tax_ids.compute_all(
            line.cost_price_unit * (1 - (line.discount or 0.0) / 100.0), line.currency_id, 1)
        val = taxes['total_included'] - taxes['total_excluded']
        return val

    def _amount_line_tax_pur_food_other(self, line):
        val = 0.0
        user_id = self.env['res.users'].search([('id', '=', self._context.get('uid'))])
        taxes = line.pur_tax_ids.compute_all(
            line.cost_price_unit * (1 - (line.discount or 0.0) / 100.0), user_id.company_id.currency_id, 1)
        val = taxes['total_included'] - taxes['total_excluded']
        return val

    def _get_tax_amt_pur(self):
        res = {}
        total = 0.00
        val = 0.00
        cur_obj = self.env['res.currency']
        res_user = self.env['res.users']
        for obj in self:
            user_id = res_user.browse()
            cur = user_id.company_id.currency_id
            for line in obj.room_ids:
                val += self._amount_line_tax_pur(line)
            for line in obj.food_items_ids:
                val += self._amount_line_tax_pur_food_other(line)
            for line in obj.other_items_ids:
                val += self._amount_line_tax_pur_food_other(line)
            obj.update({
                'pur_tax_amt': val,
            })


    def _get_untax_amt_pur(self):
        res = {}
        total = 0.00
        for obj in self:
            for service in obj.room_ids:
                total += service.cost_price_subtotal
            for food in obj.food_items_ids:
                total += food.cost_price_subtotal
            for other in obj.other_items_ids:
                total += other.cost_price_subtotal
            obj.pur_untax_amt = total


    def _get_total_amt_sale(self):
        res = {}
        for obj in self:
            obj.sale_total_amt = obj.sale_untax_amt + obj.sale_tax_amt

    
    def _amount_line_tax(self, line):
        val = 0.0
        line.company_id = self.env['res.users'].search([('id', '=', self._context.get('uid'))]).company_id
        line.currency_id = line.company_id.currency_id

        taxes = line.taxes_id.compute_all(
            line.price * (1 - (line.discount or 0.0) / 100.0), line.currency_id, line.number_of_days)
        val = taxes['total_included'] - taxes['total_excluded']
        return val

    def _amount_food_tax(self, line):
        val = 0.0
        taxes = line.tax_id.compute_all(
            line.price_subtotal * (1 - (line.discount or 0.0) / 100.0), None, 1)
        val = taxes['total_included'] - taxes['total_excluded']
        return val

  
    def _amount_other_tax(self, line):
        val = 0.0
        taxes = line.tax_id.compute_all(
            line.price_subtotal * (1 - (line.discount or 0.0) / 100.0), None, 1)
        val = taxes['total_included'] - taxes['total_excluded']
        return val

    def _get_tax_amt_sale(self):
        res = {}
        val = 0.00
        cur_obj = self.env['res.currency']
        res_user = self.env['res.users']
        for obj in self:
            user_id = res_user.browse()
            cur = user_id.company_id.currency_id
            for line in obj.room_ids:
                val += self._amount_line_tax(line)
            for line in obj.food_items_ids:
                val += self._amount_food_tax(line)
            for line in obj.other_items_ids:
                val += self._amount_other_tax(line)
            #             res[obj.id] = cur_obj.round(val)
            obj.update({
                'sale_tax_amt': val,
            })

    

    def _get_untax_amt_sale(self):
        res = {}
        total = 0.00
        for obj in self:
            for service in obj.room_ids:
                total += service.sub_total1
            for food in obj.food_items_ids:
                total += food.price_subtotal
            for other in obj.other_items_ids:
                total += other.price_subtotal
            obj.update({
                'sale_untax_amt': total,
            })

   
    @api.depends('room_ids')
    def count_total_rooms(self):
        res = {}
        for obj in self:
            count1 = 0
            for line in obj.room_ids:
                count1 += 1
        self.number_of_rooms = count1

    def count_total_days(self):
        current_date = datetime.today().date()
        date_object = (self.checkout, '%Y-%m-%d %H:%M:%S')

        if current_date != date_object:
            if self.in_date >= self.out_date:
                checkout = self.in_date
                checkout += timedelta(days=1)
                self.out_date = checkout

        ch_in = self.in_date
        ch_out = self.out_date
        check_in = self.in_date
        check_out = self.out_date

        day_count1 = (check_out - check_in).days
        if day_count1 == 0:
            day_count1 = 1

        day_count1 = round(day_count1)
        self.number_of_days = day_count1

    @api.model
    def _get_default_shop(self):
        user = self.env['res.users'].browse(self._uid)
        company_id = user.company_id.id
        shop_ids = self.env['sale.shop'].search(
            [('company_id', '=', company_id)])
        if not shop_ids:
            raise exceptions.UserError(_('Error! There is no default shop for the current user\'s company!'))
        return shop_ids[0]

    @api.onchange('shop_id')
    def onchange_shop_id(self):
        v = {}
        if self.shop_id:
            shop = self.env['sale.shop'].browse(self.shop_id.id)
            if shop.pricelist_id:
                v['pricelist_id'] = shop.pricelist_id.id
        return {'value': v}

    name = fields.Char("Quotation No.", readonly=True,tracking=True)
    current_date = fields.Date("Enquiry Date", required=True, readonly=True, default=time.strftime('%Y-%m-%d'),tracking=True)
    lead = fields.Many2one('crm.lead', 'Lead', readonly=True,tracking=True)
    contact_name = fields.Many2one('res.partner','Contact Name',required=True, readonly=True,tracking=True)
    address = fields.Char('Address', readonly=True)
    email_id = fields.Char('Email Id', readonly=True,tracking=True)
    #                'tour_name':fields.char('Banquet Name',  readonly=True, states={'draft': [('readonly', False)]},),
    mobile = fields.Char('Mobile Number', required=True, readonly=True)
    adult = fields.Integer("Adult Persons", readonly=True,tracking=True)
    child = fields.Integer("Child", readonly=True,tracking=True)
    in_date = fields.Datetime("Prefer Start Date",tracking=True)
    out_date = fields.Datetime("Prefer End Date",tracking=True)
    via = fields.Selection([('direct', 'Direct'), ('agent', 'Agent')], "Via", readonly=True, default='direct')
    agent_id = fields.Many2one('res.partner', 'Agent', readonly=True)
    room_ids = fields.One2many('hotel.reservation.line', 'banquet_id',
                               'Room Details', readonly=True)
    food_items_ids = fields.One2many('food.items', 'banquet_id', 'Food Items')
    other_items_ids = fields.One2many(
        'other.items', 'banquet_id', 'Other Items')
    number_of_days = fields.Integer(compute='count_total_days', string="Number Of Days",
                                    default=1,
                                    help="Shall be computed based on check out policy configured for selected shop.")
    number_of_rooms = fields.Integer(
        compute='count_total_rooms', string="Number Of Rooms")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('send_to', 'Sent To Customer'),
        ('approve', 'Approved'),
        ('done', 'Done'),
        ('refused', 'Refused'),
    ], 'Status', default='draft',tracking=True)  # ,readonly=True),

    theme_id = fields.Many2one('theme.plan', 'Theme', required=True, readonly=True)
    board_toread = fields.Char("Board to Read", readonly=True)
    seating_id = fields.Many2one('seating.plan', 'Seating Plan', required=True, readonly=True)
    sale_untax_amt = fields.Float(
        compute='_get_untax_amt_sale', string="Sale Untaxed Amount")
    sale_tax_amt = fields.Float(
        compute='_get_tax_amt_sale', string="Sale Taxes ")
    pur_untax_amt = fields.Float(
        compute='_get_untax_amt_pur', string="Purchase Untaxed Amount")
    pur_tax_amt = fields.Float(
        compute='_get_tax_amt_pur', string="Purchase Taxes ")
    sale_total_amt = fields.Float(
        compute='_get_total_amt_sale', string="Sale Total Amount")
    pur_total_amt = fields.Float(
        compute='_get_total_amt_pur', string="Purchase Total Amount")
    deposit_policy = fields.Selection([('percentage', 'Deposit Percentage'), ('no_deposit', 'No Deposit')],
                                      'Deposit Policy', required=True, readonly=True, default='no_deposit')
    percentage = fields.Float("Percentage/Deposit Amount", readonly=True)
    min_dep_amount = fields.Float("Minimum Deposit Amount", readonly=True)
    invoiced = fields.Boolean('Invoiced', default=False)
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', required=True, readonly=True)
    shop_id = fields.Many2one('sale.shop', 'Hotel', domain="[('company_id', '=', [current_company_id])]",
                              required=True, readonly=True, default=_get_default_shop,
                              help="Will show list of shop that belongs to allowed companies of logged-in user.")
    company_id = fields.Many2one(
        related='shop_id.company_id', string='Company', store=True)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,default=lambda self: self.env.user.company_id.currency_id.id)

    new_currency_id = fields.Many2one('res.currency', string='Currency Test')

    def update_prices(self):
        self.ensure_one()
        self.currency_id = self.pricelist_id.currency_id.id
        #self._compute_amounts()
        pricelist_amount = self.pricelist_id.currency_id.rate
        self.new_currency_id = self.pricelist_id.currency_id.id
        for line in self.room_ids:
            pricelist_rule = line.pricelist_item_id
            order_date = self.in_date or fields.Date.today()
            product = line.room_number
            qty = line.number_of_days or 1.0
            uom = line.room_number.uom_id
            pricev = pricelist_rule._compute_price(product, qty, uom, order_date, currency=self.new_currency_id)
            line.update({
                'price': pricev,
            })

  
    @api.onchange('shop_id', 'in_date', 'out_date')
    def on_change_checkout(self):
        val = {}
        if not self.shop_id:
            raise UserError('Shop is not selected.')

        if not self.out_date:
            self.out_date = time.strftime('%Y-%m-%d %H:%M:%S')
        if self.in_date and self.shop_id.id:
            new_date = str(self.in_date)
            self._cr.execute(
                'select max(start_date) from deposit_payment_policy where start_date <= %s and shop_id = %s',
                (new_date, self.shop_id.id,))
            a = self._cr.fetchone()
            pay_obj = self.env['deposit.payment.policy'].search(
                [('start_date', '=', a[0])])
            val = {'value': {
                'percentage': pay_obj.percentage, 'min_dep_amount': pay_obj.min_amount}}
        return val

    def compute(self):
        res = {}
        total = 0.00
        val = 0.00
        pur_total = 0.00
        pur_val = 0.00
        user_id = self.env['res.users'].search([('id', '=', self._context.get('uid'))])
        cur_obj = user_id.company_id.currency_id
        res_user = self.env['res.users']
        for obj in self:
            user_id = res_user.browse()
            cur = user_id.company_id.currency_id
            for line in obj.room_ids:
                line.sub_total1 = line.price
                total += line.sub_total1
                val += self._amount_line_tax(line)
                pur_total += line.cost_price_subtotal
                pur_val += self._amount_line_tax_pur(line)

            for line in obj.food_items_ids:
                total += line.price_subtotal
                val += self._amount_food_tax(line)
                pur_total += line.cost_price_subtotal
                pur_val += self._amount_line_tax_pur_food_other(line)
            for line in obj.other_items_ids:
                total += line.price_subtotal
                val += self._amount_other_tax(line)
                pur_total += line.cost_price_subtotal
                pur_val += self._amount_line_tax_pur_food_other(line)
            res[obj.id] = cur_obj.round(val)
        sum = total + val
        pur_sum = pur_total + pur_val
        self.write({'sale_tax_amt': val, 'sale_total_amt': sum, 'sale_untax_amt': total,
                    'pur_tax_amt': pur_val, 'pur_total_amt': pur_sum, 'pur_untax_amt': pur_total
                    })
        return True

    def action_confirm(self):

        for obj in self:
            if not obj.room_ids:
                raise exceptions.UserError(_("Warning! Room Details are missing."))
            for room in obj.room_ids:
                room_line_id = self.env['hotel.room'].search(
                    [('product_id', '=', room.room_number.id)])
                room_line_browse = self.env['hotel.room'].browse(
                    room_line_id.id)
                if room_line_browse.room_folio_ids:
                    for history in room_line_browse.room_folio_ids:
                        if history.state == 'done':
                            history_start_date = history.check_in
                            history_end_date = history.check_out
                            reservation_start_date = obj.in_date
                            reservation_end_date = obj.out_date
                            if (history_start_date <= reservation_start_date < history_end_date) or (
                                    history_start_date < reservation_end_date <= history_end_date) or (
                                    (reservation_start_date < history_start_date) and (
                                    reservation_end_date > history_end_date)):
                                if not (obj == history.booking_id):
                                    raise exceptions.UserError(_("Warning1! You tried to confirm reservation with room  %s which is already reserved in this reservation period !") % (room.room_number.name))

        self.write({'state': 'confirm'})
        return True

    def action_approve(self):
        for obj in self:
            data_obj = self.env['ir.model.data']
            data_id = data_obj._xmlid_to_res_id(
                'crm.view_crm_lead2opportunity_partner')

            view_id1 = False
            if self._context is None:
                self._context = {}
            ctx = dict(self._context)
            ctx['active_ids'] = [obj.id]
            ctx['banquet_id'] = obj.id

            if data_id:
                view_id1 = data_id

            id_lead = self.env['crm.lead'].browse(obj.lead.id)
            rejected_history_id = self.env['banquet.quotation.lead.history'].search(
                [('ref_id', '=', id_lead.id)])
            if rejected_history_id:
                for id in rejected_history_id:
                    self.env['banquet.quotation.lead.history'].write(
                        {'state': 'refused', 'update_date': time.strftime('%Y-%m-%d')})
            history_id = self.env['banquet.quotation.lead.history'].search(
                [('name', '=', obj.name), ('ref_id', '=', id_lead.id)])
            if history_id:
                self.env['banquet.quotation.lead.history'].write(
                    {'state': 'approve', 'update_date': time.strftime('%Y-%m-%d')})

            rejected_itinary = self.search([('lead', '=', id_lead.id)])
            if rejected_itinary:
                for rec in rejected_itinary:
                    rec.write({'state': 'refused'})
            obj.write({'state': 'approve'})

    def action_refuse(self):
        for obj in self:
            id_lead = self.env['crm.lead'].browse(obj.lead.id)
            history_id = self.env['banquet.quotation.lead.history'].search(
                [('name', '=', obj.name), ('ref_id', '=', id_lead.id)])
            if history_id:
                self.env['banquet.quotation.lead.history'].write(
                    {'state': 'refused', 'update_date': time.strftime('%Y-%m-%d')})
            obj.write({'state': 'refused'})
        return True

    def action_sent(self):
        for obj in self:
            id_lead = self.env['crm.lead'].browse(obj.lead.id)
            itinarary_id = self.env['banquet.quotation.lead.history'].create({
                'name': obj.name,
                'contact_name': obj.contact_name,
                'state': 'send_to',
                #'ref_id': id_lead.id,
                'current_date': time.strftime('%Y-%m-%d'),
                'update_date': time.strftime('%Y-%m-%d'),
            })
            stage = self.env['crm.stage'].search(
                [('name', '=', 'Proposition')])
            if stage:
                self.env['crm.lead'].write({'stage_id': stage.id})
            obj.write({'state': 'send_to'})
        return True

    def action_create_tour(self):
        for obj in self:
            if not self.shop_id:
                raise exceptions.UserError(
                    'Configuration Error! Shop is not define.')
            shop_id = self.env['sale.shop'].browse(self.shop_id.id)
            if not obj.contact_name:
                raise UserError(_(
                    "Please convert the Lead '%s' in Opportunity first!") % (obj.lead.lead_sequence))
            banquet_id = self.env['hotel.reservation'].create({
                'shop_id': obj.shop_id.id,
                'pricelist_id': obj.pricelist_id.id,
                'banq_bool': True,
                'partner_id': obj.contact_name.id,
                'adults': obj.adult,
                'childs': obj.child,
                'deposit_policy': obj.deposit_policy,
                'percentage': obj.percentage,
                'min_dep_amount': obj.min_dep_amount,
                'banquet_id': obj.id,
                'via': obj.via,
                'agent_id': obj.agent_id.id,
                'source': 'internal_reservation',
                'food_type': True,
            })

            for room in obj.room_ids:
                tax_ids = []
                for tax_line in room.taxes_id:
                    tax_ids.append(tax_line.id)
                room_booking_id = self.env['hotel.reservation.line'].create({
                    'room_number': room.room_number.id,
                    'price': room.price,
                    'categ_id': room.categ_id.id,
                    'discount': room.discount,
                    'taxes_id': [(6, 0, tax_ids)],
                    'line_id': banquet_id.id,
                    'checkin': obj.in_date,
                    'checkout': obj.out_date,
                })
            for room in obj.food_items_ids:

                tax_ids = []
                for tax_line in room.tax_id:
                    tax_ids.append(tax_line.id)
                vv=self.env['food.items'].create({
                    'product_id': room.product_id.id,
                    'name': room.product_id.name,
                    'price_unit': room.price_unit,
                    'discount': room.discount,
                    'tax_id': [(6, 0, tax_ids)],
                    'food_items_id': banquet_id.id,
                    'product_uom': room.product_uom.id,
                    'product_uom_qty': room.product_uom_qty
                })
            for room in obj.other_items_ids:
                tax_ids = []
                for tax_line in room.tax_id:
                    tax_ids.append(tax_line.id)
                room_booking_id = self.env['other.items'].create({
                    'product_id': room.product_id.id,
                    'name': room.product_id.name,
                    'price_unit': room.price_unit,
                    'discount': room.discount,
                    'tax_id': [(6, 0, tax_ids)],
                    'other_items_id': banquet_id.id,
                    'product_uom': room.product_uom.id,
                    'product_uom_qty': room.product_uom_qty
                })
            tour_search = self.env['hotel.reservation'].search(
                [('id', '=', banquet_id.id)])
            custom_tour = self.env['hotel.reservation'].browse(tour_search.id)
            obj.write({'state': 'done'})
        return True


class HotelReservationLine(models.Model):
    _inherit = "hotel.reservation.line"
    _description = "Reservation Line"

    def count_total_days(self):
        res = {}
        for obj in self:

            if obj.company_id.id == self.env.user.company_id.id:

                policy_obj = self.env['checkout.configuration'].sudo().search([('shop_id', '=', obj.line_id.shop_id.id)])
                policy_browse = self.env['checkout.configuration'].sudo().browse(policy_obj.id)

                ch_in = obj.checkin

                ch_out = obj.checkout
                check_in = obj.checkin
                check_out = obj.checkout
                day_count1 = (check_out - check_in).days
                if not policy_browse.name == '24hour':
                    check_in = obj.checkin

                    check_out = obj.checkout
                    day_count1 = check_out - check_in

                    day_count2 = day_count1.total_seconds()

                    day_count2 = day_count2 / 86400
                    day_count2 = "{:.2f}".format(day_count2)
                    day_count2 = math.ceil(float(day_count2))

                    day_count1 = day_count2

                else:

                    day_count1 = check_out - check_in

                    day_count2 = day_count1.total_seconds()
                    day_count2 = day_count2 / 86400
                    day_count2 = "{:.2f}".format(day_count2)

                    day_count2 = math.ceil(float(day_count2))

                    day_count1 = day_count2
                obj.number_of_days = day_count1
            else:
                obj.number_of_days = 0

    

    @api.depends('number_of_days', 'discount', 'price', 'taxes_id', 'room_number')
    def count_price(self):
        tax_obj = self.env['account.tax']
        cur_obj = self.env['res.currency']
        res_user = self.env['res.users']
        res = {}
        if self._context is None:
            self._context = {}

        for line in self:
            
            if line.line_id:
                price = line.price * (1 - (line.discount or 0.0) / 100.0)
                
                taxes = line.taxes_id.compute_all(
                    price, None, line.number_of_days)
                val = taxes['total_excluded']
                cur = line.line_id.pricelist_id.currency_id
                if cur:
                    line.update({
                        'sub_total': cur.round(val),
                    })
            else:
                price = line.price * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.taxes_id.compute_all(
                    price, None, line.number_of_days)
                val = taxes['total_excluded']
                user_id = res_user.browse(self._uid)
                cur = user_id.company_id.currency_id
                line.update({
                    'sub_total': cur.round(val),
                })

    def _amount_line_cost(self):
        res_user = self.env['res.users']
        res = {}
        if self._context is None:
            context = {}
        for line in self:
            cur = 0
            if line.banquet_id:
                price = line.cost_price_unit
                taxes = line.pur_tax_ids.compute_all(
                    price, None, line.number_of_days)
                val = taxes['total_excluded']
                user_id = res_user.browse(self._uid)
                cur = user_id.company_id.currency_id
            line.update({
                'cost_price_subtotal': cur.round(val) if cur else 0,
            })

    @api.depends('checkin', 'checkout', 'number_of_days')
    @api.onchange('room_number')
    def onchange_room_id(self):


        if self.line_id:
            pricelist = self.line_id.pricelist_id.id
            parent_id = self.line_id
        if self.banquet_id:
            pricelist = self.banquet_id.pricelist_id.id
            parent_id = self.banquet_id
        room_id = self.room_number
        v = {}
        res_list = []
        warning = ''
        if self.banquet_id:
            if not pricelist:
                raise exceptions.UserError(
                    _("Warning! PriceList is not Selected !"))

            product_browse = room_id
            ctx = self._context and self._context.copy() or {}
            ctx.update({'date': self.checkin})

            tax_ids = []
            for tax_line in product_browse.taxes_id:
                tax_ids.append(tax_line.id)
            v['taxes_id'] = [(6, 0, tax_ids)]
            v['checkin'] = self.checkin
            v['checkout'] = self.checkout

            cost_price_unit = get_price(
                self, pricelist, product_browse.standard_price)
            v['cost_price_unit'] = cost_price_unit

            room_line_id = self.env['hotel.room'].search(
                [('product_id', '=', room_id.id)])
            room_line_browse = self.env['hotel.room'].browse(room_line_id.id)
            if room_line_browse.room_folio_ids:
                for history in room_line_browse.room_folio_ids:
                    if history.state == 'done':
                        history_start_date = history.check_in
                        history_end_date = history.check_out
                        reservation_start_date = self.checkin
                        reservation_end_date = self.checkout
                        #############################Added by Pornima############
                        housekeeping_room = self.env['hotel.housekeeping'].search(
                            [('room_no', '=', room_line_browse.product_id.id), ('state', '=', 'dirty')])
                        if housekeeping_room:
                            for house1 in housekeeping_room:
                                house = house1
                                house_current_date = (datetime.strptime(
                                    house.current_date, '%Y-%m-%d %H:%M:%S')).date()
                                house_end_date = (datetime.strptime(
                                    house.end_date, '%Y-%m-%d %H:%M:%S')).date()
                                start_reser = datetime.strptime(
                                    self.checkin, '%Y-%m-%d %H:%M:%S').date()
                                end_reser = datetime.strptime(
                                    self.checkout, '%Y-%m-%d %H:%M:%S').date()

                                if (house_current_date <= start_reser <= house_end_date) or (
                                        house_current_date <= end_reser <= house_end_date) or (
                                        (start_reser < house_current_date) and (end_reser > house_end_date)):

                                    raise exceptions.UserError(_("Warning! Room  %s is not clean for reservation period !") % (room_line_browse[0].name))

                        #############################Added by Pornima##########
                        if (history_start_date <= reservation_start_date < history_end_date) or (
                                history_start_date < reservation_end_date <= history_end_date) or (
                                (reservation_start_date < history_start_date) and (
                                reservation_end_date > history_end_date)):
                            if not (parent_id == history.booking_id.id):
                                raise exceptions.UserError(_("Warning! Room %s is booked in this reservation period !") % (room_line_browse[0].name))
        else:

            if self.line_id:
                if not self.line_id.pricelist_id:
                    raise UserError("PriceList is not Selected !")
                if self.room_number:
                    check_in = self.checkin
                    checkout = self.checkout
                    total_price = 0
                    if self.line_id.shop_id.dynamic_pricelist == True:
                        pricelist_items = self.env['product.pricelist.item'].search([
                       ('product_tmpl_id.product_variant_ids.id', '=', self.room_number.id),
                      ('date_start', '<=', checkout),('date_end', '>=', check_in),])
                        if pricelist_items:
                            current_day = check_in
                            while current_day < checkout:
                                matched = False
                        
                                for price_list in pricelist_items:
                                    if price_list.pricelist_id.id == self.line_id.pricelist_id.id:
                                        if price_list.date_start <= current_day <= price_list.date_end:

                                            price = re.sub(r'[^\d.]', '', price_list.price)
                                            price = price.replace(',', '')
                                            daily_price = float(price) 
                                            total_price += daily_price
                                            matched = True
                                            break
                                if not matched:
                                    raise UserError(f"Couldn't find a pricelist line matching the date: {current_day.strftime('%Y-%m-%d')}")
                                current_day += timedelta(days=1)
                                price = total_price              
            
                        else:
                            raise UserError("Couldn't find a pricelist line matching this Date")
                    product_browse = self.room_number
                    product_id = product_browse.id
                    if self.line_id.shop_id.dynamic_pricelist == False:
                        price = product_browse.lst_price

                    if price is False:
                        raise UserError(
                            "Couldn't find a pricelist line matching this product!1")

                    ctx = self._context and self._context.copy() or {}
                    ctx.update({'date': self.checkin})
                    check_in = self.checkin
                    checkout = self.checkout
                    total_price = 0.0
                    for i in range((checkout - check_in).days):
                        current_day = check_in + timedelta(days=i)
                        ctx = self._context.copy() if self._context else {}
                        ctx.update({'date': current_day})
                        price_per_day = self.env['product.pricelist'].with_context(ctx)._price_get(
                        room_id, self.number_of_days)[pricelist]
                        total_price += price_per_day
                    #price = self.env['product.pricelist'].with_context(ctx)._price_get(
                        #room_id, self.number_of_days)[pricelist]
                    v['price'] = price
                    tax_ids = []
                    for tax_line in product_browse.taxes_id:
                        tax_ids.append(tax_line.id)
                    v['taxes_id'] = [(6, 0, tax_ids)]
                    v['checkin'] = self.checkin
                    v['checkout'] = self.checkout

                    room_line_id = self.env['hotel.room'].search(
                        [('product_id', '=', product_id)])
                    housekeeping_room = self.env['hotel.housekeeping'].search(
                        [('room_no', '=', room_line_id.id), ('state', '=', 'dirty')])
                    if housekeeping_room:
                        for house1 in housekeeping_room:
                            house = house1
                            house_current_date = (datetime.strptime(
                                str(house.current_date), '%Y-%m-%d %H:%M:%S')).date()
                            house_end_date = (datetime.strptime(
                                str(house.end_date), '%Y-%m-%d %H:%M:%S')).date()
                            start_reser = datetime.strptime(
                                str(self.checkin), '%Y-%m-%d %H:%M:%S').date()
                            end_reser = datetime.strptime(
                                str(self.checkout), '%Y-%m-%d %H:%M:%S').date()
                            if (house_current_date <= start_reser <= house_end_date) or (
                                    house_current_date <= end_reser <= house_end_date) or (
                                    (start_reser < house_current_date) and (end_reser > house_end_date)):
                                raise UserError(
                                    "Room  %s is not clean for reservation period !" % (room_line_id.name))

                    ###################################################################

                    if room_line_id.room_folio_ids:
                        for history in room_line_id.room_folio_ids:
                            if history.state == 'done':
                                history_start_date = history.check_in
                                history_end_date = history.check_out
                                reservation_start_date = self.checkin
                                reservation_end_date = self.checkout
                                if (history_start_date <= reservation_start_date < history_end_date) or (
                                        history_start_date < reservation_end_date <= history_end_date) or (
                                        (reservation_start_date < history_start_date) and (
                                        reservation_end_date > history_end_date)):

                                    history_date_time = str(history_end_date)
                                    dth = datetime.strptime(history_date_time, "%Y-%m-%d %H:%M:%S")
                                    hour_minute_dt = dth.strftime("%H:%M")
                                    datetime_string = str(self.checkin)
                                    dt = datetime.strptime(datetime_string, "%Y-%m-%d %H:%M:%S")
                                    hour_minute = dt.strftime("%H:%M")
                                    if not (self.line_id.id == history.booking_id.id):
                                        raise UserError(
                                            "Room  %s is booked in this reservation period !" % (room_line_id.name,))

        return {'value': v, 'warning': warning}

    currency_id = fields.Many2one(
        'res.currency', store=True, string='Currency', readonly=True)
    banquet_id = fields.Many2one('banquet.quotation', 'Banquet Id')
    sub_total = fields.Float(compute='count_price', compute_sudo=False,
                             string="sub total")
    cost_price_unit = fields.Float('Cost Price', digits='Cost Price')
    cost_price_subtotal = fields.Float(
        compute='_amount_line_cost', string='Cost Subtotal', digits='Cost Price')
    pur_tax_ids = fields.Many2many(
        'account.tax', 'pur_hotel_line_tax_rel', 'hotel_line_id', 'tax_id', 'Purchase Taxes')
    purches_bol = fields.Boolean('Show Purchase Tax')
    number_of_days = fields.Integer(
        compute='count_total_days', string="Number Of Days", default=1)


    def get_price_new(text):
        num = re.search(r'[\d.,]+', text)
        if num:
            n = num.group()
            if ',' in n and '.' in n:
                n = n.replace('.', '').replace(',', '.')
            elif n.count(',') == 1 and n[-3] == ',':
                n = n.replace(',', '')
            elif ',' in n:
                n = n.replace(',', '.')
            return int(float(n))


class HotelReservation(models.Model):
    _inherit = "hotel.reservation"
    _description = "Reservation"

    food_type = fields.Boolean('Food',)
    food_items_ids_res = fields.One2many('food.items', 'food_items_id', 'Food Items Res')

    @api.onchange('deposit_policy')
    def onchange_deposit_policy(self):
        v = {}
        if self.deposit_policy == 'no_deposit':
            v['percentage'] = 0.0
        return {'value': v}

    @api.depends('reservation_line.price', 'reservation_line.discount')
    def _get_subtotal_amount(self):
        line_subtotal = super(HotelReservation, self)._get_subtotal_amount()
        total = 0.00
        tax_obj = self.env['account.tax']
        for obj in self:
            if obj.id:
                cur = obj.pricelist_id.currency_id
                for line in obj.reservation_line:
                    price = line.price * (1 - (line.discount or 0.0) / 100.0)
                    taxes = line.taxes_id.compute_all(
                        price,self.shop_id.company_id.currency_id, line.number_of_days)
                    cur = line.line_id.pricelist_id.currency_id
                    total += line.sub_total1
                for food in obj.food_items_ids:
                    total += food.price_subtotal
                for other in obj.other_items_ids:
                    total += other.price_subtotal
                obj.update({
                    'untaxed_amt': total,
                })
            else:
                 obj.update({
                    'untaxed_amt': 0,
                }) 


    @api.depends('reservation_line.price', 'reservation_line.discount')
    def _get_total_tax(self):
        res = {}
        total = 0.00
        val = 0.00
        total_val = 0.00
        tax_obj = self.env['account.tax']
        cur_obj = self.env['res.currency']
        for obj in self:
            if obj.id:
                cur = obj.pricelist_id.currency_id
                for line in obj.reservation_line:
                    val += self._amount_line_tax(line)
                for line in obj.food_items_ids:
                    total += line.price_subtotal
                    val += self._amount_food_tax(line)
                for line in obj.other_items_ids:
                    total += line.price_subtotal

                    val += self._amount_other_tax(line)
                obj.update({
                    'total_tax': cur.round(val),
                })
            else:
                 obj.update({
                    'total_tax': 0,
                }) 

    def _amount_other_tax(self, line):
        val = 0.0
        taxes = line.tax_id.compute_all(
            line.price_subtotal * (1 - (line.discount or 0.0) / 100.0), line.currency_id, 1)
        val = taxes['total_included'] - taxes['total_excluded']
        return val

    def _amount_food_tax(self, line):
        val = 0.0
        taxes = line.tax_id.compute_all(
            line.price_subtotal * (1 - (line.discount or 0.0) / 100.0), line.currency_id, 1)
        val = taxes['total_included'] - taxes['total_excluded']
        return val

    # @api.multi
    def _get_total_rental_cost(self):
        res = {}
        total = 0.00
        val = 0.00
        sum = 0.00
        cur_obj = self.env['res.currency']
        for obj in self:
            total = 0.00
            val = 0.00
            sum = 0.00
            cur = obj.pricelist_id.currency_id
            for line in obj.reservation_line:
                total += line.sub_total1
                val += self._amount_line_tax(line)
            for line in obj.food_items_ids:
                total += line.price_subtotal
                val += self._amount_food_tax(line)
            for line in obj.other_items_ids:
                total += line.price_subtotal
                val += self._amount_other_tax(line)
            if cur:
                sum = cur.round(total) + cur.round(val)
            obj.total_cost1 = sum

    def _get_deposit_cost1(self):
        total = 0
        for obj in self:
            if obj.deposit_policy == 'percentage':
                for rental_line in obj.reservation_line:
                    room_line_id = self.env['hotel.room'].search(
                        [('product_id', '=', rental_line.room_number.id)])
                    if room_line_id:
                        room_line_browse = self.env['hotel.room'].browse(room_line_id)[
                            0].id
                        if room_line_id.deposit_bool:
                            total += (rental_line.sub_total1 + self._amount_line_tax(
                                rental_line)) * obj.percentage / 100
                if total and (total < obj.min_dep_amount):
                    total = obj.min_dep_amount
            elif obj.deposit_policy == 'no_deposit':
                total = 0.0
            obj.deposit_cost = total

    @api.depends('checkin_date')
    def on_change_checkout(self):
        self.checkin_date = time.strftime('%Y-%m-%d %H:%M:%S')
        self.checkout_date = time.strftime('%Y-%m-%d %H:%M:%S')
        delta = timedelta(days=1)
        if not self.checkout_date:
            self.checkout_date = time.strftime('%Y-%m-%d %H:%M:%S')
        addDays = datetime.datetime(
            *time.strptime(self.checkout_date, '%Y-%m-%d %H:%M:%S')[:5]) + delta
        if self.checkin_date:
            new_date = str(self.checkin_date)
            self._cr.execute(
                'select max(start_date) from deposit_payment_policy where start_date <= %s ', (new_date,))
            a = self._cr.fetchone()
            if not a[0]:
                raise exceptions.except_orm(
                    'Configuration Error', 'Deposit policy is not define.')
            pay_obj = self.env['deposit.payment.policy'].search(
                [('start_date', '=', a[0])])
            dep_obj = self.env['deposit.payment.policy'].browse(pay_obj[0])
        val = {'value': {'dummy': addDays.strftime(
            '%Y-%m-%d %H:%M:%S'), 'percentage': dep_obj.percentage, 'min_dep_amount': dep_obj.min_amount}}
        return val

    banq_bool = fields.Boolean('Banquet Booking', default=False)
    deposit_policy = fields.Selection([('percentage', 'Deposit Percentage'), ('no_deposit', 'No Deposit')],
                                      'Deposit Policy', required=True, readonly=True, default='no_deposit')
    percentage = fields.Float("Percentage/Deposit Amount")
    min_dep_amount = fields.Float("Minimum Deposit Amount")
    food_items_ids = fields.One2many(
        'food.items', 'food_items_id', 'Food Items')
    other_items_ids = fields.One2many(
        'other.items', 'other_items_id', 'Other Items')
    untaxed_amt = fields.Float(
        compute='_get_subtotal_amount', string="Untaxed Amount")
    total_tax = fields.Float(compute='_get_total_tax', type="float", string="Reservation Tax",store=True,
                             help="The amount without tax.")
    total_cost1 = fields.Float(
        compute='_get_total_rental_cost', string="Total Reservation cost", )
    deposit_cost = fields.Float(
        compute='_get_deposit_cost1', string="Deposit Cost", )
    banquet_id = fields.Many2one(
        'banquet.quotation', 'Booking Ref,.', readonly=True)
    complimentary = fields.Selection([
        ('all_meals', 'All Meals'),
        ('no_meals', 'No Meals'),
        ('breakfast_dinner', 'Breakfast & Dinner'),
        ('breakfast', 'Breakfast')
    ], string='Meal Type', tracking=True)
    agent_comm = fields.Float("Commision")

   
    def done(self):
        active_id = self._ids
        for reservation in self:
            booking_ids = self.env['hotel.room.booking.history'].search([('booking_id', '=', reservation.id)])
            for booking_id in booking_ids:
                booking_id.write({
                    'check_in': datetime.now()
                })

            self.write({'agent_comm': reservation.total_cost1, })
            if reservation.deposit_cost2:
                data_obj = self.env['ir.model.data']
                data_id = data_obj._get_id(
                    'hotel_management', 'deposit_journal_entry_wizard1')
                view_id1 = False
                if self._context is None:
                    self._context = {}
                ctx = dict(self._context)
                ctx['active_ids'] = [reservation.id]
                ctx['booking_id'] = reservation.id
                if data_id:
                    view_id1 = data_obj.browse(data_id).res_id
                value = {
                    'name': _('Advance Payment Entry'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'deposit_journal_entry.wizard1',
                    'view_id': False,
                    'context': ctx,
                    'views': [(view_id1, 'form')],
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'nodestroy': True
                }
                return value
            elif (reservation.banq_bool and reservation.deposit_cost2):
                data_obj = self.env['ir.model.data']
                data_id = data_obj._get_id(
                    'banquet_managment', 'deposit_journal_entry_wizard')
                view_id1 = False
                if self._context is None:
                    self._context = {}
                ctx = dict(self._context)
                ctx['active_ids'] = [reservation.id]
                ctx['booking_id'] = reservation.id
                if data_id:
                    view_id1 = data_obj.browse(data_id).res_id
                value = {
                    'name': _('Deposit amount entry'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'deposit_journal_entry.wizard',
                    'view_id': False,
                    'context': ctx,
                    'views': [(view_id1, 'form')],
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'nodestroy': True
                }
                return value
            else:

                so = self.create_folio()
                folio = self.env['hotel.folio'].search([('reservation_id', '=', self.id)])

                for reservation in self:
                    if reservation.other_items_ids:
                        for service_line in reservation.other_items_ids:
                            product_id = self.env['product.product'].search(
                                [('id', '=', service_line.product_id.id)])
                            if product_id:
                                vals = {
                                    'folio_id': folio.id,
                                    'product_id': product_id.id,
                                    'name': product_id.name,
                                    'product_uom': service_line.product_uom.id,
                                    'product_uom_qty': service_line.product_uom_qty,
                                    'price_unit': service_line.price_unit,
                                }

                                self.env["hotel_service.line"].create(vals)
                    if reservation.food_items_ids:
                        for food_line in reservation.food_items_ids:
                            product_id = self.env['product.product'].search(
                                [('id', '=', food_line.product_id.id)])
                            if product_id:
                                vals = {
                                    'folio_id': folio.id,
                                    'product_id': product_id.id,
                                    'name': product_id.name,
                                    'product_uom': food_line.product_uom.id,
                                    'product_uom_qty': food_line.product_uom_qty,
                                    'price_unit': food_line.price_unit,
                                }

                                self.env["hotel_food.line"].create(vals)

                return so


class FoodItems(models.Model):
    _name = "food.items"
    _description = "Food Items Details"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    def _amount_line_tax_for_food(self, line):
        val = 0.0
        taxes = line.tax_id.compute_all(line.price_unit * (1 - (line.discount or 0.0) / 100.0), None,
                                        line.product_uom_qty)
        val = taxes['total_included'] - taxes['total_excluded']
        return val

    def _amount_line(self):
        res = {}
        cur_obj = self.env['res.currency']
        res_user = self.env['res.users']
        if self._context is None:
            self._context = {}
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            if line.food_items_id:
                taxes = line.tax_id.compute_all(
                    price, None, line.product_uom_qty)
                val = taxes['total_excluded']
                cur = line.food_items_id.pricelist_id.currency_id
            else:
                taxes = line.tax_id.compute_all(
                    price, None, line.product_uom_qty)
                val = taxes['total_excluded']
                user_id = res_user.browse()
                cur = user_id.company_id.currency_id
            line.price_subtotal = val

    def _amount_line_cost(self):
        res_user = self.env['res.users']
        res = {}
        if self._context is None:
            context = {}
        for line in self:
            if line:
                price = line.cost_price_unit
                taxes = line.pur_tax_ids.compute_all(
                    price, None, line.product_uom_qty)
                val = taxes['total_excluded']
                user_id = res_user.browse(self._uid)
                cur = user_id.company_id.currency_id
          
            line.cost_price_subtotal = cur.round(val)
        return res

    @api.onchange('product_id')
    @api.depends('banquet_id.pricelist_id', 'product_uom_qty')
    def onchange_product_id(self):
        res = {}
        if self.banquet_id:

            pricelist = self.banquet_id.pricelist_id.id
            if not pricelist:
                raise exceptions.except_orm(
                    'Warning', 'Price List is not define1.')
            if self.product_id:
                record = self.env['product.product'].browse(self.product_id.id)
                price_unit = self.env['product.pricelist']._price_get(
                    self.product_id, self.product_uom_qty, uom=record.uom_id)[pricelist]

                if price_unit is False:
                    raise UserError("Could not find a pricelist line matching this product!")

                res['price_unit'] = price_unit
                res['price_unit'] = get_price(self, pricelist, record.list_price)
                res['cost_price_unit'] = get_price(
                    self, pricelist, record.standard_price)
                res['cost_price_unit'] = record.standard_price
                res['product_uom'] = record.uom_id.id
                res['name'] = record.name
                tax_ids = []
                for tax_line in record.taxes_id:
                    tax_ids.append(tax_line.id)
                res['tax_id'] = [(6, 0, tax_ids)]
            return {'value': res}

    def get_subcategory_ids(self, parent_id):
        all_categ_ids = []
        get_ids = []
        if parent_id:
            categ_sub_ids = self.env['product.category'].search(
                [('parent_id', '=', parent_id)])
            if categ_sub_ids:
                for categ_sub in categ_sub_ids:
                    all_categ_ids.append(categ_sub)
                    get_ids = self.get_subcategory_ids(categ_sub)
                    if get_ids:
                        for get_sub_id in get_ids:
                            all_categ_ids.append(get_sub_id)
        return all_categ_ids

    def get_category_id(self):
        food_categ = []
        obj = self.env['product.category'].search([('name', '=', 'Foods')])
        categ_ids = self.env['product.category'].search(
            [('parent_id', '=', obj[0])])
        if categ_ids:
            for categ in categ_ids:
                food_categ.append(categ)
                get_categ_ids = self.get_subcategory_ids(categ)
                if get_categ_ids:
                    for get_categ_id in get_categ_ids:
                        food_categ.append(get_categ_id)
        food_categ.append(obj[0])
        return food_categ

    food_items_id = fields.Many2one('hotel.reservation')
    name = fields.Char('Description', required=True, index=True,tracking=True)
    product_id = fields.Many2one('product.product', 'Product', domain=[(
        'sale_ok', '=', True)], change_default=True,
                                 help="Will list out all food items that belong to company of selected shop. \n It also shows global product as well.",tracking=True)
    price_unit = fields.Float(
        'Unit Price', required=True, digits='Sale Price', default=0.0,tracking=True)
    price_subtotal = fields.Float(
        compute='_amount_line', string='Subtotal', digits='Sale Price',tracking=True)
    tax_id = fields.Many2many(
        'account.tax', 'food_item_tax', 'order_line_id', 'tax_id', 'Taxes')
    product_uom_qty = fields.Float(
        'Quantity (UoM)', digits='Product UoS', default=1,tracking=True)
    product_uom = fields.Many2one('uom.uom', 'UoM', required=True,tracking=True)
    discount = fields.Float('Discount (%)', digits=(16, 2), default=0.0,tracking=True)
    banquet_id = fields.Many2one('banquet.quotation',tracking=True)
    res_id = fields.Many2one('hotel.reservation',tracking=True)
    cost_price_unit = fields.Float('Cost Price', digits='Cost Price')
    cost_price_subtotal = fields.Float(
        compute='_amount_line_cost', string='Cost Subtotal', digits='Cost Price')
    pur_tax_ids = fields.Many2many(
        'account.tax', 'pur_tax_tax_line_rel', 'food_id', 'tax_id', 'Purchase Taxes')
    purches_bol = fields.Boolean('Show Purchase Tax')
    category_id = fields.Char('Category', default='get_category_id')
    currency_id = fields.Many2one('res.currency', compute='_compute_currency', string="Currency")

    @api.depends('banquet_id')
    def _compute_currency(self):
        for rec in self:
            rec.currency_id = rec.banquet_id.pricelist_id.currency_id or rec.banquet_id.company_id.currency_id


class OtherItems(models.Model):
    _name = "other.items"
    _description = "Other Items Details"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    def _amount_line(self):
        res = {}
        cur_obj = self.env['res.currency']
        res_user = self.env['res.users']
        if self._context is None:
            self._context = {}
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            if line.other_items_id:
                taxes = line.tax_id.compute_all(
                    price, None, line.product_uom_qty)
                val = taxes['total_excluded']
                cur = line.other_items_id.pricelist_id.currency_id
            else:
                taxes = line.tax_id.compute_all(
                    price, None, line.product_uom_qty)
                val = taxes['total_excluded']
                user_id = res_user.browse()
                cur = user_id.company_id.currency_id
            line.price_subtotal = val

    @api.onchange('product_id')
    @api.depends('banquet_id.pricelist_id', 'product_uom_qty')
    def onchange_product_id(self):
        res = {}
        if self.banquet_id:
            pricelist = self.banquet_id.pricelist_id.id
            if not pricelist:
                raise UserError('Price List is not define.')
            if self.product_id:
                record = self.env['product.product'].browse(self.product_id.id)
                price_unit = self.env['product.pricelist']._price_get(
                    self.product_id, self.product_uom_qty, uom=record.uom_id)[pricelist]
                if price_unit is False:
                    raise UserError(_(
                        "Couldn't find a pricelist line matching this product!"))
                res['price_unit'] = price_unit
                res['cost_price_unit'] = record.standard_price
                res['product_uom'] = record.uom_id.id
                res['name'] = record.name
                tax_ids = []
                for tax_line in record.taxes_id:
                    tax_ids.append(tax_line.id)
                self.tax_id = [(6, 0, tax_ids)]
            return {'value': res}

    def _amount_line_cost(self):
        res = {}
        tax_obj = self.env['account.tax']

        res_user = self.env['res.users'].search([('id', '=', self._context.get('uid'))])
        cur_obj = res_user.company_id.currency_id
        cur = res_user.company_id.currency_id

        for line in self:
            val = 0
            if line.banquet_id:
                price = line.cost_price_unit
                taxes = line.pur_tax_ids.compute_all(
                    price, None, line.product_uom_qty)
                val = taxes['total_excluded']

            line.update({
                'cost_price_subtotal': cur.round(val) if cur else round(val, 2),
            })
            line.cost_price_subtotal = cur.round(val) if cur else round(val, 2)

    other_items_id = fields.Many2one('hotel.reservation')
    name = fields.Char('Description', required=True, index=True,tracking=True)
    product_id = fields.Many2one('product.product', 'Product', domain=[
        ('sale_ok', '=', True), ('isservice', '=', True)], change_default=True,tracking=True)
    price_unit = fields.Float(
        'Unit Price', required=True, digits='Sale Price', default=0.0)
    price_subtotal = fields.Float(
        compute='_amount_line', string='Subtotal', digits='Sale Price')
    tax_id = fields.Many2many(
        'account.tax', 'other_service_tax', 'order_line_id', 'tax_id', 'Taxes')
    product_uom_qty = fields.Float(
        'Quantity (UoM)', digits='Product UoS', default=1)
    product_uom = fields.Many2one('uom.uom', 'UoM', required=True)
    discount = fields.Float('Discount (%)', digits=(16, 2), default=0.0,tracking=True)
    banquet_id = fields.Many2one('banquet.quotation')
    cost_price_unit = fields.Float('Cost Price', digits='Cost Price')
    cost_price_subtotal = fields.Float(
        compute='_amount_line_cost', string='Cost Subtotal', digits='Cost Price')
    pur_tax_ids = fields.Many2many(
        'account.tax', 'pur_other_tax_line_rel', 'other_id', 'tax_id', 'Purchase Taxes')
    purches_bol = fields.Boolean('Show Purchase Tax')
    currency_id = fields.Many2one('res.currency', compute='_compute_currency', string="Currency")

    @api.depends('banquet_id')
    def _compute_currency(self):
        for rec in self:
            rec.currency_id = rec.banquet_id.pricelist_id.currency_id or rec.banquet_id.company_id.currency_id


class HotelRoom(models.Model):
    _inherit = "hotel.room"
    _description = "room Inherit "

    deposit_bool = fields.Boolean('Is Deposit Applicable', default=True)


class BanquetQuotationLeadHistory(models.Model):
    _name = 'banquet.quotation.lead.history'
    _description = 'itinerary lead history'

    ref_id = fields.Many2one('crm.lead', 'History')
    name = fields.Char("Banquet Quotation No.", readonly=True)
    contact_name = fields.Char('Contact Name', readonly=True, )
    current_date = fields.Date("Creation Date", required=True, )
    update_date = fields.Date("Last Updated Date", required=True, )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('send_to', 'Send To Customer'),
        ('approve', 'Approved'),
        ('refused', 'Refused'),
    ], 'Status', readonly=True)
