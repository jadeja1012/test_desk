# -*- encoding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
# from mx import DateTime
from odoo import netsvc
# from odoo.tools import config
from datetime import datetime


class product_category(models.Model):
    _inherit = "product.category"

    ismenutype = fields.Boolean('Is Menu Type')


class product_product(models.Model):
    _inherit = "product.product"

    ismenucard = fields.Boolean('Is room ')


class hotel_menucard_type(models.Model):
    _name = 'hotel.menucard.type'
    _description = 'amenities Type'
    _inherits = {'product.category': 'menu_id'}

    menu_id = fields.Many2one('product.category', string='Category', required=True, ondelete='cascade')
    ismenutype = fields.Boolean('Is Menu Type', related='menu_id.ismenutype', inherited=True, default=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 domain="[('id', 'in', [current_company_id])]",
                                 required=True)

    def unlink(self):
        for categ in self:
            categ.menu_id.unlink()
        return super(hotel_menucard_type, self).unlink()


class Hotel_menucard(models.Model):
    _name = 'hotel.menucard'
    _description = 'Hotel Menucard'
    _inherits = {'product.product': 'product_id'}
    _inherit = ['mail.thread']

    product_id = fields.Many2one('product.product', string='Product_id', required=True, ondelete='cascade')
    ismenucard = fields.Boolean('Is Hotel Room', related='product_id.ismenucard', inherited=True, default=True)
    currency_id = fields.Many2one('res.currency', 'Currency')

    def _price_compute(self):
        for ticket in self:
            if ticket.product_id and ticket.product_id.lst_price:
                ticket.price = ticket.product_id.lst_price or 0
            elif not ticket.price:
                ticket.price = 0

    def action_open_documents(self):
        self.product_id.product_tmpl_id.action_open_documents()

    def action_compute_bom_days(self):
        return True

    def action_open_label_layout(self):
        action = self.env['ir.actions.act_window']._for_xml_id('product.action_open_label_layout')
        action['context'] = {'default_product_tmpl_ids': self.ids}
        return action
        
    def open_pricelist_rules(self):
        self.ensure_one()
        domain = ['|',
                  ('product_tmpl_id', '=', self.id),
                  ('product_id', 'in', self.product_variant_ids.ids)]
        return {
            'name': ('Price Rules'),
            'view_mode': 'tree,form',
            'views': [(self.env.ref('product.product_pricelist_item_tree_view_from_product').id, 'tree'),
                      (False, 'form')],
            'res_model': 'product.pricelist.item',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': domain,
            'context': {
                'default_product_tmpl_id': self.id,
                'default_applied_on': '1_product',
                'product_without_variants': self.product_variant_count == 1,
            },
        }

    @api.onchange('type')
    def onchange_type(self):
        res = {}
        if self.type in ('consu', 'service'):
            res = {'value': {'valuation': 'manual_periodic'}}
        return res

    @api.onchange('tracking')
    def onchange_tracking(self):
        if not self.tracking:
            return {}
        product_product = self.env['product.product']
        variant_ids = product_product.search(
            [('product_tmpl_id', 'in', self._ids)])
        for variant_id in variant_ids:
            variant_id.onchange_tracking()

    def read_followers_data(self):
        result = []
        technical_group = self.env['ir.model.data'].get_object('base', 'group_no_one')
        for follower in self.env['res.partner'].browse(self._ids):
            is_editable = self._uid in map(lambda x: x.id, technical_group.users)
            is_uid = self._uid in map(lambda x: x.id, follower.user_ids)
            data = (follower.id,
                    follower.name,
                    {'is_editable': is_editable,
                     'is_uid': is_uid
                     },
                    )
            result.append(data)
        return result

    def unlink(self):
        return super(Hotel_menucard, self).unlink()

    @api.onchange('uom_id', 'uom_po_id')
    def onchange_uom(self):
        if self.uom_id:
            return {'value': {'uom_po_id': self.uom_id}}
        return {}

    def message_get_subscription_data(self, user_pid=None):
        return self.env['mail.thread']._get_subscription_data(None, None, user_pid=user_pid)
    
    def action_open_label_layout(self):
        action = self.env['ir.actions.act_window']._for_xml_id('product.action_open_label_layout')
        action['context'] = {'default_product_tmpl_ids': self.ids}
        return action  

