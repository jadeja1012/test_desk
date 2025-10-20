import time
import datetime
from dateutil.relativedelta import relativedelta
from PIL import Image
from odoo.tools import formatLang, float_is_zero
from odoo import fields,models,api
from odoo.http import request
from odoo.tools.translate import _
# import odoo.addons.decimal_precision as dp
from decimal import Decimal
from odoo import netsvc, tools
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_round, float_repr, float_compare
from collections import defaultdict
from markupsafe import Markup


class HotelRestaurantPos(models.Model):
    _name = "hotel.restaurant.pos"
    _description = "Restaurant POS related Back end"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    kot_prev_quantity=0;
    def update_table_book(self,vals):

        for t_id in vals['tableid']:
            self.env['hotel.restaurant.tables'].write({ 'avl_state': 'book', })


    def update_table_available(self,vals):
        
        for ts_id in vals['tab_id']:
                self.env['hotel.restaurant.tables'].write({'avl_state':'available'})

    def create_kot(self,vals):
        
        if vals['kot']:
            if 'tableno' in vals:

                shop_name=vals['shop_name']
                order_no = vals['orderno']
                reservation_no = vals['resno']
                table=vals['tableno']
                waiter=vals['w_name']
                date=vals['kot_date']
                kot_data=False

                shop_id=self.env['sale.shop'].search([('name','=',shop_name)])[0]
                product_nature=None
                create_kot = False
                for k in vals['kot'] :
                    old_product_id=k[2]['product_id'];
                    product_obj=self.env['product.product'].browse(k[2]['product_id'])
                    product_name=product_obj.name
                    product_nature=product_obj.product_nature
                    max_qty=0
                    kot_quantity=k[2]['qty']

                    product_obj=self.env['product.product'].browse(k[2]['product_id'])
                    menu_card_id = self.env['hotel.menucard'].search([('name','=',product_obj.name)])
                    old_kot_id = self.env['hotel.restaurant.kitchen.order.tickets'].search([('resno','=',reservation_no)])
                    if not old_kot_id:
                        create_kot = True
                    for test in self.env['hotel.restaurant.order.list'].search([('product_id','=',menu_card_id[0]), ('resno','=',reservation_no)]):
                                prod_name=self.env['hotel.restaurant.order.list'].browse(test)
                                if max_qty <= prod_name.product_qty:
                                    max_qty = prod_name.product_qty

                    if max_qty!=kot_quantity:
                        create_kot = True
                old_kot_id = self.env['hotel.restaurant.kitchen.order.tickets'].search([('resno','=',reservation_no)])
                old_kot_length = len(old_kot_id)

                if create_kot:
                    kot_data=self.env['hotel.restaurant.kitchen.order.tickets'].create({
                                                                                            'orderno':order_no,
                                                                                            'resno':reservation_no,
                                                                                            'kot_date':date,
                                                                                            'w_name':waiter,
                                                                                            'shop_id':shop_id,
                                                                                            'product_nature':product_nature,
                                                                                            })
                    table_id=self.env['hotel.restaurant.tables'].search([('name','=',table)])
                    for tab_id in table_id:
                                self._cr.execute('insert into temp_table3 (name,table_no) values (%s,%s)',(tab_id,kot_data))
                for x in vals['kot']:
                    kot_quantities=x[2]['qty']
                    sum_qty = 0
                    i=0
                    for i in range(0,old_kot_length) :
                       kot_no_id = old_kot_id[i]
                       old_kot_object = self.env['hotel.restaurant.kitchen.order.tickets'].browse(kot_no_id)
                       
                       for y in old_kot_object.kot_list :
                            product_id = self.env['product.product'].search([('name','=',y['product_id'].name)])

                            if x[2]['product_id'] == product_id[0] :

                                sum_qty = sum_qty + int (y['item_qty'])


                    x[2]['qty'] = x[2]['qty'] - sum_qty
                    product_obj = self.env['product.product'].browse(x[2]['product_id'])
                    name=product_obj.name
                    product_nature=product_obj.product_nature
                    menu_card_id = self.env['hotel.menucard'].search([('name','=',name)])
                    if(x[2]['qty']!=0):
                        o_line={
                             'product_id':menu_card_id[0],
                             'kot_order_list':kot_data,
                             'name':name,
                             'item_qty':x[2]['qty'],
                             'item_rate':x[2]['price_unit'],
                             'product_qty':kot_quantities,
                             'product_nature':product_nature,
                            }

                        self.env['hotel.restaurant.order.list'].create(o_line)

            else:
                shop_name=vals['shop_name']
                order_no = vals['orderno']
                reservation_no = vals['resno']
                rooms=vals['room_no'][0]
                waiter=vals['w_name']
                date=vals['kot_date']
                kot_data=False
                shop_id=self.env['sale.shop'].search([('name','=',shop_name)])[0]
                product_nature=None
                create_kot = False
                for k in vals['kot'] :
                    old_product_id=k[2]['product_id'];
                    product_obj=self.env['product.product'].browse(k[2]['product_id'])
                    product_name=product_obj.name
                    product_nature=product_obj.product_nature
                    max_qty=0
                    kot_quantity=k[2]['qty']

                    product_obj=self.env['product.product'].browse(k[2]['product_id'])
                    menu_card_id = self.env['hotel.menucard'].search([('name','=',product_obj.name)])
                    old_kot_id = self.env['hotel.restaurant.kitchen.order.tickets'].search([('resno','=',reservation_no)])
                    if not old_kot_id:
                        create_kot = True
                    for test in self.env['hotel.restaurant.order.list'].search([('product_id','=',menu_card_id[0]), ('resno','=',reservation_no)]):
                                prod_name = self.env['hotel.restaurant.order.list'].browse(test)
                                if max_qty <= prod_name.product_qty:
                                    max_qty = prod_name.product_qty

                    if max_qty!=kot_quantity:
                        create_kot = True
                old_kot_id = self.env['hotel.restaurant.kitchen.order.tickets'].search([('resno','=',reservation_no)])
                old_kot_length = len(old_kot_id)
                if create_kot:
                    kot_data=self.env['hotel.restaurant.kitchen.order.tickets'].create({
                                                                                            'orderno':order_no,
                                                                                            'resno':reservation_no,
                                                                                            'kot_date':date,
                                                                                            'w_name':waiter,
                                                                                            'shop_id':shop_id,
                                                                                            'product_nature':product_nature,
                                                                                            'room_no':rooms,
                                                                                            })
                for x in vals['kot']:
                    kot_quantities=x[2]['qty']
                    sum_qty = 0
                    i=0
                    for i in range(0,old_kot_length) :
                       kot_no_id = old_kot_id[i]
                       old_kot_object = self.env['hotel.restaurant.kitchen.order.tickets'].browse(kot_no_id)
                       
                       for y in old_kot_object.kot_list :
                            product_id = self.env['product.product'].search([('name','=',y['product_id'].name)])
                            
                            if x[2]['product_id'] == product_id[0] :
                                
                                sum_qty = sum_qty + int (y['item_qty'])
                  
                    x[2]['qty'] = x[2]['qty'] - sum_qty
                    product_obj = self.env['product.product'].browse(x[2]['product_id'])
                    name = product_obj.name
                    product_nature = product_obj.product_nature
                    menu_card_id = self.env['hotel.menucard'].search([('name','=',name)])
                    if(x[2]['qty']!=0):
                        o_line={
                             'product_id':menu_card_id[0],
                             'kot_order_list':kot_data,
                             'name':name,
                             'item_qty':x[2]['qty'],
                             'item_rate':x[2]['price_unit'],
                             'product_qty':kot_quantities,
                             'product_nature':product_nature,
                            }

                        self.env['hotel.restaurant.order.list'].create(o_line)

        if vals['bot']:
            if 'tableno' in vals:
                shop_name=vals['shop_name']
                ordernobot = vals['ordernobot']
                reservation_no = vals['resno']
                table=vals['tableno']
                waiter=vals['w_name']
                date=vals['kot_date']
                bot_data=False;
                create_bot = False;

                shop_id = self.env['sale.shop'].search([('name','=',shop_name)])[0]
                for k in vals['bot'] :
                    old_product_id = k[2]['product_id'];
                    product_obj = self.env['product.product'].browse(k[2]['product_id'])
                    product_name = product_obj.name
                    product_nature = product_obj.product_nature
                    kot_quantity = k[2]['qty']
                    max_qty = 0

                    product_obj=self.env['product.product'].browse(k[2]['product_id'])
                    menu_card_id = self.env['hotel.menucard'].search([('name','=',product_obj.name)])
                    old_kot_id = self.env['hotel.restaurant.kitchen.order.tickets'].search([('resno','=',reservation_no)])
                    if not old_kot_id:
                        create_bot = True
                    for test in self.env['hotel.restaurant.order.list'].search([('product_id','=',menu_card_id[0]), ('resno','=',reservation_no)]):
                                prod_name = self.env['hotel.restaurant.order.list'].browse(test)
                                if max_qty <= prod_name.product_qty:
                                    max_qty = prod_name.product_qty

                    if max_qty!=kot_quantity:
                        create_bot = True
                old_kot_id = self.env['hotel.restaurant.kitchen.order.tickets'].search([('resno','=',reservation_no)])
                old_kot_length = len(old_kot_id)
                if create_bot:
                    bot_data=self.env['hotel.restaurant.kitchen.order.tickets'].create({
                                                                                        'resno':reservation_no,
                                                                                        'kot_date':date,
                                                                                        'w_name':waiter,
                                                                                        'shop_id':shop_id,
                                                                                        'product_nature':product_nature,
                                                                                         })
                   

                    table_id = self.env['hotel.restaurant.tables'].search([('name','=',table)])
                    for tab_id in table_id:
                        self._cr.execute('insert into temp_table3 (name,table_no) values (%s,%s)',(tab_id,bot_data))
                for x in vals['bot']:
                        kot_quantities=x[2]['qty']
                        sum_qty = 0
                        i=0
                        for i in range(0,old_kot_length) :
                           kot_no_id = old_kot_id[i]
                           old_kot_object = self.env['hotel.restaurant.kitchen.order.tickets'].browse(kot_no_id)
                           for y in old_kot_object.kot_list :
                                product_id = self.env['product.product'].search([('name','=',y['product_id'].name)])
                                if x[2]['product_id'] == product_id[0] :
                                    sum_qty = sum_qty + int (y['item_qty'])

                        x[2]['qty'] = x[2]['qty'] - sum_qty
                        product_obj=self.env['product.product'].browse(x[2]['product_id'])
                        name=product_obj.name
                        product_nature = product_obj.product_nature
                        menu_card_id = self.env['hotel.menucard'].search([('name','=',name)])
                        if(x[2]['qty']!=0):
                            o_line={
                                 'product_id':menu_card_id[0],
                                 'kot_order_list':bot_data,
                                 'name':name,
                                 'item_qty':x[2]['qty'],
                                 'item_rate':x[2]['price_unit'],
                                 'product_qty':kot_quantities,
                                 'product_nature':product_nature,
                                }

                            self.env['hotel.restaurant.order.list'].create(o_line)

            else:
                shop_name=vals['shop_name']
                ordernobot = vals['ordernobot']
                reservation_no = vals['resno']
                rooms=vals['room_no'][0]
                waiter=vals['w_name']
                date=vals['kot_date']
                bot_data=False;
                create_bot = False;
                shop_id = self.env['sale.shop'].search([('name','=',shop_name)])[0]
                for k in vals['bot'] :
                    old_product_id=k[2]['product_id'];
                    product_obj=self.env['product.product'].browse(k[2]['product_id'])
                    product_name=product_obj.name
                    product_nature=product_obj.product_nature
                    kot_quantity=k[2]['qty']
                    max_qty= 0
                    product_obj = self.env['product.product'].browse(k[2]['product_id'])
                    menu_card_id = self.env['hotel.menucard'].search([('name','=',product_obj.name)])
                    old_kot_id = self.env['hotel.restaurant.kitchen.order.tickets'].search([('resno','=',reservation_no)])
                    if not old_kot_id:
                        create_bot = True
                    for test in self.env['hotel.restaurant.order.list'].search([('product_id','=',menu_card_id[0]), ('resno','=',reservation_no)]):
                                prod_name = self.env['hotel.restaurant.order.list'].browse(test)
                                if max_qty <= prod_name.product_qty:
                                    max_qty = prod_name.product_qty

                    if max_qty!=kot_quantity:
                        create_bot = True
                old_kot_id = self.env['hotel.restaurant.kitchen.order.tickets'].search([('resno','=',reservation_no)])
                old_kot_length = len(old_kot_id)

                if create_bot:
                    bot_data=self.env['hotel.restaurant.kitchen.order.tickets'].create({
                                                                                        'resno':reservation_no,
                                                                                        'kot_date':date,
                                                                                        'w_name':waiter,
                                                                                        'shop_id':shop_id,
                                                                                        'product_nature':product_nature,
                                                                                        'room_no':rooms,
                                                                                         })
                for x in vals['bot']:
                        kot_quantities=x[2]['qty']
                        sum_qty = 0
                        i=0
                        for i in range(0,old_kot_length) :
                           kot_no_id = old_kot_id[i]
                           old_kot_object = self.env['hotel.restaurant.kitchen.order.tickets'].browse(kot_no_id)
                           for y in old_kot_object.kot_list :
                                product_id = self.env['product.product'].search([('name','=',y['product_id'].name)])
                                if x[2]['product_id'] == product_id[0] :
                                    sum_qty = sum_qty + int (y['item_qty'])
                        x[2]['qty'] = x[2]['qty'] - sum_qty
                        product_obj = self.env['product.product'].browse(x[2]['product_id'])
                        name=product_obj.name
                        product_nature=product_obj.product_nature
                        menu_card_id = self.env['hotel.menucard'].search([('name','=',name)])
                        if(x[2]['qty']!=0):
                            o_line={
                                 'product_id':menu_card_id[0],
                                 'kot_order_list':bot_data,
                                 'name':name,
                                 'item_qty':x[2]['qty'],
                                 'item_rate':x[2]['price_unit'],
                                 'product_qty':kot_quantities,
                                 'product_nature':product_nature,
                                }

                            self.env['hotel.restaurant.order.list'].create(o_line)