class hotel_restaurant_tables(models.Model):
    _name = "hotel.restaurant.tables"
    _description = "Includes Hotel Restaurant Table"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char(string='Table number', required=True)
    capacity = fields.Integer(string='Capacity')
    state = fields.Selection([('available', 'Available'), ('book', 'Booked')],
                             string='State', default='available', index=True, required=True, readonly=True,tracking=True)


class hotel_restaurant_reservation(models.Model):

    @api.model_create_multi
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code(
            'hotel.restaurant.reservation')
        self.write({'name': vals['name']})
        return super(hotel_restaurant_reservation, self).create(vals)

    def create_order(self):
        for i in self:
            table_ids = [x.id for x in i.tableno]
            kot_data = self.env['hotel.reservation.order'].create({
                'reservation_id': i.id,
                'date1': i.start_date,
                'partner_id': i.cname.id,
                'room_no': i.room_no.id,
                'folio_id': i.folio_id.id,
                'table_no': [(6, 0, table_ids)],
            })
            for line in i.order_list_ids:
                line.write({'o_l': kot_data.id})
        self.write({'state': 'order'})
        return True

    def action_set_to_draft(self, *args):
        self.write({'state': 'draft'})
        wf_service = netsvc.LocalService('workflow')
        for record in self._ids:
            wf_service.trg_create(self._uid, self._name, record, self._cr)
        return True

    def table_reserved(self):
        for reservation in self:
            if reservation.room_no:
                if reservation.start_date <= reservation.folio_id.checkin_date and reservation.start_date >= reservation.folio_id.checkout_date:
                    raise UserError('Please Check Start Date which is not between check in and check out date')
                if reservation.end_date <= reservation.folio_id.checkin_date and reservation.end_date >= reservation.folio_id.checkout_date:
                    raise UserError('Please Check End Date which is not between check in and check out date')
            self._cr.execute("select count(*) from hotel_restaurant_reservation as hrr "
                             "inner join reservation_table as rt on rt.reservation_table_id = hrr.id "
                             "where (start_date,end_date)overlaps( timestamp %s , timestamp %s ) "
                             "and hrr.id<> %s "
                             "and rt.name in (select rt.name from hotel_restaurant_reservation as hrr "
                             "inner join reservation_table as rt on rt.reservation_table_id = hrr.id "
                             "where hrr.id= %s) and hrr.state not in ('order','cancel')",
                             (reservation.start_date, reservation.end_date, reservation.id, reservation.id))

            res = self._cr.fetchone()
            roomcount = res and res[0] or 0.0
            if roomcount:
                raise UserError(
                    'You tried to confirm reservation with table those already reserved in this reservation period')
            else:
                self.write({'state': 'confirm'})
            return True

    def table_cancel(self, *args):
        return self.write({'state': 'cancel'})

    def table_done(self, *args):
        return self.write({'state': 'done'})

    _name = "hotel.restaurant.reservation"
    _description = "Includes Hotel Restaurant Reservation"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char('Reservation No', readonly=True)
    room_no = fields.Many2one('hotel.room', 'Room No')
    start_date = fields.Datetime('Start Date', required=True)
    end_date = fields.Datetime('End Date', required=True)
    cname = fields.Many2one('res.partner', 'Customer Name', required=True)
    folio_id = fields.Many2one('hotel.folio', 'Hotel Folio', ondelete='cascade')
    tableno = fields.Many2many('hotel.restaurant.tables', 'reservation_table', 'reservation_table_id', 'name',
                               'Table number')
    order_list_ids = fields.One2many('hotel.restaurant.order.list', 'order_l', 'Order List')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('done', 'Done'), ('order', 'Order Done'), (
        'cancel', 'Cancelled')], 'State', default='draft', index=True, required=True, readonly=True,tracking=True)

    def onchange_partner_id(self):
        if not self.partner_id:
            return {'value': {'partner_address_id': False}}
        addr = self.partner_id.address_get(['default'])
        return {'value': {'partner_address_id': addr['default']}}