class POSPayment(models.Model):
    _inherit = "pos.payment"

    def name_get(self):
        res = []
        for payment in self:
            if payment.name:
                res.append((payment.id, '%s %s' % (payment.name, formatLang(self.env, payment.amount, currency_obj=payment.currency_id))))
            else:
                res.append((payment.id, payment.payment_method_id.name))
        return res
    
class PosOrder(models.Model):
    _inherit="pos.order"
    
    total_advance = fields.Float(string='Total Advance')
    remaining_amt = fields.Float(string='Total Remaining')

    payment_status = fields.Selection([
        ('paid', 'Paid'),
        ('payatcheckout', 'Pay at Checkout'),
    ], string='Payment Status', compute='_compute_payment_status', store=True)

    @api.depends('payment_ids')
    def _compute_payment_status(self):
        for order in self:
            if order.payment_ids:
                order.payment_status = 'paid'
            else:
                order.payment_status = 'payatcheckout'
                order.is_payatcheckout = True



    @api.model_create_multi
    def create(self, vals):
        # First, create the pos.order instance
        order = super(PosOrder, self).create(vals)
        # Loop over the order lines
        for order_line in order.lines:
            # Check if the product name is "breakfast"
            if order.folio_line_id.name == 'All Meals' or order.folio_line_id.name == 'Breakfast' or order.folio_line_id.name == 'Breakfast And Dinner':
                # Set the price to 0 if the product name is breakfast
                order_line.write({
                    'price_subtotal': 0,
                    'price_unit': 0,
                    'price_subtotal_incl': 0
                })
        return order

   
    

    def create_reverse_entry(self, original_line, debit=True):
    
        if debit:
            amount = original_line.debit  # amount will be the debit of the original line
            new_line = {
            'account_id': original_line.account_id.id,
            'name': original_line.name+"b",
            'debit': 0.0,
            'credit': amount,
            'tax_ids': original_line.tax_ids.ids,
            'partner_id': original_line.partner_id.id,
        }
        else:
            amount = original_line.credit  # amount will be the credit of the original line
            new_line = {
            'account_id': original_line.account_id.id,
            'name': original_line.name+'v',
            'debit': amount,
            'credit': 0.0,
            'tax_ids': original_line.tax_ids.ids,
            'partner_id': original_line.partner_id.id,
        }

        self.session_move_id.write({'line_ids': [(0, 0, new_line)]})        
           
    def update_folio_history(self):
        pass
        return True

    def write(self, vals):
        # If the write operation is changing the order lines, process accordingly
        if ('amount_total' in vals and vals['amount_total'] == 0) or \
           ('amount_tax' in vals and vals['amount_tax'] == 0):
            return super(PosOrder, self).write(vals)
        for order in self:
            # Loop over the order lines to check if the product is "breakfast"
            if order:
                for order_line in order.lines:
                    if  order.folio_line_id.name == 'All Meals' or order.folio_line_id.name == 'Breakfast' or order.folio_line_id.name == 'Breakfast And Dinner':
                        # Set the price to 0 if the product name is "breakfast"
                        order_line.write({
                            'price_subtotal': 0,
                            'price_unit': 0,
                            'price_subtotal_incl': 0
                        })
                        pos_order = self.env["pos.order"].search([("id","=",order_line.order_id.id)])
                        vals['amount_total'] = 0
                        vals['amount_tax'] = 0
                        vals['state'] = 'done'
        # Call the original write method
        return super(PosOrder, self).write(vals)


    def action_pos_order_paid(self):
        self.ensure_one()
        for rec in self:
            for payment in rec.payment_ids:
                if payment.name in ['return', 'retour']:
                    payment.unlink()
                    #self.write({'state': 'payatcheckout','is_payatcheckout':True})
                    #payment.unlink()
                elif payment.name is False:
                    self.write({'state': 'paid'})
                   

        # TODO: add support for mix of cash and non-cash payments when both cash_rounding and only_round_cash_method are True
        if not self.config_id.cash_rounding \
           or self.config_id.only_round_cash_method \
           and not any(p.payment_method_id.is_cash_count for p in self.payment_ids):
            total = self.amount_total
        else:
            total = float_round(self.amount_total, precision_rounding=self.config_id.rounding_method.rounding, rounding_method=self.config_id.rounding_method.rounding_method)

        isPaid = float_is_zero(total - self.amount_paid, precision_rounding=self.currency_id.rounding)

        if not isPaid and not self.config_id.cash_rounding:
            if not self.is_payatcheckout:
                self.write({'state': 'payatcheckout','is_payatcheckout':True})
        elif not isPaid and self.config_id.cash_rounding:
            currency = self.currency_id
            if self.config_id.rounding_method.rounding_method == "HALF-UP":
                maxDiff = currency.round(self.config_id.rounding_method.rounding / 2)
            else:
                maxDiff = currency.round(self.config_id.rounding_method.rounding)

            diff = currency.round(self.amount_total - self.amount_paid)
            if not abs(diff) <= maxDiff:
                raise UserError(_("Order %s is not fully paid.", self.name))
        if not self.is_payatcheckout:
            self.write({'state': 'paid'})
        return True

   


    
    def create_pos_order_invoice(self):
        
        existing_hotel_order = self.env['hotel.folio'].search([('name','=',self.folio_ids.name)])
        current_folio = self.folio_ids.name
        hotel_folio = self.env['hotel.folio'].search([('name', '=', current_folio)])
        existing_pos_order = self.env['hotel.folio'].search([('pos_order_ids','=',self.id)])
        
        if not existing_pos_order:
            self.action_pos_order_invoice()
            
        elif not existing_hotel_order.invoice_ids.id:
            return {
                'name': 'Invoice',
                'type': 'ir.actions.act_window',
                'res_model': 'hotel.invoice.creation.popup',
                'view_mode': 'form',
                'view_id': self.env.ref('hotel_restaurant_pos.view_invoice_creation').id,
                'target': 'new',
                    
            }
            
        elif existing_pos_order and hotel_folio:
            
            raise UserError('You cannot create an invoice as you have already created one from the folio.')

    def action_pos_order_invoice(self):
        if len(self.company_id) > 1:
            raise UserError(_("You cannot invoice orders belonging to different companies."))
        self.write({'to_invoice': True})
        if self.company_id.anglo_saxon_accounting and self.session_id.update_stock_at_closing and self.session_id.state != 'closed':
            if self.folio_line_id.name != 'All Meals' or self.folio_line_id.name != 'Breakfast' or self.folio_line_id.name != 'Breakfast And Dinner':
                vvv = self._create_order_picking()
                
                

        move_vals = self._prepare_invoice_vals()
        ccc = self._create_invoice(move_vals) 
                

    def _should_create_picking_real_time(self):
        if self.folio_line_id.name == 'All Meals' or self.folio_line_id.name == 'Breakfast' or self.folio_line_id.name == 'Breakfast And Dinner':
            return not self.session_id.update_stock_at_closing or (self.company_id.anglo_saxon_accounting)
        else:
            return not self.session_id.update_stock_at_closing or (self.company_id.anglo_saxon_accounting and self.to_invoice)



    @api.model
    def _order_fields(self, ui_order):
        pos_order_obj = super(PosOrder,self)._order_fields(ui_order)
        pos_order_obj.update({
                              'folio_line_id':ui_order.get('folio_line_id'),
                              'folio_ids':ui_order.get('folio_ids'),
                              });
        return pos_order_obj


    table_ids = fields.Many2many('hotel.restaurant.tables','pos_book_tables','table_no','name','Table number')
    state = fields.Selection(selection_add=[('draft', 'Draft'),
                ('credit', 'Credit Sale'),
               ('cancel', 'Cancelled'),
               ('payatcheckout','Pay At Checkout'),
               ('paid', 'Paid'),
               ('done', 'Posted'),
               ('invoiced', 'Invoiced') ,],
              string='Status', readonly=True)

    folio_line_id = fields.Many2one('hotel_folio.line','Link to Room')
    folio_ids = fields.Many2one('hotel.folio','Link to Folio')
    credit_sales = fields.Char('creditsales')
    waiter_name = fields.Char('Waiter Name')
    is_payatcheckout = fields.Boolean(default=False)

    def action_paid(self):

        for order in self.env['pos.order'].browse():
            if order.credit_sales=='True':
                self.write({'state': 'paid'})
            else:
                self.create_picking()
                self.write({'state': 'paid'})

        return True

    def action_credit(self):
        return self.write({'state': 'credit'})

    def create_picking(self):
        picking_obj = request.env['stock.picking.out']
        partner_obj = self.env['res.partner']
        move_obj = self.env['stock.move']

        for order in self.browse():
            if not order.state in ['draft','credit']:
                continue
            addr = order.partner_id and partner_obj.address_get([order.partner_id.id], ['delivery']) or {}
            picking_id = picking_obj.create({
                'origin': order.name,
                'partner_id': addr.get('delivery',False),
                'type': 'out',
                'company_id': order.company_id.id,
                'move_type': 'direct',
                'invoice_state': 'none',
                'auto_picking': True,
            })
            self.write({'picking_id': picking_id})
            location_id = order.shop_id.warehouse_id.lot_stock_id.id
            output_id = order.shop_id.warehouse_id.lot_output_id.id

            for line in order.lines:
                if line.product_id and line.product_id.type == 'service':
                    continue
                if line.qty < 0:
                    location_id, output_id = output_id, location_id

                move_obj.create({
                    'name': line.name,
                    'product_uom': line.product_id.uom_id.id,
                    'product_uos': line.product_id.uom_id.id,
                    'picking_id': picking_id,
                    'product_id': line.product_id.id,
                    'product_uos_qty': abs(line.qty),
                    'product_qty': abs(line.qty),
                    'tracking_id': False,
                    'state': 'draft',
                    'location_id': location_id,
                    'location_dest_id': output_id,
                })
                if line.qty < 0:
                    location_id, output_id = output_id, location_id

            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate('stock.picking', picking_id, 'button_confirm')
            picking_obj.force_assign([picking_id])
        return True