class hotel_restaurant_kitchen_order_tickets(models.Model):
    _name = "hotel.restaurant.kitchen.order.tickets"
    _description = "Includes Hotel Restaurant Order"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    @api.model_create_multi
    def create(self, vals):
        for rec in vals:
            rec['orderno'] = self.env['ir.sequence'].next_by_code('hotel.reservation.order12')
        return super(hotel_restaurant_kitchen_order_tickets, self).create(vals)

    orderno = fields.Char('KOT Number', readonly=True)
    resno = fields.Char('Order Number',tracking=True)
    kot_date = fields.Date('Date',tracking=True)
    room_no = fields.Char('Room No', readonly=True,tracking=True)
    w_name = fields.Char('Waiter Name', readonly=True)
    tableno = fields.Many2many('hotel.restaurant.tables', 'temp_table3', 'table_no', 'name', 'Table number')
    kot_list = fields.One2many('hotel.restaurant.order.list', 'kot_order_list', 'Order List')
    

class hotel_restaurant_order(models.Model):

    @api.model_create_multi
    def create(self, vals):
        for rec in vals:
            order_no = self.env['ir.sequence'].next_by_code('hotel.restaurant.order')
            rec.update({
                'order_no': order_no,
                'name': order_no
            })

        
        return super(hotel_restaurant_order, self).create(vals)

    def _sub_total(self):
        res = {}
        for sale in self:
            res[sale.id] = 0.00
            for line in sale.order_list:
                res[sale.id] += line.price_subtotal
        return res

    def _total(self):
        res = {}
        for line in self:
            res[line.id] = line.amount_subtotal + (line.amount_subtotal * line.tax) / 100
        return res

    _name = "hotel.restaurant.order"
    _description = "Includes Hotel Restaurant Order"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    order_no = fields.Char('Order Number', readonly=True)
    name = fields.Char('Name',tracking=True)
    partner_id = fields.Many2one('res.partner', 'Customer', required=True,tracking=True)
    guest_name = fields.Char('Guest Name',tracking=True)
    o_date = fields.Datetime('Date', required=True, default=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),tracking=True)
    room_no = fields.Many2one('hotel.room', 'Room No',tracking=True)
    folio_id = fields.Many2one('hotel.folio', 'Hotel Folio Ref',tracking=True)
    waiter_name = fields.Many2one('res.partner', 'Waiter Name')
    table_no = fields.Many2many('hotel.restaurant.tables', 'temp_table2', 'table_no', 'name', 'Table number')
    order_list = fields.One2many('hotel.restaurant.order.list', 'o_list', 'Order List')
    tax = fields.Float('Tax (%) ',tracking=True)
    amount_subtotal = fields.Float(compute='_sub_total', string='Subtotal',tracking=True)
    amount_total = fields.Float(compute='_total', string='Total',tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('done', 'Done'), (
        'order', 'Order Done'), ('cancel', 'Cancelled')], string='State', default='draft', index=True, required=True,tracking=True)

    invoice_count = fields.Integer(compute="_compute_invoice", string='Invoice Count', copy=False, default=0,
                                   readonly=True)
    invoice_ids = fields.Many2many('account.move', compute="_compute_invoice", string='Invoices', copy=False,
                                   readonly=True)
    picking_count = fields.Integer(compute="_compute_pickings", string='Picking Count', copy=False, default=0,
                                   readonly=True)
    picking_ids = fields.Many2many('stock.picking', compute="_compute_pickings", string='Pickings', copy=False,
                                   readonly=True)
    company_id = fields.Many2one(
        'res.company', string='Company', store=True)
    pricelist_id = fields.Many2one(
        'product.pricelist', 'Pricelist',)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,default=lambda self: self.env.user.company_id.currency_id.id)

    @api.depends('picking_count')
    def _compute_pickings(self):
        for order in self:
            if self.order_no:
                pickings = self.env['stock.picking'].search([('origin', "=", self.order_no)])
                order.picking_ids = pickings
                order.picking_count = len(pickings)
            else:
                order.picking_count = 0

    def action_picking_order_view(self):
        pickings = self.mapped('picking_ids')
        action = self.env.ref('stock.stock_picking_action_picking_type').sudo().read()[0]
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif len(pickings) == 1:
            form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = pickings.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    @api.depends('order_no', 'order_list', 'invoice_count')
    def _compute_invoice(self):
        for order in self:
            if self.order_no:
                invoices = self.env['account.move'].search([('invoice_origin', "=", self.order_no)])
                order.invoice_ids = invoices
                order.invoice_count = len(invoices)
            else:
                order.invoice_count = 0

    def action_invoice_view(self):
        invoices = self.mapped('invoice_ids')
        action = self.env.ref('account.action_move_out_invoice_type').sudo().read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        return action
    


    def confirm_order(self, *args):
        for obj in self:
            for line in obj.table_no:
                line.write({'state': 'book'})
        self.write({'state': 'confirm'})
        return True

    def cancel_order(self, *args):
        for obj in self:
            for line in obj.table_no:
                line.write({'avl_state': 'available'})
            obj.write({'state': 'cancel'})

    def create_invoice(self):
        for obj in self:
            for line in obj.table_no:
                line.write({'avl_state': 'available'})

            acc_id = obj.partner_id.property_account_receivable_id.id
            journal_obj = self.env['account.journal'].search(
                [('type', '=', 'sale')], limit=1)

            journal_id = None
            if journal_obj[0]:
                journal_id = journal_obj[0].id

            type = 'out_invoice'

            if not obj.room_no:
                inv = {
                    'invoice_origin': obj.order_no,
                    'move_type': type,
                    'ref': "Order Invoice",
                    'partner_id': obj.partner_id.id,
                    'currency_id': obj.pricelist_id.currency_id.id,
                    'journal_id': journal_id,
                }
                inv_id = self.env['account.move'].create(inv)
                todo = []
                for ol in obj.order_list:
                    todo.append(ol.id)
                    if ol.product_id.categ_id:
                        a = ol.product_id.categ_id.property_account_income_categ_id.id
                        if not a:
                            raise ValidationError(_(
                                'There is no expense account defined for this product: "%s" (id:%d)') % (
                                                      ol.product_id.name, ol.product_id.id,))
                    else:
                        a = self.env['ir.property'].get(
                            'property_account_income_categ', 'product.category').id

                    tax_ids = []
                    for tax_line in ol.tax_id:
                        tax_ids.append(tax_line.id)
                    inv_line_values = {
                        'invoice_line_ids': [(0, 0, {
                            'name': ol.product_id.name,
                            'move_id': inv_id.id,
                            'account_id': a,
                            'price_unit': ol.item_rate,
                            'quantity': float(ol.item_qty),
                            'product_id': ol.product_id.product_id.id,
                            'tax_ids': [(6, 0, tax_ids)],
                        })]
                    }

                    inv_id.write({

                        'invoice_line_ids': [(0, 0, {
                            'name': ol.product_id.name,
                            'move_id': inv_id.id,
                            'account_id': a,
                            'price_unit': ol.item_rate,
                            'quantity': float(ol.item_qty),
                            'product_id': ol.product_id.product_id.id,
                            'tax_ids': [(6, 0, tax_ids)],
                        })]
                    })
        self.write({'state': 'done'})
        if self.folio_id.id:
            for r in self.order_list:
                tax_ids = []
                for tax_line in r.tax_id:
                    tax_ids.append(tax_line.id)
                so_line = {
                    'name': r.product_id.name,
                    'product_uom_qty': r.item_qty,
                    'product_id': r.product_id.product_id.id,
                    'price_unit': r.item_rate,
                    'product_uom': r.product_id.product_id.uom_id.id,
                    'order_id': self.folio_id.order_id.id,
                    'tax_id': [(6, 0, tax_ids)],
                }
                so_line_id = self.env['sale.order.line'].create(so_line)

                service_line = {
                    'folio_id': self.folio_id.id,
                    'food_line_id': so_line_id.id,
                    'source_origin': obj.order_no,
                }
                service_line_id = self.env[
                    'hotel_food.line'].create(service_line)

        return True

    def generate_kot(self):
        for order in self:
            table_ids = [x.id for x in order.table_no]

        # Check if there is an existing KOT/BOT record for this order
            existing_tickets = self.env['hotel.restaurant.kitchen.order.tickets'].search([('resno', '=', order.order_no)])
            if existing_tickets:
                ticket_data = existing_tickets[0]
            else:
                # Prepare order data for new KOT/BOT record
                order_data = {
                'resno': order.order_no,
                'kot_date': order.o_date,
                'room_no': order.room_no.name if order.room_no else False,
                'w_name': order.waiter_name1.name if order.waiter_name1 else False,
                'shop_id': order.shop_id.id if order.shop_id else False,
                'tableno': [(6, 0, table_ids)] if table_ids else False,
                'product_nature': None,  # This will be set later
                'pricelist_id': order.pricelist_id.id if order.pricelist_id else False,
            }

                if not order_data['shop_id']:
                    raise ValueError("Shop ID (shop_id) must be set for the order.")    
                if any(ol.product_id.product_nature == 'kot' for ol in order.order_list):
                    order_data['product_nature'] = 'kot'
                    ticket_data_kot = self.env['hotel.restaurant.kitchen.order.tickets'].create(order_data)

                if any(ol.product_id.product_nature == 'bot' for ol in order.order_list ):
                    order_data['product_nature'] = 'bot'
                    ticket_data_bot = self.env['hotel.restaurant.kitchen.order.tickets'].create(order_data)


            order_lines_to_create_kot = []
            order_lines_to_create_bot = []
            for order_line in order.order_list:
                existing_order_lines = self.env['hotel.restaurant.order.list'].search([
                ('product_id', '=', order_line.product_id.id),
                ('kot_order_list.resno', '=', order.order_no),
                ])

                if existing_order_lines:
                    continue  # Skip existing order lines

                product_id = order_line.product_id
                product_nature = product_id.product_nature

                if product_nature in ['kot']:
                    current_qty = int(order_line.item_qty) - order_line.previous_qty if order_line.states else order_line.item_qty
                    o_line = {
                    'product_id': order_line.product_id.id,
                    'kot_order_list': ticket_data_kot.id,
                    'item_qty': current_qty,
                    'item_rate': order_line.item_rate,
                    'product_nature': product_nature,
                }
                    order_lines_to_create_kot.append(o_line)
                    self.env['hotel.restaurant.order.list'].write({'previous_qty': order_line.item_qty, 'states': True})

                    total_qty = sum(int(ol.item_qty) for ol in self.env['hotel.restaurant.order.list'].search([
                    ('product_id', '=', order_line.product_id.id), ('kot_order_list.resno', '=', order.order_no)]))
                    self.env['hotel.restaurant.order.list'].write({'total': total_qty})

                if product_nature in ['bot']:
                    current_qty = int(order_line.item_qty) - order_line.previous_qty if order_line.states else order_line.item_qty
                    o_line = {
                    'product_id': order_line.product_id.id,
                    'kot_order_list': ticket_data_bot.id,
                    'item_qty': current_qty,
                    'item_rate': order_line.item_rate,
                    'product_nature': product_nature,
                }
                    order_lines_to_create_bot.append(o_line)
                    self.env['hotel.restaurant.order.list'].write({'previous_qty': order_line.item_qty, 'states': True})

                    total_qty = sum(int(ol.item_qty) for ol in self.env['hotel.restaurant.order.list'].search([
                    ('product_id', '=', order_line.product_id.id), ('kot_order_list.resno', '=', order.order_no)]))
                    self.env['hotel.restaurant.order.list'].write({'total': total_qty})
                

            if order_lines_to_create_kot:
                self.env['hotel.restaurant.order.list'].create(order_lines_to_create_kot)

            if order_lines_to_create_bot:
                self.env['hotel.restaurant.order.list'].create(order_lines_to_create_bot)

            stock_brw = self.env['stock.picking'].search([('origin', '=', order.order_no)])
            if stock_brw:
                for order_items in order.order_list:
                    total_qty1 = sum(int(ol.item_qty) for ol in self.env['hotel.restaurant.order.list'].search([
                    ('product_id', '=', order_items.product_id.id), ('kot_order_list.resno', '=', order.order_no)]))
                    product_id = self.env['hotel.menucard'].browse(order_items.product_id.id).product_id.id

                    if product_id:
                        move_id = self.env['stock.move'].search([('product_id', '=', product_id), ('picking_id', '=', stock_brw.id)])
                        if move_id:
                            move_id.write({'product_uom_qty': total_qty1})

            self.write({'state': 'order'})
        return True


class hotel_reservation_order(models.Model):

    @api.model_create_multi
    def create(self, vals):
        # function overwrites create method and auto generate request no.
        vals['order_number'] = self.env['ir.sequence'].next_by_code('hotel.reservation.order')
        return super(hotel_reservation_order, self).create(vals)

   
    def _sub_total(self):
        res = {}
        for sale in self:
            res[sale.id] = 0.00
            for line in sale.order_list:
                res[sale.id] += line.price_subtotal
        return res

    def _total(self):
        res = {}
        for line in self:
            res[line.id] = line.amount_subtotal + \
                           (line.amount_subtotal * line.tax) / 100
        return res

   
    def reservation_generate_kot(self):
        for order in self:
            table_ids = [x.id for x in order.table_no]
            kot_data = self.env['hotel.restaurant.kitchen.order.tickets'].create({
                'resno': order.order_number,
                'room_no': order.room_no.name,
                'kot_date': order.date1,
                'w_name': order.waitername.name,
                'tableno': [(6, 0, table_ids)],
            })

            for order_line in order.order_list:
                o_line = {
                    'kot_order_list': kot_data.id,
                    'name': order_line.name.id,
                    'item_qty': order_line.item_qty,
                }
                self.env['hotel.restaurant.order.list'].create(o_line)
        self.write({'state': 'order'})
        return True

    _name = "hotel.reservation.order"
    _description = "Reservation Order"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    order_number = fields.Char('Order No', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Customer', required=True,tracking=True)
    guest_name = fields.Char('Guest Name',tracking=True)
    room_no = fields.Many2one('hotel.room', 'Room No',tracking=True)
    folio_id = fields.Many2one('hotel.folio', 'Hotel Folio Ref',tracking=True)
    reservation_id = fields.Many2one('hotel.restaurant.reservation', 'Reservation No',tracking=True)
    date1 = fields.Datetime('Date', required=True,tracking=True)
    waitername = fields.Many2one('res.partner', 'Waiter Name')
    table_no = fields.Many2many('hotel.restaurant.tables', 'temp_table4', 'table_no', 'name', 'Table number')
    order_list = fields.One2many('hotel.restaurant.order.list', 'o_l', 'Order List')
    tax = fields.Float('Tax (%) ')
    amount_subtotal = fields.Float(compute='_sub_total', string='Subtotal')
    amount_total = fields.Float(compute='_total', string='Total')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('done', 'Done'), ('order', 'Order Done'), (
        'cancel', 'Cancelled')], 'State', default='draft', index=True, required=True, readonly=True,tracking=True)

    invoice_count = fields.Integer(compute="_compute_invoice", string='Invoice Count', copy=False, default=0, readonly=True)
    invoice_ids = fields.Many2many('account.move', compute="_compute_invoice", string='Invoices', copy=False, readonly=True )

    @api.depends('order_number', 'order_list', 'invoice_count')
    def _compute_invoice(self):
        for order in self:
            invoices = self.env['account.move'].search([('name', "=", self.order_number)])
            order.invoice_ids = invoices
            order.invoice_count = len(invoices)

    def action_invoice_view(self):
        invoices = self.mapped('invoice_ids')
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def confirm_order(self, *args):
        for obj in self:
            for line in obj.table_no:
                line.write({'state': 'book'})
        self.write({'state': 'confirm'})
        return True

    def create_invoice(self, *args):
        for obj in self:
            for line in obj.table_no:
                line.write({'state': 'available'})

            acc_id = obj.partner_id.property_account_receivable_id.id
            journal_obj = self.env['account.journal']
            journal_ids = journal_obj.search([('type', '=', 'sale')], limit=1)

            journal_id = None
            if journal_ids[0]:
                journal_id = journal_ids[0].id

            inv = {
                'name': obj.order_number,
                'origin': obj.order_number,
                'type': 'out_invoice',
                'reference': "Order Invoice",
                'account_id': acc_id,
                'partner_id': obj.partner_id.id,
                'currency_id': self.env['res.currency'].search([('name', '=', 'EUR')])[0].id,
                'journal_id': journal_id,
                'amount_tax': 0,
                'amount_untaxed': obj.amount_total,
                'amount_total': obj.amount_total,
            }

            inv_id = self.env['account.move'].create(inv)

            todo = []
            for ol in obj.order_list:
                todo.append(ol.id)
                if ol.name.categ_id:
                    a = ol.name.categ_id.property_account_income_categ_id.id
                    if not a:
                        raise ValidationError(
                            _('There is no expense account defined for this product: "%s" (id:%d)') % (
                                ol.product_id.name, ol.product_id.id,))
                else:
                    a = self.env['ir.property'].get(
                        'property_account_income_categ_id', 'product.category').id

                il = {
                    'name': ol.name.name,
                    'account_id': a,
                    'price_unit': ol.item_rate,
                    'quantity': ol.item_qty,
                    'uos_id': False,
                    'origin': obj.order_number,
                    'invoice_id': inv_id.id,
                    'price_subtotal': ol.price_subtotal,
                }

                cres = self.env['account.move.line'].create(il)

            if obj.room_no:
                self._cr.execute('insert into order_reserve_invoice_rel(folio_id,invoice_id) values (%s,%s)',
                                 (obj.folio_id.id, inv_id.id))
        self.write({'state': 'done'})
        return True


class hotel_restaurant_order_list(models.Model):
    _name = "hotel.restaurant.order.list"
    _description = "Includes Hotel Restaurant Order"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    
    # @api.multi
    def _sub_total(self):
        res = {}
        for line in self:
            res[line.id] = line.item_rate * int(line.item_qty)
        return res

    @api.onchange('name')
    def on_change_item_name(self):
        if not self.name:
            return {'value': {}}
        return {'value': {'item_rate': self.name.list_price}}

    o_list = fields.Many2one('hotel.restaurant.order')
    order_l = fields.Many2one('hotel.restaurant.reservation')
    o_l = fields.Many2one('hotel.reservation.order')
    kot_order_list = fields.Many2one('hotel.restaurant.kitchen.order.tickets')
    name = fields.Many2one('hotel.menucard', 'Item',tracking=True)
    item_qty = fields.Char('Qty', required=True,tracking=True)
    item_rate = fields.Float('Rate',tracking=True)
    price_subtotal = fields.Float(compute='_sub_total', string='Subtotal',tracking=True)