class PosSession(models.Model):
        _inherit="pos.session"
        _description="inherited pos.session class"


        def get_session_orders(self):
            return self.order_ids

        def _validate_session(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
            bank_payment_method_diffs = bank_payment_method_diffs or {}
            draft_orders = self.get_session_orders().filtered(lambda order: order.state == 'payatcheckout')
            if draft_orders:
                for draft_o in draft_orders:
                    continue
            self.ensure_one()
            data = {}
            sudo = self.env.user.has_group('point_of_sale.group_pos_user')
            if self.get_session_orders().filtered(lambda o: o.state != 'payatcheckout' and o.state != 'cancel') or self.sudo().statement_line_ids:
                self.cash_real_transaction = sum(self.sudo().statement_line_ids.mapped('amount'))
                if self.state == 'closed':
                    raise UserError(_('This session is already closed.'))
                self._check_if_no_draft_orders()
                self._check_invoices_are_posted()
                cash_difference_before_statements = self.cash_register_difference
                if self.update_stock_at_closing:
                    self._create_picking_at_end_of_session()
                    self._get_closed_orders().filtered(lambda o: not o.is_total_cost_computed)._compute_total_cost_at_session_closing(self.picking_ids.move_ids)
                try:
                    with self.env.cr.savepoint():
                        data = self.with_company(self.company_id).with_context(check_move_validity=False, skip_invoice_sync=True)._create_account_move(balancing_account, amount_to_balance, bank_payment_method_diffs)
                except AccessError as e:
                    if sudo:
                        data = self.sudo().with_company(self.company_id).with_context(check_move_validity=False, skip_invoice_sync=True)._create_account_move(balancing_account, amount_to_balance, bank_payment_method_diffs)
                    else:
                        raise e

                balance = sum(self.move_id.line_ids.mapped('balance'))
                try:
                    with self.move_id._check_balanced({'records': self.move_id.sudo()}):
                        pass
                except UserError:
                  
                    self.env.cr.rollback()
                    return self._close_session_action(balance)

                self.sudo()._post_statement_difference(cash_difference_before_statements)
                if self.move_id.line_ids:
                    self.move_id.sudo().with_company(self.company_id)._post()
                    # Set the uninvoiced orders' state to 'done'
                    self.env['pos.order'].search([('session_id', '=', self.id), ('state', '=', 'paid')]).write({'state': 'done'})
                else:
                    self.move_id.sudo().unlink()
                #self.sudo().with_company(self.company_id)._reconcile_account_move_lines(data)
            else:
                self.sudo()._post_statement_difference(self.cash_register_difference)

            if self.config_id.order_edit_tracking:
                edited_orders = self.get_session_orders().filtered(lambda o: o.is_edited)
                if len(edited_orders) > 0:
                    body = _("Edited order(s) during the session:%s",
                        Markup("<br/><ul>%s</ul>") % Markup().join(Markup("<li>%s</li>") % order._get_html_link() for order in edited_orders)
                    )
                    self.message_post(body=body)

            # Make sure to trigger reordering rules
            self.picking_ids.move_ids.sudo()._trigger_scheduler()

            self.write({'state': 'closed'})
            return True
   
        def _accumulate_amounts(self, data):
            AccountTax = self.env['account.tax']
            amounts = lambda: {'amount': 0.0, 'amount_converted': 0.0}
            tax_amounts = lambda: {'amount': 0.0, 'amount_converted': 0.0, 'base_amount': 0.0, 'base_amount_converted': 0.0}
            split_receivables_bank = defaultdict(amounts)
            split_receivables_cash = defaultdict(amounts)
            split_receivables_pay_later = defaultdict(amounts)
            combine_receivables_bank = defaultdict(amounts)
            combine_receivables_cash = defaultdict(amounts)
            combine_receivables_pay_later = defaultdict(amounts)
            combine_invoice_receivables = defaultdict(amounts)
            split_invoice_receivables = defaultdict(amounts)
            sales = defaultdict(amounts)
            taxes = defaultdict(tax_amounts)
            stock_expense = defaultdict(amounts)
            stock_return = defaultdict(amounts)
            stock_output = defaultdict(amounts)
            rounding_difference = {'amount': 0.0, 'amount_converted': 0.0}
            # Track the receivable lines of the order's invoice payment moves for reconciliation
            # These receivable lines are reconciled to the corresponding invoice receivable lines
            # of this session's move_id.
            combine_inv_payment_receivable_lines = defaultdict(lambda: self.env['account.move.line'])
            split_inv_payment_receivable_lines = defaultdict(lambda: self.env['account.move.line'])
            pos_receivable_account = self.company_id.account_default_pos_receivable_account_id
            currency_rounding = self.currency_id.rounding
            closed_orders = self._get_closed_orders()
            for order in closed_orders:
                if order.state == 'payatcheckout':
                    continue
                order_is_invoiced = order.is_invoiced
                for payment in order.payment_ids:
                    amount = payment.amount
                    if float_is_zero(amount, precision_rounding=currency_rounding):
                        continue
                    date = payment.payment_date
                    payment_method = payment.payment_method_id
                    is_split_payment = payment.payment_method_id.split_transactions
                    payment_type = payment_method.type

               
                    if payment_type != 'pay_later':
                        if is_split_payment and payment_type == 'cash':
                            split_receivables_cash[payment] = self._update_amounts(split_receivables_cash[payment], {'amount': amount}, date)
                        elif not is_split_payment and payment_type == 'cash':
                            combine_receivables_cash[payment_method] = self._update_amounts(combine_receivables_cash[payment_method], {'amount': amount}, date)
                        elif is_split_payment and payment_type == 'bank':
                            split_receivables_bank[payment] = self._update_amounts(split_receivables_bank[payment], {'amount': amount}, date)
                        elif not is_split_payment and payment_type == 'bank':
                            combine_receivables_bank[payment_method] = self._update_amounts(combine_receivables_bank[payment_method], {'amount': amount}, date)

                        # Create the vals to create the pos receivables that will balance the pos receivables from invoice payment moves.
                        if order_is_invoiced:
                            if is_split_payment:
                                split_inv_payment_receivable_lines[payment] |= payment.account_move_id.line_ids.filtered(lambda line: line.account_id == pos_receivable_account)
                                split_invoice_receivables[payment] = self._update_amounts(split_invoice_receivables[payment], {'amount': payment.amount}, order.date_order)
                            else:
                                combine_inv_payment_receivable_lines[payment_method] |= payment.account_move_id.line_ids.filtered(lambda line: line.account_id == pos_receivable_account)
                                combine_invoice_receivables[payment_method] = self._update_amounts(combine_invoice_receivables[payment_method], {'amount': payment.amount}, order.date_order)

               
                    if payment_type == 'pay_later' and not order_is_invoiced:
                        if is_split_payment:
                            split_receivables_pay_later[payment] = self._update_amounts(split_receivables_pay_later[payment], {'amount': amount}, date)
                        elif not is_split_payment:
                            combine_receivables_pay_later[payment_method] = self._update_amounts(combine_receivables_pay_later[payment_method], {'amount': amount}, date)

                if not order_is_invoiced:
                    base_lines = order.with_context(linked_to_pos=True)._prepare_tax_base_line_values()
                    AccountTax._add_tax_details_in_base_lines(base_lines, order.company_id)
                    AccountTax._round_base_lines_tax_details(base_lines, order.company_id)
                    AccountTax._add_accounting_data_in_base_lines_tax_details(base_lines, order.company_id)
                    tax_results = AccountTax._prepare_tax_lines(base_lines, order.company_id)
                    total_amount_currency = 0.0
                    for base_line, to_update in tax_results['base_lines_to_update']:
                        # Combine sales/refund lines
                        sale_key = (
                        # account
                        base_line['account_id'].id,
                        # sign
                        -1 if base_line['is_refund'] else 1,
                        # for taxes
                        tuple(base_line['record'].tax_ids_after_fiscal_position.flatten_taxes_hierarchy().ids),
                        tuple(base_line['tax_tag_ids'].ids),
                        base_line['product_id'].id if self.config_id.is_closing_entry_by_product else False,
                    )
                        total_amount_currency += to_update['amount_currency']
                        sales[sale_key] = self._update_amounts(
                        sales[sale_key],
                        {
                            'amount': to_update['amount_currency'],
                            'amount_converted': to_update['balance'],
                        },
                        order.date_order,
                    )
                        if self.config_id.is_closing_entry_by_product:
                            sales[sale_key] = self._update_quantities(sales[sale_key], base_line['quantity'])

                    # Combine tax lines
                    for tax_line in tax_results['tax_lines_to_add']:
                        tax_key = (
                        tax_line['account_id'],
                        tax_line['tax_repartition_line_id'],
                        tuple(tax_line['tax_tag_ids'][0][2]),
                        order.id
                    )
                        total_amount_currency += tax_line['amount_currency']
                        taxes[tax_key] = self._update_amounts(
                        taxes[tax_key],
                        {
                            'amount': tax_line['amount_currency'],
                            'amount_converted': tax_line['balance'],
                            'base_amount': tax_line['tax_base_amount']
                        },
                        order.date_order,
                    )

                    if self.config_id.cash_rounding:
                        diff = order.amount_paid + total_amount_currency
                        rounding_difference = self._update_amounts(rounding_difference, {'amount': diff}, order.date_order)

                    # Increasing current partner's customer_rank
                    partners = (order.partner_id | order.partner_id.commercial_partner_id)
                    partners._increase_rank('customer_rank')

            if self.company_id.anglo_saxon_accounting:
                all_picking_ids = self.order_ids.filtered(lambda p: not p.is_invoiced and not p.shipping_date).picking_ids.ids + self.picking_ids.filtered(lambda p: not p.pos_order_id).ids
                if all_picking_ids:
                    # Combine stock lines
                    stock_move_sudo = self.env['stock.move'].sudo()
                    stock_moves = stock_move_sudo.search([
                    ('picking_id', 'in', all_picking_ids),
                    ('company_id.anglo_saxon_accounting', '=', True),
                    ('product_id.categ_id.property_valuation', '=', 'real_time'),
                    ('product_id.is_storable', '=', True),
                ])
                    for stock_moves_split in self.env.cr.split_for_in_conditions(stock_moves.ids):
                        stock_moves_batch = stock_move_sudo.browse(stock_moves_split)
                        candidates = stock_moves_batch\
                        .filtered(lambda m: not bool(m.origin_returned_move_id and sum(m.stock_valuation_layer_ids.mapped('quantity')) >= 0))\
                        .mapped('stock_valuation_layer_ids')

                        for move in stock_moves_batch.with_context(candidates_prefetch_ids=candidates._prefetch_ids):
                            exp_key = move.product_id._get_product_accounts()['expense']
                            out_key = move.product_id.categ_id.property_stock_account_output_categ_id
                            signed_product_qty = move.product_qty
                            if move._is_in():
                                signed_product_qty *= -1
                            amount = signed_product_qty * move.product_id._compute_average_price(0, move.quantity, move)
                            stock_expense[exp_key] = self._update_amounts(stock_expense[exp_key], {'amount': amount}, move.picking_id.date, force_company_currency=True)
                            if move._is_in():
                                stock_return[out_key] = self._update_amounts(stock_return[out_key], {'amount': amount}, move.picking_id.date, force_company_currency=True)
                            else:
                                stock_output[out_key] = self._update_amounts(stock_output[out_key], {'amount': amount}, move.picking_id.date, force_company_currency=True)
            MoveLine = self.env['account.move.line'].with_context(check_move_validity=False, skip_invoice_sync=True)

            data.update({
            'taxes':                               taxes,
            'sales':                               sales,
            'stock_expense':                       stock_expense,
            'split_receivables_bank':              split_receivables_bank,
            'combine_receivables_bank':            combine_receivables_bank,
            'split_receivables_cash':              split_receivables_cash,
            'combine_receivables_cash':            combine_receivables_cash,
            'combine_invoice_receivables':         combine_invoice_receivables,
            'split_receivables_pay_later':         split_receivables_pay_later,
            'combine_receivables_pay_later':       combine_receivables_pay_later,
            'stock_return':                        stock_return,
            'stock_output':                        stock_output,
            'combine_inv_payment_receivable_lines': combine_inv_payment_receivable_lines,
            'rounding_difference':                 rounding_difference,
            'MoveLine':                            MoveLine,
            'split_invoice_receivables': split_invoice_receivables,
            'split_inv_payment_receivable_lines': split_inv_payment_receivable_lines,
        })
            return data


        def _get_tax_vals(self, key, amount, amount_converted, base_amount_converted):
            account_id, repartition_line_id, tag_ids,order_id = key 
            tax_rep = self.env['account.tax.repartition.line'].browse(repartition_line_id)
            tax = tax_rep.tax_id
            return {
            'name': tax.name,
            'account_id': account_id,
            'move_id': self.move_id.id,
            'tax_base_amount': abs(base_amount_converted),
            'tax_repartition_line_id': repartition_line_id,
            'tax_tag_ids': [(6, 0, tag_ids)],
            'display_type': 'tax',
            'currency_id': self.currency_id.id,
            'amount_currency': amount,
            'balance': amount_converted,
        }

        def _create_bank_payment_moves(self, data):
            combine_receivables_bank = data.get('combine_receivables_bank')
            split_receivables_bank = data.get('split_receivables_bank')
            bank_payment_method_diffs = data.get('bank_payment_method_diffs')
            MoveLine = data.get('MoveLine')
            payment_method_to_receivable_lines = {}
            payment_to_receivable_lines = {}
            for payment_method, amounts in combine_receivables_bank.items():
                combine_receivable_line = MoveLine.create(self._get_combine_receivable_vals(payment_method, amounts['amount'], amounts['amount_converted']))
                payment_receivable_line = self._create_combine_account_payment(payment_method, amounts, diff_amount=bank_payment_method_diffs.get(payment_method.id) or 0)
                payment_method_to_receivable_lines[payment_method] = combine_receivable_line | payment_receivable_line

            for payment, amounts in split_receivables_bank.items():
                split_receivable_line = MoveLine.create(self._get_split_receivable_vals(payment, amounts['amount'], amounts['amount_converted']))
                payment_receivable_line = self._create_split_account_payment(payment, amounts)
                payment_to_receivable_lines[payment] = split_receivable_line | payment_receivable_line

            for bank_payment_method in self.payment_method_ids.filtered(lambda pm: pm.type == 'bank' and pm.split_transactions):
                self._create_diff_account_move_for_split_payment_method(bank_payment_method, bank_payment_method_diffs.get(bank_payment_method.id) or 0)

            data['payment_method_to_receivable_lines'] = payment_method_to_receivable_lines
            data['payment_to_receivable_lines'] = payment_to_receivable_lines
            return data

        def _reconcile_account_move_lines(self, data):
            # reconcile cash receivable lines
            split_cash_statement_lines = data.get('split_cash_statement_lines')
            combine_cash_statement_lines = data.get('combine_cash_statement_lines')
            split_cash_receivable_lines = data.get('split_cash_receivable_lines')
            combine_cash_receivable_lines = data.get('combine_cash_receivable_lines')
            combine_inv_payment_receivable_lines = data.get('combine_inv_payment_receivable_lines')
            split_inv_payment_receivable_lines = data.get('split_inv_payment_receivable_lines')
            combine_invoice_receivable_lines = data.get('combine_invoice_receivable_lines')
            split_invoice_receivable_lines = data.get('split_invoice_receivable_lines')
            stock_output_lines = data.get('stock_output_lines')
            payment_method_to_receivable_lines = data.get('payment_method_to_receivable_lines')
            payment_to_receivable_lines = data.get('payment_to_receivable_lines')


            all_lines = (
              split_cash_statement_lines
            | combine_cash_statement_lines
            | split_cash_receivable_lines
            | combine_cash_receivable_lines
        )
            all_lines.filtered(lambda line: line.move_id.state != 'posted').move_id._post(soft=False)

            accounts = all_lines.mapped('account_id')
            lines_by_account = [all_lines.filtered(lambda l: l.account_id == account and not l.reconciled) for account in accounts if account.reconcile]
            for lines in lines_by_account:
                lines.with_context(no_cash_basis=True).reconcile()


            for payment_method, lines in payment_method_to_receivable_lines.items():
                receivable_account = self._get_receivable_account(payment_method)
                if receivable_account.reconcile:
                    lines.filtered(lambda line: not line.reconciled).with_context(no_cash_basis=True).reconcile()

            for payment, lines in payment_to_receivable_lines.items():
                if payment.partner_id.property_account_receivable_id.reconcile:
                    lines.filtered(lambda line: not line.reconciled).with_context(no_cash_basis=True).reconcile()

            # Reconcile invoice payments' receivable lines. But we only do when the account is reconcilable.
            # Though `account_default_pos_receivable_account_id` should be of type receivable, there is currently
            # no constraint for it. Therefore, it is possible to put set a non-reconcilable account to it.
            if self.company_id.account_default_pos_receivable_account_id.reconcile:
                for payment_method in combine_inv_payment_receivable_lines:
                    lines = combine_inv_payment_receivable_lines[payment_method] | combine_invoice_receivable_lines.get(payment_method, self.env['account.move.line'])
                    lines.filtered(lambda line: not line.reconciled).with_context(no_cash_basis=True).reconcile()

                for payment in split_inv_payment_receivable_lines:
                    lines = split_inv_payment_receivable_lines[payment] | split_invoice_receivable_lines.get(payment, self.env['account.move.line'])
                    lines.filtered(lambda line: not line.reconciled).with_context(no_cash_basis=True).reconcile()

            # reconcile stock output lines
            pickings = self.picking_ids.filtered(lambda p: not p.pos_order_id)
            pickings |= self._get_closed_orders().filtered(lambda o: not o.is_invoiced).mapped('picking_ids')
            stock_moves = self.env['stock.move'].search([('picking_id', 'in', pickings.ids)])
            stock_account_move_lines = self.env['account.move'].search([('stock_move_id', 'in', stock_moves.ids)]).mapped('line_ids')
            for account_id in stock_output_lines:
                ( stock_output_lines[account_id]
                | stock_account_move_lines.filtered(lambda aml: aml.account_id == account_id)
                ).filtered(lambda aml: not aml.reconciled).with_context(no_cash_basis=True).reconcile()
            return data

        def _pos_ui_models_to_load(self):
            result = super()._pos_ui_models_to_load()
            result.append('hotel.folio')
            result.append('hotel.room.booking.history')
            result.append('sale.shop')
            result.append('hotel.restaurant.tables')
            result.append('hotel.restaurant.kitchen.order.tickets')
            result.append('hotel.restaurant.reservation')
            result.append('hotel.reservation')
            result.append('hotel_folio.line')
            return result

        def _loader_params_hotel_folio(self):
            return {
                'search_params': {
                    # 'domain': [('state', '=', 'draft')],
                    'fields': ['id', 'name', 'reservation_id', 'state', 'room_lines', 'order_id', 'partner_id'],
                },
            }
        def _get_pos_ui_hotel_folio(self, params):
            return self.env['hotel.folio'].search_read(**params['search_params'])
        def _loader_params_hotel_room_booking_history(self):
            current_date = datetime.datetime.now()
            current_str_date = str(current_date.year) + '-' + str(current_date.month) + '-' + str(current_date.day)
            return {
                'search_params': {
                    'domain': [[str('check_in_date'), '<=', current_str_date], [str('check_out_date'), '>=', current_str_date]],
                    'fields': ['partner_id', 'history_id', 'id', 'name', 'check_in_date', 'check_out_date', 'booking_id'],
                },
            }
        def _get_pos_ui_hotel_room_booking_history(self, params):
            return self.env['hotel.room.booking.history'].search_read(**params['search_params'])
        def _loader_params_sale_shop(self):
            config_id = self.env['pos.config'].search([('id','=',self.config_id.id)])
            if config_id:
                shop_id = self.env['sale.shop'].search([('company_id', '=', config_id.shop_id.id)])

            else:
                raise UserError("Please Attach the Shop ID in Pos Configuration")
            return {
                'search_params': {
                    'domain': [['id', 'in', shop_id.ids]],
                    'fields': ['name', 'id', 'shop_img'],
                },
            }
        def _get_pos_ui_sale_shop(self, params):
            return self.env['sale.shop'].search_read(**params['search_params'])
        def _loader_params_hotel_restaurant_tables(self):
            config_id = self.env['pos.config'].search([('id', '=', self.config_id.id)])
            if config_id:
                shop_id = self.env['sale.shop'].search([('company_id', '=', config_id.shop_id.id)])
            else:
                raise UserError("Please Attach the Shop ID in Pos Configuration")
            return {
                'search_params': {
                    'domain': [['state', '=', 'confirmed'], ['shop_id', 'in', shop_id.ids], ['avl_state', '=', 'available']],
                    'fields': ['id', 'name', 'shop_id', 'state', 'avl_state'],
                },
            }
        def _get_pos_ui_hotel_restaurant_tables(self, params):
            return self.env['hotel.restaurant.tables'].search_read(**params['search_params'])
        def _loader_params_hotel_restaurant_kitchen_order_tickets(self):
            return {
                'search_params': {
                    'fields': ['orderno', 'resno'],
                },
            }
        def _get_pos_ui_hotel_restaurant_kitchen_order_tickets(self, params):
            return self.env['hotel.restaurant.kitchen.order.tickets'].search_read(**params['search_params'])
        def _loader_params_hotel_restaurant_reservation(self):
            return {
                'search_params': {
                    'domain': [['state', 'in', ['draft', 'confirm']]],
                    'fields': ['name', 'start_date', 'end_date', 'tableno', 'cname'],
                },
            }
        def _get_pos_ui_hotel_restaurant_reservation(self, params):
            return self.env['hotel.restaurant.reservation'].search_read(**params['search_params'])
        def _loader_params_hotel_reservation(self):
            return {
                'search_params': {
                    'domain': [['state', 'in', ['confirm']]],
                    'fields': ['id', 'name', 'folio_id'],
                },
            }
        def _get_pos_ui_hotel_reservation(self, params):
            return self.env['hotel.reservation'].search_read(**params['search_params'])
        def _loader_params_hotel_folio_line(self):
            return {
                'search_params': {
                    'fields': ['id', 'folio_id', 'order_line_id', 'checkin_date', 'checkout_date', 'categ_id'],
                },
            }
        def _get_pos_ui_hotel_folio_line(self, params):
            return self.env['hotel_folio.line'].search_read(**params['search_params'])

        def _confirm_orders(self):
                for session in self:
                    order_ids = [order.id for order in session.order_ids
                                 if order.state == 'paid']
                    move_id = self.env['account.move'].create({'ref' : session.name, 'journal_id' : session.config_id.journal_id.id, })
                    if order_ids:
                        for order in order_ids:
                            order._create_account_move_line(session, move_id)
                    for order in session.order_ids:
                        if order.state not in ('paid', 'invoiced','draft'):
                            raise UserError(_("You cannot confirm all orders of this session, because they have not the 'paid' status."))
                        else:
                            order.action_pos_order_done(session, move_id)

                return True

        def close_session(self):
            # Call the original close method
            for order in self.order_ids:
                # Prepare the lines for the journal entry
                journal_entry_lines = []
                total_sales = 0
                total_tax = 0

                for line in order.lines:
                    # Get the product, quantity, and price unit for the line
                    product = line.product_id
                    qty = line.qty
                    price_unit = line.price_unit

                    # Calculate total sales for the product line
                    line_sales = price_unit * qty
                    total_sales += line_sales

                    # Initialize tax amount for the product
                    line_tax = 0

                    # Loop through the product's associated taxes (could be multiple taxes)
                    for tax in product.taxes_id:
                        # Calculate the tax for this specific tax rate
                        tax_rate = tax.amount / 100  # Convert percentage to decimal
                        line_tax += line_sales * tax_rate  # Tax calculation for this line
                        total_tax += line_sales * tax_rate  # Sum the total tax
                    income_account = product.product_tmpl_id.get_product_accounts().get('income_account', False)
                    # Prepare the journal entry lines for the product sale
                    journal_entry_lines.append((0, 0, {
                    'account_id': income_account,
                    'debit': line_sales,
                    'credit': 0.0,
                    'name': product.name,
                }))
                
                    # Prepare the journal entry lines for the product tax
                    for tax in product.taxes_id:
                        journal_entry_lines.append((0, 0, {
                        'account_id': income_account,
                        'debit': 0.0,
                        'credit': line_sales * (tax.amount / 100),  # Credit the tax amount
                        'name': f"Tax for {product.name} ({tax.name})",
                    }))

                # Create the journal entry for the order
                journal_entry = self.env['account.move'].create({
                'journal_id': order.session_id.config_id.journal_id.id,
                'date': fields.Date.today(),
                'line_ids': journal_entry_lines,
                'ref': order.name,
                'invoice_origin': order.name,
                })

                # Post the journal entry                

        def create_dynamic_journal_entries(self, session):
   
            sales_by_tax = {}
            receivable_amount = 0
            difference_amount = 0

            # Loop through the POS orders and compute totals for sales and tax dynamically
            for order in session.order_ids:
                for line in order.lines:
                    # Process all taxes dynamically
                    for tax in line.tax_ids:
                        tax_rate = tax.amount  # Get the tax rate dynamically
                        if tax.tax_group_id:  # Check if the tax is linked to a tax group
                            tax_account = tax.tax_group_id.tax_payable_account_id  # Correctly fetch the tax account
                        else:
                            tax_account = tax.account_collected  
                        if tax_rate not in sales_by_tax:
                            sales_by_tax[tax_rate] = {'sales': 0, 'tax': 0, 'tax_account': tax_account.id}

                        # Accumulate sales and tax for each rate
                        sales_by_tax[tax_rate]['sales'] += line.price_subtotal
                        sales_by_tax[tax_rate]['tax'] += line.price_subtotal * (tax_rate / 100)

                # Accumulate receivable amounts and differences
                receivable_amount += order.amount_total
                difference_amount += order.amount_total - order.amount_paid  # Compute the difference

            # Prepare journal entry for the session
            journal_entry_vals = {
        'ref': f'POSS//04/0053',
        'date': datetime.datetime.now(),
        'journal_id': session.config_id.journal_id.id,  # POS journal
        'line_ids': []
    }

            # Dynamically fetch sales account from product category (or session configuration)
            sales_account = self.env['account.account'].search([('code', '=', '400000')], limit=1)  # Default or from configuration

            # Dynamically fetch receivable account from the session configuration (or default)
            receivable_account = self.env['account.account'].search([('code', '=', '101300')], limit=1)  # Default

            # Dynamically fetch difference account from session configuration (or default)
            difference_account = self.env['account.account'].search([('code', '=', '101300')], limit=1)  # Default

            # Add dynamic tax and sales lines based on computed totals
            for tax_rate, amounts in sales_by_tax.items():
                # Dynamically fetch tax account (from the tax linked to the product)
                tax_account_id = amounts['tax_account']  # Tax account dynamically fetched from the tax linked to the product

                # Create tax received line
                journal_entry_vals['line_ids'].append((0, 0, {
            'name': f'Tax Received {tax_rate}%',
            'account_id': tax_account_id,
            'debit': 0.0,
            'credit': amounts['tax'],
        }))
        
                # Create product sales line
                journal_entry_vals['line_ids'].append((0, 0, {
            'name': f'Product Sales {tax_rate}%',
            'account_id': sales_account.id,
            'debit': 0.0,
            'credit': amounts['sales'],
        }))

            # Add Account Receivable line
            journal_entry_vals['line_ids'].append((0, 0, {
        'name': f'Account Receivable (PoS) {session.name} - Cash',
        'account_id': receivable_account.id,
        'debit': receivable_amount,
        'credit': 0.0,
    }))

            # Add difference line at closing
            journal_entry_vals['line_ids'].append((0, 0, {
        'name': 'Difference at closing PoS session',
        'account_id': difference_account.id,
        'debit': difference_amount,
        'credit': 0.0,
    }))

            # Create and post the journal entry
            journal_entry = self.env['account.move'].create(journal_entry_vals)
            return journal_entry      


class HotelFolio(models.Model):

    _inherit = "hotel.folio"
    _description = "Hotel Folio Inherit Adding POS ORDER TABS"

    pos_order_ids = fields.One2many('pos.order','folio_ids','POS Orders',readonly=True)

class HotelMenucard(models.Model):

    def _get_image(self, name, args):
        result = dict.fromkeys(self._ids, False)
        for obj in self.browse():
            result[obj.id] = tools.image_get_resized_images(obj.image)
        return result

    def _set_image(self, name, value, args):
        return self.write({'image1': tools.image_resize_image_big(value)})

    _inherit = "hotel.menucard"
    _description = "Hotel Menucard Inherit Adding Point_of_sale category"
    pos_category = fields.Many2one('pos.category','Point Of Sale Category ',
                                        help="The Point of Sale Category this products belongs to. Those categories are used to group similar products and are specific to the Point of Sale.")


class HotelReservationOrder(models.Model):

    _inherit = 'hotel.reservation.order'

    pos_ref = fields.Char('POS Ref.')


class PosConfig(models.Model):
    _inherit = 'pos.config'

    shop_id = fields.Many2one('sale.shop', string='Hotel')
        
        
