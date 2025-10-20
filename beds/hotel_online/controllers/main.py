# -*- coding: utf-8 -*-
from odoo import http
from werkzeug.exceptions import Forbidden
from odoo.http import request
from datetime import datetime, timedelta
import logging
from odoo import tools
import time
import werkzeug.urls
from werkzeug.exceptions import NotFound
from dateutil.relativedelta import relativedelta
from odoo.addons.payment.controllers.post_processing import PaymentPostProcessing
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.sale.controllers import portal as sale_portal
from odoo.osv import expression
from odoo.tools.translate import _
from odoo import fields, models, api
import hashlib
import json
import ast
from odoo import SUPERUSER_ID
from odoo.exceptions import AccessError, MissingError, ValidationError, UserError
from builtins import int
from odoo.fields import Command
from odoo.addons.payment.controllers import portal as payment_portal
import pytz
import math
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.payment.controllers.post_processing import PaymentPostProcessing

utc_time = datetime.utcnow()
_logger = logging.getLogger(__name__)

from odoo import http
from odoo.http import request

class HotelRoomDashboardController(http.Controller):

    @http.route('/your_route', type='http', auth="user", csrf=False)
    def your_method(self):
        # Find the menu action by its XML ID
        action = request.env.ref('hotel_room_dashboard_view.hotel_compare_widget_client_actn')
        result = action.read()[0]
        return request.render('hotel_room_dashboard_view.hotel_dashboard_template', result)


class PaymentPortal(payment_portal.PaymentPortal):

    @http.route(
        '/shop/payment/transaction/<int:order_id>', type='json', auth='public', website=True
    )
    def shop_payment_transaction(self, order_id, access_token, **kwargs):
        try:
            if request.session.get('reservation_order_id'):
                order_sudo = self._document_check_access('hotel.reservation', order_id, access_token)
            elif request.session.get('sale_order_id'):
                order_sudo = self._document_check_access('sale.order', order_id, access_token)
        except MissingError as error:
            raise error
        except AccessError:
            raise ValidationError("The access token is invalid.")
        
        if order_sudo.state == "cancel":
            raise ValidationError(_("The order has been canceled."))
        if request.session.get('reservation_order_id'):
            if not order_sudo.online_advance_amount:
                if tools.float_compare(kwargs['amount'], order_sudo.total_cost1, precision_rounding=order_sudo.currency_id.rounding):
                    raise ValidationError(_("The cart has been updated. Please refresh the page."))
        elif request.session.get('sale_order_id'):
            if tools.float_compare(kwargs['amount'], order_sudo.amount_total, precision_rounding=order_sudo.currency_id.rounding):
                raise ValidationError(_("The cart has been updated. Please refresh the page."))

        if order_id:
            if request.session.get('reservation_order_id'):
                order = request.env['hotel.reservation'].sudo().search(
                    [('id', '=', int(order_id))])
                request.session['reservation_last_order_id'] = order.id
            elif request.session.get('sale_order_id'):
                order = request.env['sale.order'].sudo().search(
                    [('id', '=', int(order_id))])
                request.session['sale_last_order_id'] = order.id
        if request.session.get('reservation_order_id'):
            kwargs.update({
                'reference_prefix': order.name,  # Allow the reference to be computed based on the order
                'reservation_id': order_id,  # Include the SO to allow Subscriptions to tokenize the tx
                'partner_id':order.partner_id.id,
                'currency_id':order.currency_id.id,
            })
            kwargs.pop('custom_create_values', None)  # Don't allow passing arbitrary create values
            tx_sudo = self._create_transaction(
                custom_create_values={
                                        'reservation_ids': [Command.set([order_id])],
                                    }, **kwargs,
            )
        elif request.session.get('sale_order_id'):
            kwargs.update({
                'reference_prefix': None,  # Allow the reference to be computed based on the order
                'sale_order_id': order_id,  # Include the SO to allow Subscriptions to tokenize the tx
            })
            kwargs.pop('custom_create_values', None)  # Don't allow passing arbitrary create values
            tx_sudo = self._create_transaction(
                custom_create_values={'sale_order_ids': [Command.set([order_id])]}, **kwargs,
            )
        
        last_tx_id = request.session.get('__website_sale_last_tx_id')
        last_tx = request.env['payment.transaction'].browse(last_tx_id).sudo().exists()
        request.session['__website_sale_last_tx_id'] = tx_sudo.id

        return tx_sudo._get_processing_values()

class PaymentPostProcessingInherit(PaymentPostProcessing):

    @http.route(['/payment/status'], type="http", auth="public", website=True, sitemap=False)
    def display_status(self, **kwargs):
        if not request.session.get('reservation_order_id'):
            if request.session.get('sale_order_id'):
                sale_order_id = request.env['sale.order'].sudo().search([('id','=', request.session.get('sale_order_id'))])
                tx = request.website.sale_get_transaction()
                if tx and tx.state == 'done':
                    sale_order_id.sudo().write({
                        'state': 'done'
                    })
                res = super(PaymentPostProcessingInherit, self).display_status()
                return res
        else:
            tx = request.website.sale_get_transaction()

            if request.session.get('reservation_order_id'): 
                order_id = request.website.get_reservation()
                order_id = request.env['hotel.reservation'].sudo().search([('id', '=', order_id)])
            
            order = None
            if tx and tx.state == 'done':
                if request.session.get('reservation_order_id'): 
                    order = tx.reservation_id

                if order_id:
                    order_id.confirmed_reservation()
                    payment_vals = {
                        'amt': tx.amount,
                        'reservation_id': order_id.id,
                        'payment_date': datetime.now().date(),
                        'deposit_recv_acc': order_id.partner_id.property_account_receivable_id.id,
                        'journal_id': tx.provider_id.journal_id.id,
                    }
                    if request.session.get('reservation_order_id'): 
                        wiz_obj = request.env['advance.payment.wizard'].sudo().with_context(active_model='hotel.reservation',
                                                                                            active_id=order_id.id).create(
                            payment_vals)
                        wiz_obj.with_context(active_model='hotel.reservation').payment_process()
                        order = order_id
            elif order_id:
                if request.session.get('reservation_order_id'): 
                    order_obj = request.env['hotel.reservation'].sudo().browse(
                        order_id)
                    tx = request.env['payment.transaction'].sudo().search(
                    [('reservation_id', '=', order_obj.id.id), ('state', '=', 'draft')], limit=1)
                if request.session.get('sale_order_id'):
                    order_obj = request.env['sale.order'].sudo().browse(
                        order_id)
                    tx = request.env['payment.transaction'].sudo().search(
                    [('sale_order_ids', '=', order_obj.id.id), ('state', '=', 'draft')], limit=1)
                tx.write({'state': 'done'})
                if request.session.get('sale_order_id'):  
                    order = request.session.get('sale_order_id')
                if request.session.get('reservation_order_id'): 
                    order = tx.reservation_id
                if order:
                    order.confirmed_reservation()
                    payment_vals = {
                        'amt': tx.amount,
                        'reservation_id': order.id,
                        'payment_date': datetime.now().date(),
                        'deposit_recv_acc': order.partner_id.property_account_receivable_id.id,
                        'journal_id': tx.acquirer_id.journal_id.id,
                    }
                    if request.session.get('reservation_order_id'): 
                        wiz_obj = request.env['advance.payment.wizard'].sudo().create(payment_vals)
                        wiz_obj.with_context(active_model='hotel.reservation', active_id=order_id.id).payment_process()
                else:
                    order = order_id
            if request.session.get('reservation_order_id'): 
                return request.render("hotel_online.confirmation1", {'order': order})

class WebsiteShopInherit(WebsiteSale):
    @http.route(['/shop/cart/update'], type='http', auth="public", methods=['POST'], website=True, csrf=False)
    def cart_update(self, product_id, add_qty=1, set_qty=0, **kw):
        if not request.session.get('reservation_order_id'):
            res = super(WebsiteShopInherit, self).cart_update(product_id)
            return res
        else:
            product_id = request.env['product.template'].sudo().search(
                [('id', '=', product_id)])
            
            vals = {
                'product_id': product_id.id,
                'name': product_id.name,
                'product_uom': product_id.uom_id.id,
                'product_uom_qty': add_qty,
                'price_unit': product_id.list_price,
                
            }
            if product_id.taxes_id:
                vals.update({
                    'tax_id': [(6, 0, [product_id.taxes_id.id])],
                })
           

            if request.session.get('reservation_order_id'):
                order = request.env['hotel.reservation'].sudo().search(
                    [('id', '=', request.session.get('reservation_order_id'))])
                other_items_id = request.env['other.items'].sudo().create(vals)
                vals.update({'other_items_id': order.id, })
            
            if request.uid != 4:
                return request.redirect('/shop/payment')
            else:
                return request.redirect('/partner/checkout')

    @http.route(['/shop/cart/update_json'], type='json', auth="public", methods=['POST'], website=True, csrf=False)
    def cart_update_json(self, product_id, line_id=None, add_qty=None, set_qty=None, display=True, **kw):
        if not request.session.get('reservation_order_id'):
            res = super(WebsiteShopInherit, self).cart_update_json(product_id, line_id, add_qty, set_qty, display, **kw)
            return res
        else:
            product_id = request.env['product.template'].sudo().search(
                [('id', '=', product_id)])

            vals = {
                'product_id': product_id.id,
                'name': product_id.name,
                'product_uom': product_id.uom_id.id,
                'product_uom_qty': add_qty,
                'price_unit': product_id.list_price,
            }
            if product_id.taxes_id:
                vals.update({
                    'tax_id': [(6, 0, [product_id.taxes_id.id])],
                })     
            if request.session.get('reservation_order_id'):
                order = request.env['hotel.reservation'].sudo().search(
                    [('id', '=', request.session.get('reservation_order_id'))])
                vals.update({'other_items_id': order.id, })
                other_items_id = request.env['other.items'].sudo().create(vals)

            if request.uid != 4:
                return request.redirect('/shop/payment')
            else:
                return request.redirect('/partner/checkout')

class check(http.Controller):

    @http.route(['/page/hotel_online.product_show', '/page/product_show'], auth="public", website=True)
    def contact(self, **kwargs):
        values = {}
        portal_id = request.env['hotel.room'].sudo().search([])
        for port in portal_id:
            port.sudo().write({'state': 'draft'})
        request.website.sale_reset()
        values.update({
            'home':True
        })
        return request.render("hotel_online.product_show", values)

    @http.route('/product_screen/', type='http', auth='public', website=True)
    def get_products(self):
        result = {}
        values = {'product': False}
        return request.redirect_query("/page/hotel_online.product_show", values)

    @http.route('/product_search/', auth='public', website=True)
    def search_products(self, **kwargs):
        lst = []
        res1 = []
        res = []
        room_ids1 = []
        room_res = {}
        cnt = 0
        result_list11 = []
        count = []
        result = {}
        rm_brw = []
        date_values = list(kwargs.values())
        if not (kwargs.get('from_date') and kwargs.get('to_date')):
            raise UserError("Please Enter Checkin Date And Checkout Date")
        self._uid = SUPERUSER_ID
        product_id = request.env['product.product'].sudo().search([]).ids
        room_idsss = request.env['hotel.room_type'].sudo().search([]).ids
        amenities_idsss = request.env['hotel.room_type'].sudo().search([]).ids
        services_idsss = request.env['hotel.services'].sudo().search([]).ids

        if room_idsss:
            room_res11 = {}
            room_brw = request.env['hotel.room_type'].sudo().browse(room_idsss)
            amenities_brw = request.env['hotel.room_type'].sudo().browse(amenities_idsss)
            services_brw = request.env['hotel.services'].sudo().browse(services_idsss)
            for rbrw in room_brw:
                room_res11 = {}
                res = []
                res1 = []
                img_lst = []
                img_lst_ids = []
                room_res11['type'] = rbrw.name,
                room_res11['description'] = rbrw.description
                room_res11['amenities'] = []
                if amenities_idsss:
                    amenities = rbrw.room_type_amenities
                    for amenity in amenities:
                        if amenity != False:
                            room_res11['amenities'].append(amenity.name)
                        else:
                            pass
                img_lst = rbrw.img_ids
                user = request.env['res.users'].sudo().browse(request.uid)
                company = request.env.user.sudo().company_id
                if kwargs['from_date'] and kwargs['to_date']:
                    room_res11['chkin'] = kwargs['from_date']
                    room_res11['chkout'] = kwargs['to_date']
                for i in img_lst:
                    img_lst_ids.append(i.id)
                if rbrw.img_ids:
                    room_res11['image'] = img_lst_ids

                else:
                    room_res11['image'] = ''
                room_ids111 = request.env['hotel.room'].sudo().search([]).ids

                if room_ids111:
                    room_br11 = request.env['hotel.room'].sudo().browse(
                        room_ids111)
                    room_ids1 = []
                    room_res11['room_type_id'] = rbrw.id
                    shop_ids = request.env['sale.shop'].sudo().search(
                        [('company_id', '=', request.env.user.sudo().company_id.id)]).ids
                    shop_brw = request.env['sale.shop'].sudo().browse(
                        shop_ids[0])
                    room_res11['currency'] = shop_brw.pricelist_id.currency_id.symbol
                    for r in room_br11:
                        if r.product_id.product_tmpl_id.categ_id == rbrw.cat_id:
                            room_ids1.append(r.id)
                for rm in room_ids1:
                    rm1 = request.env['hotel.room'].sudo().browse(rm)
                    if shop_brw.pricelist_id.id:
                        price1 = shop_brw.sudo().pricelist_id._price_get(rm1.product_id, 0)[shop_brw.pricelist_id.id]
                    else:
                        price1 = 0
                    room_res11['price'] = round(price1, 2)
                    book_his = request.env['hotel.room.booking.history'].sudo().search(
                        [('history_id', '=', rm)]).ids
                    if book_his:
                        room_book = ''
                        book_brw = request.env['hotel.room.booking.history'].sudo().browse(
                            book_his)
                        for bk_his in book_brw:
                            start_date = datetime.strptime(
                                kwargs['from_date'], '%Y-%m-%d').date()
                            end_date = datetime.strptime(
                                kwargs['to_date'], '%Y-%m-%d').date()
                            try:
                                chkin_date = datetime.strptime(
                                    str(bk_his.check_in), '%Y-%m-%d %H:%M:%S').date()
                            except Exception as e:
                                chkin_date = datetime.strptime(
                                    str(bk_his.check_in), '%Y-%m-%d %H:%M:%S.%f').date()
                            try:
                                chkout_date = datetime.strptime(
                                    str(bk_his.check_out), '%Y-%m-%d %H:%M:%S').date()
                            except Exception as e:
                                chkout_date = datetime.strptime(
                                    str(bk_his.check_out), '%Y-%m-%d %H:%M:%S.%f').date()
                            if ((start_date <= chkin_date and (
                                    chkout_date <= end_date or chkout_date >= end_date >= chkin_date)) or (
                                    start_date >= chkin_date and chkout_date >= end_date) or (
                                    start_date <= chkout_date <= end_date)):
                                room_book = bk_his.history_id
                                break
                            else:
                                if not bk_his.history_id in lst:
                                    lst.append(bk_his.history_id)
                        if room_book in lst:
                            lst.remove(room_book)
                        for l in lst:
                            rm_brw = l
                            housek = request.env['hotel.housekeeping'].sudo().search(
                                [('room_no', '=', rm_brw.product_id.id), ('state', '=', 'dirty')])
                            if not housek:
                                if rm_brw.product_id.product_tmpl_id.categ_id == rbrw.cat_id:
                                    if not rm_brw in res1:
                                        res1.append(rm_brw)
                    else:
                        rm_brw = request.env['hotel.room'].sudo().browse(rm)
                        if rm_brw.product_id.product_tmpl_id.categ_id == rbrw.cat_id:
                            housek = request.env['hotel.housekeeping'].sudo().search(
                                [('room_no', '=', rm_brw.product_id.id), ('state', '=', 'dirty')])
                            if not housek:
                                res1.append(rm_brw)
                cnt = 0
                count = []
                adult = []
                child = []
                if rm_brw:
                    for i in range(1, (int(rm_brw[0].max_adult) + 1)):
                        adult.append(i)
                    for i in range(1, (int(rm_brw[0].max_child) + 1)):
                        child.append(i)
                    for r in res1:
                        cnt = cnt + 1
                        count.append(cnt)
                    room_res11['count'] = count,
                    room_res11['adult'] = adult,
                    room_res11['child'] = child,
                    room_res11['services'] = []
                    if services_idsss:
                            for rbrw in services_brw:
                                room_res11['services'].append(rbrw)
                    result_list11.append(room_res11)

        values = {
            'length': len(room_idsss),
            'count': count,
            'room_res': result_list11
            # 'room_res': None
        }
        return request.render("hotel_online.product_show", values)

    @http.route(['/page/hotel_online.booking_show', '/page/booking_show'], type='http', auth="public", website=True)
    def contact11(self, **kwargs):
        values = {}
        return request.render("hotel_online.booking_show", values)

    @http.route('/booking_screen/', type='http', auth='pubilc', website=True)
    def get_productsss(self):
        values = {'product': False}
        return http.local_redirect("/page/hotel_online.booking_show", values)

    @http.route(['/product/reserv/'], type='http', auth="public", website=True)
    def reserv_products(self, **kwargs):
        # cr,  context , pool= request.cr, request.context, request.registry
        values = {}
        rm_types = []
        room_id123 = []
        room_data = []
        lsttt = []
        cnt = 0
        tot = 0
        tax = 0
        dayss = 0
        res1, lst = [], []
        room_id = ''
        self._uid = SUPERUSER_ID
        user = request.env['res.users'].sudo().browse(request.uid)
        company = request.env.user.sudo().company_id
        names = [value for key, value in kwargs.items() if key.startswith('name_') and value]
        create_contact = request.env['res.partner'].sudo().create({'name': names[0]})
        if request.uid != 4:
            user_id = request.env['res.users'].sudo().search(
                [('id', '=', request.uid)])
            part_id = user_id.partner_id
        else:
            part_id = request.env['res.partner'].sudo().search(
                [('name', '=', 'Public user'), ('active', '=', False)])

        shop_ids = request.env['sale.shop'].sudo().search(
            [('company_id', '=', company.id)]).ids
        shop_brw = request.env['sale.shop'].sudo().browse(shop_ids[0])
        if 'chkin_id' in kwargs:
            newdate = kwargs['chkin_id'] + " 01:00:00"
        if 'chkout_id' in kwargs:
            newdate1 = kwargs['chkout_id'] + " 00:00:00"
        dt = datetime.strptime(time.strftime(
            '%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S').date()
        no = int(kwargs['len']) + 1
        total_no_adults = 0
        total_no_childs = 0
        for ll in range(1, int(no)):
            lsttt.append(ll)
        for l1 in lsttt:
            no_of_childs = 0
            no_of_adults = 0
            record = {}
            str1 = 'type_' + str(l1)
            str2 = 'child_' + str(l1)
            str3 = 'adult_' + str(l1)
            str4 = 'sel_' + str(l1)
            str5 = 'no_room_' + str(l1)
            if str1 in kwargs:
                record.update({'room_type': int(kwargs[str1])})

            if str2 in kwargs:
                record.update({'child': int(kwargs[str2])})
                no_of_childs = int(kwargs[str2])

            if str3 in kwargs:
                record.update({'adult': int(kwargs[str3])})
                no_of_adults += int(kwargs[str3])

            if str4 in kwargs:
                record.update({'chk': kwargs[str4]})

            if str5 in kwargs:
                record.update({'no_room': int(kwargs[str5])})
                if int(kwargs[str5]):
                    if no_of_adults:
                        total_no_adults += no_of_adults * int(kwargs[str5])
                    if no_of_childs:
                        total_no_childs += no_of_childs * int(kwargs[str5])

            if record:
                rm_types.append(record)
        room_id = request.session.get('reservation_order_id')

        policy = request.env['advance.payment.policy'].sudo().search([('type','=','website'),('shop_id','=',shop_ids[0])],limit=1)
        if policy:
            booking = policy.amount
        else:
            booking = False
        if not room_id:
            room_id = request.env['hotel.reservation'].sudo().create({
                'partner_id': create_contact.id,
                'shop_id': shop_ids[0],
                'adults': total_no_adults,
                'childs': total_no_childs,
                'pricelist_id': shop_brw.pricelist_id.id,
                'source': 'through_web',
                'date_order': time.strftime('%Y-%m-%d %H:%M:%S'),
                'online_advance_amount':booking,
            })

            request.session['reservation_order_id'] = room_id.id
        else:
            room_id = request.env['hotel.reservation'].sudo().search(
                [('id', '=', room_id)])
        tot_lines = 0
        for rtype in rm_types:
            room_brwww = request.env['hotel.room_type'].sudo().browse(
                rtype['room_type'])
            room_ids111 = request.env['hotel.room'].sudo().search([]).ids
            if room_ids111:
                room_br11 = request.env['hotel.room'].sudo().browse(
                    room_ids111)
                room_ids1 = []
                for r in room_br11:
                    housek = request.env['hotel.housekeeping'].sudo().search(
                        [('room_no', '=', r.product_id.id), ('state', '=', 'dirty')]).ids
                    if not housek:
                        if r.product_id.product_tmpl_id.categ_id.id == room_brwww.cat_id.id:
                            room_ids1.append(r.id)
            res1 = []
            for rm in room_ids1:
                book_his = request.env['hotel.room.booking.history'].sudo().search(
                    [('history_id', '=', rm)]).ids
                if book_his:
                    room_book = ''
                    book_brw = request.env['hotel.room.booking.history'].sudo().browse(
                        book_his)

                    for bk_his in book_brw:

                        if kwargs['chkin_id'] and kwargs['chkout_id']:
                            start_date = datetime.strptime(
                                kwargs['chkin_id'], '%Y-%m-%d').date()
                            end_date = datetime.strptime(
                                kwargs['chkout_id'], '%Y-%m-%d').date()
                            try:
                                chkin_date = datetime.strptime(
                                    str(bk_his.check_in), '%Y-%m-%d %H:%M:%S').date()
                            except Exception as e:
                                chkin_date = datetime.strptime(
                                    str(bk_his.check_in), '%Y-%m-%d %H:%M:%S.%f').date()

                            try:
                                chkout_date = datetime.strptime(
                                    str(bk_his.check_out), '%Y-%m-%d %H:%M:%S').date()
                            except Exception as e:
                                chkout_date = datetime.strptime(
                                    str(bk_his.check_out), '%Y-%m-%d %H:%M:%S.%f').date()
                            if ((start_date <= chkin_date and (
                                    chkout_date <= end_date or chkout_date >= end_date >= chkin_date)) or (
                                    start_date >= chkin_date and chkout_date >= end_date) or (
                                    start_date <= chkout_date <= end_date)):
                                room_book = bk_his.history_id
                                break
                            else:
                                if not bk_his.history_id in lst:
                                    lst.append(bk_his.history_id)
                    if room_book in lst:
                        lst.remove(room_book)
                    for l in lst:
                        rm_brw = l
                        if rm_brw.product_id.product_tmpl_id.categ_id == room_brwww.cat_id:
                            if not rm in res1 and not rm_brw in res1:
                                res1.append(rm_brw)
                else:
                    rm_brw = request.env['hotel.room'].sudo().browse(rm)
                    if rm_brw.product_id.product_tmpl_id.categ_id == room_brwww.cat_id:
                        res1.append(rm_brw)
            if 'no_room' in rtype and 'chk' in rtype:
                if rtype['chk'] == 'on':
                    for lno in range(0, (int(rtype['no_room']))):
                        no_of_days = (datetime.strptime(newdate1, '%Y-%m-%d %H:%M:%S') - datetime.strptime(newdate,
                                                                                                           '%Y-%m-%d %H:%M:%S')).total_seconds()

                        no_of_days = no_of_days / 86400
                        no_of_days = "{:.2f}".format(no_of_days)
                        no_of_days = math.ceil(float(no_of_days))

                        cin = str(datetime.strptime(
                            newdate, '%Y-%m-%d %H:%M:%S').date())
                        if len(res1) > 0:
                            price = shop_brw.sudo().pricelist_id._price_get(res1[lno].product_id, 0)
                            for key,value in price.items():
                                price = value
                            vals = {
                                'checkin': datetime.strptime(newdate, '%Y-%m-%d %H:%M:%S'),
                                'checkout': datetime.strptime(newdate1, '%Y-%m-%d %H:%M:%S'),
                                'categ_id': room_brwww.cat_id.id,
                                'room_number': res1[lno].product_id.id,
                                'line_id': room_id.id,
                                'price': price,
                                'number_of_days': no_of_days,
                            }
                            vals = self.set_checkin_checkout(vals)
                            room_line_id = request.env['hotel.reservation.line'].sudo().create(
                                vals)
                            if res1[lno].taxes_id.id:
                                room_line_id.update(
                                    {'taxes_id': [(6, 0, [res1[lno].taxes_id.id])]})
                            room_line_id.line_id.sudo().compute()
                            for rec in room_line_id:
                                room_line_id = request.env['hotel.room'].sudo().search(
                                    [('product_id', '=', rec.room_number.id)])
                              
                                vals = {
                                    'partner_id': create_contact.id,
                                    'check_in': rec.checkin,
                                    'check_out': rec.checkout,
                                    'history_id': room_line_id.id,
                                    'product_id': rec.room_number.id,
                                    'booking_id': room_id.id,
                                    'state': 'draft',
                                    'category_id': room_line_id.categ_id.id,
                                    'name': rec.room_number.name,
                                    'check_in_date': (rec.checkin).date(),
                                    'check_out_date': (rec.checkout).date(),
                                }

                                room_his_id = request.env['hotel.room.booking.history'].sudo().create(vals)

            dict = {}
            if 'no_room' in rtype and 'chk' in rtype:
                tot_lines = tot_lines + rtype['no_room']
                room_brw = request.env['hotel.room_type'].sudo().browse(
                    rtype['room_type'])
                for lll in range(1, (int(rtype['no_room'] + 1))):
                    dict = {'rm_name': room_brw.name}
                    if room_brw.img_ids:
                        dict.update({'image': room_brw.img_ids[0].id})
                    if 'child' in rtype:
                        dict.update({'child': int(rtype['child'])})
                    if 'adult' in rtype:
                        dict.update({'adult': int(rtype['adult'])})
                    if 'chkin_id' in kwargs:
                        dict.update({'chkin': kwargs['chkin_id']})
                    if 'chkout_id' in kwargs:
                        dict.update({'chkout': kwargs['chkout_id']})
                    delta = (datetime.strptime(newdate1, '%Y-%m-%d %H:%M:%S')) - (
                        datetime.strptime(newdate, '%Y-%m-%d %H:%M:%S'))

                    dayss = delta.total_seconds()
                    dayss = dayss / 86400
                    dayss = "{:.2f}".format(dayss)
                    dayss = math.ceil(float(dayss))
                    nights = dayss
                    if delta:
                        dict.update({'nights': nights})
                    dict.update({'img': company.currency_id.symbol})
                    room_search = request.env['hotel.room'].sudo().search(
                        []).ids
                    if room_search:
                        for rm_sear in room_search:
                            rm_brw = request.env['hotel.room'].sudo().browse(
                                rm_sear)
                            if rm_brw.product_id.product_tmpl_id.categ_id.id == room_brw.cat_id.id:
                                price = rm_brw.lst_price * dayss
                                tot = tot + rm_brw.lst_price
                                tax = tax + price * \
                                      (rm_brw.taxes_id.amount / 100)
                                break
                    dict.update({'price': "%.2f" % price, })
                    room_data.append(dict)
        values = {
            'room_data': room_data,
            'length': tot_lines,
            'tot': "%.2f" % (tot * dayss),
            'tax': "%.2f" % tax,
            'tot_tax': "%.2f" % ((tot * dayss) + tax),
            'room_id': room_id.id,
        }
        return request.render("hotel_online.booking_show", values)

    def set_checkin_checkout(self, vals):
        user_id = request.env['res.users'].sudo().search([('id', '=', 2)])
        tz = pytz.timezone(user_id.tz)
        time_difference = tz.utcoffset(utc_time).total_seconds()

        reservation_id = request.env['hotel.reservation'].sudo().search([('id', '=', vals.get('line_id'))])
        sale_shop_id = request.env['sale.shop'].sudo().search([('id', '=', reservation_id.shop_id.id)])

        checkout_policy_id = request.env['checkout.configuration'].sudo().search([('shop_id', '=', sale_shop_id.id)])
        if checkout_policy_id.name == 'custom':
            time = int(checkout_policy_id.time)

            checkin = vals.get('checkin')
            checkin = datetime(checkin.year, checkin.month, checkin.day)
            checkin = checkin + timedelta(hours=int(time))

            checkout = vals.get('checkout')
            checkout = datetime(checkout.year, checkout.month, checkout.day)
            checkout = checkout + timedelta(hours=int(time))

            checkout = checkout - timedelta(seconds=time_difference)
            checkin = checkin - timedelta(seconds=time_difference)

            vals.update({'checkout': checkout, 'checkin': checkin})
        else:
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            checkin = vals.get('checkin')
            from_string = datetime.strptime(current_time, "%H:%M:%S")

            checkin = checkin + timedelta(hours=from_string.hour, minutes=from_string.minute,
                                          seconds=from_string.second)


            checkout = vals.get('checkout')
            checkout = checkout + timedelta(hours=from_string.hour, minutes=from_string.minute,
                                            seconds=from_string.second)

            vals.update({'checkout': checkout, 'checkin': checkin})
        return vals

    @http.route(['/product_remove/'], type='http', auth="public", website=True)
    def remove_products(self, **kwargs):
        values = {}
        i = 0
        tot = 0
        room_data = []
        if 'len' in kwargs:
            data = ast.literal_eval(kwargs['len'])['data']
            for l in data:
                if 'room_type' in kwargs and 'rm_name' in l and str(l['rm_name']) == str(kwargs['room_type']):
                    if 'adult' in kwargs and 'adult' in l and str(l['adult']) == str(kwargs['adult']):
                        if 'child' in kwargs and 'child' in l and str(l['child']) == str(kwargs['child']):
                            data.pop(i)
                            i = i + 1
                            part_id = request.env['res.partner'].sudo().search(
                                [('name', '=', 'Public user'), ('active', '=', False)], limit=1)
                            reserv_se = request.env['hotel.reservation'].sudo().search(
                                [('partner_id', '=', part_id)])
                            if reserv_se:
                                for r_sear in reserv_se:
                                    reserv_br = request.env['hotel.reservation'].sudo().browse(
                                        r_sear)
                                    if datetime.strptime(reserv_br.date_order,
                                                         '%Y-%m-%d %H:%M:%S').date() == datetime.strptime(
                                        time.strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S').date():
                                        if reserv_br.reservation_line:
                                            for rl in reserv_br.reservation_line:
                                                if 'chkin' in kwargs and 'chkout' in kwargs:
                                                    rtse = request.env['hotel.room_type'].sudo().search(
                                                        [('name', '=', kwargs['room_type'])])
                                                    rtypr_br = request.env['hotel.room_type'].sudo().browse(
                                                        rtse)
                                                    chin = datetime.strptime(
                                                        rl.checkin, '%Y-%m-%d %H:%M:%S').date()
                                                    kchin = datetime.strptime(
                                                        kwargs['chkin'], '%Y-%m-%d').date()
                                                    chout = datetime.strptime(
                                                        rl.checkout, '%Y-%m-%d %H:%M:%S').date()
                                                    kcout = datetime.strptime(
                                                        kwargs['chkout'], '%Y-%m-%d').date()
                                                    if (chin == kchin and (chout == kcout) and (
                                                            rl.categ_id.id == rtypr_br.cat_id.id)):
                                                        request.env['hotel.reservation.line'].unlink(
                                                            rl.id)
                                                        break
        for d1 in data:
            tot = tot + d1['price']
        values = {
            'room_data': data,
            'tot': tot}
        return request.render("hotel_online.booking_show", values)

    def checkout_values(self, data=None):
        countries = request.env['res.country'].sudo().search([])
        states_ids = request.env['res.country.state'].sudo().search([])
        states = states_ids
        user_id = request.env['res.users'].sudo().search([('id', '=', request.uid)])
        partner = user_id.partner_id
        order = None

        shipping_id = data and data.get('shipping_id') or None
        shipping_ids = []
        checkout = {}
        if not data:
            if request.uid != request.website.user_id.id:
                checkout.update(self.checkout_parse("billing", partner))
            else:
                order1 = request.website.get_reservation()
                order = request.env['hotel.reservation'].sudo().browse(order1)
                if order.partner_id:
                    domain = [("partner_id", "=", order.partner_id.id)]
                    user_ids = request.env['res.users'].sudo().search(
                        domain)
                    if not user_ids or request.website.user_id.id not in user_ids:
                        checkout.update(self.checkout_parse(
                            "billing", order.partner_id))
        else:
            checkout = self.checkout_parse('billing', data)

        if not checkout.get('country_id'):
            
            country_code = request.geoip.country_code
            if country_code:
                country_ids = request.env['res.country'].search(
                    [('code', '=', country_code)], limit=1)
                if country_ids:
                    checkout['country_id'] = country_ids[0]

        values = {
            'countries': countries,
            'states': states,
            'checkout': checkout,
            'error': {},
            'has_check_vat': hasattr(request.env['res.partner'], 'check_vat'),
            'only_services': order or False
        }
        return values

    mandatory_billing_fields = ["name", "phone",
                                "email", "street", "city", "country_id"]
    optional_billing_fields = ["street", "state_id", "zip"]
    mandatory_shipping_fields = [
        "name", "phone", "street", "city", "country_id"]
    optional_shipping_fields = ["state_id", "zip"]

    def checkout_parse(self, address_type, data, remove_prefix=False):
        assert address_type in ('billing', 'shipping')
        if address_type == 'billing':
            all_fields = self.mandatory_billing_fields + self.optional_billing_fields
            prefix = ''
        else:
            all_fields = self.mandatory_shipping_fields + self.optional_shipping_fields
            prefix = 'shipping_'
        # set data
        if isinstance(data, dict):
            query = dict((prefix + field_name, data[prefix + field_name])
                         for field_name in all_fields if prefix + field_name in data)
        else:
            query = dict((prefix + field_name, getattr(data, field_name))
                         for field_name in all_fields if getattr(data, field_name))
            if address_type == 'billing' and data.parent_id:
                query[prefix + 'street'] = data.parent_id.name

        if query.get(prefix + 'state_id'):
            query[prefix + 'state_id'] = int(query[prefix + 'state_id'])
        if query.get(prefix + 'country_id'):
            query[prefix + 'country_id'] = int(query[prefix + 'country_id'])

        if not remove_prefix:
            return query
        return dict((field_name, data[prefix + field_name]) for field_name in all_fields if prefix + field_name in data)

    def checkout_form_validate(self, data):
        cr, uid, context, registry = request.cr, request.uid, request.context, request.registry

        error = dict()
        error_message = []

        for field_name in self.mandatory_billing_fields:
            if not data.get(field_name):
                error[field_name] = 'missing'

        if data.get('email') and not tools.single_email_re.match(data.get('email')):
            error["email"] = 'error'
            error_message.append(
                _('Invalid Email! Please enter a valid email address.'))

        if data.get("vat") and hasattr(registry["res.partner"], "check_vat"):
            if request.website.company_id.vat_check_vies:
                check_func = registry["res.partner"].vies_vat_check
            else:
                check_func = registry["res.partner"].simple_vat_check
         
        if data.get("shipping_id") == -1:
            for field_name in self.mandatory_shipping_fields:
                field_name = 'shipping_' + field_name
                if not data.get(field_name):
                    error[field_name] = 'missing'
        if [err for err in list(error.values()) if err == 'missing']:
            error_message.append(_('Some required fields are empty.'))
        return error, error_message

    def checkout_form_save(self, checkout):
        order1 = request.website.get_reservation()
        order = request.env['hotel.reservation'].sudo().browse(order1)
        orm_partner = request.env['res.partner']
        orm_user = request.env['res.users']
        order_obj = request.env['hotel.reservation']
        partner_lang = request.lang if request.lang in request.website.mapped(
            'language_ids.code') else None
        billing_info = {}
        if partner_lang:
            billing_info['lang'] = partner_lang
        billing_info.update(self.checkout_parse('billing', checkout, True))
        partner_id = None
        if request.uid != request.website.user_id.id:
            partner_id = orm_user.sudo().browse(request.uid).id
        elif order.partner_id:
            user_ids = request.env['res.users'].sudo().search(
                [("partner_id", "=", order.partner_id.id)])
            if not user_ids or request.website.user_id.id not in user_ids:
                partner_id = order.partner_id.id

        if billing_info.get('country_id'):
            partner_geoip = request.env["res.partner"].new({'country_id': int(billing_info.get('country_id'))})
            billing_info['property_account_position_id'] = request.env[
                'account.fiscal.position'].sudo()._get_fiscal_position(partner_geoip)
        if partner_id and request.website.partner_id.id != partner_id:
            partner_id1 = orm_partner.browse(partner_id)
            if not billing_info.get('state_id'):
                billing_info.pop('state_id')
            valiee = partner_id1.sudo().write(billing_info)
        else:
            partner_id = request.env['res.partner'].sudo().create(billing_info)
        order.write({'partner_id': partner_id})
        order_info = {
            'message_partner_ids': [(4, partner_id), (3, request.website.partner_id.id)],
        }
        zz = order_obj.sudo().write(order_info)


    @http.route(['/page/hotel_online.booking_show', '/partner/checkout'], type='http', auth="public", website=True)
    def checkout(self, **post):
        if request.session.get('sale_order_id'):
            cr, context = request.cr, request.context
            order_id = request.website.get_sale_order_id()
            redirection = self.checkout_redirection(order_id)
            if redirection:
                return redirection
            values = self.checkout_values()

            return request.render("hotel_online.res_partner_show", values)

        if request.session.get('reservation_order_id'):
            cr, context = request.cr, request.context

            reservation = request.website.get_reservation()
            redirection = self.checkout_redirection(reservation)
            if redirection:
                return redirection

            values = self.checkout_values()

            return request.render("hotel_online.res_partner_show", values)
        else:
            return request.redirect("/product_screen/")

    @http.route(['/custom/search/read'], type='json', auth="public", website=True)
    def custom_search_read(self, **post):
        reservation_obj = request.env['hotel.reservation'].sudo().search(
            [('id', '=', int(post['room_id']))])
        if reservation_obj and len(reservation_obj) > 0:
            if reservation_obj.state == 'cancel':
                return False
            else:
                return True
        return False

    @http.route(['/partner_add/'], type='http', auth="public", website=True, csrf=False)
    def confirm_order(self, **post):
        vals = {
            'name': post.get('name'),
            'email': post.get('email'),
            'phone': post.get('phone'),
            'street': post.get('street'),
            'city': post.get('city'),
            'zip': post.get('zip'),
            'country_id': int(post.get('country_id')),

        }
        if post.get('state_id'):
            vals.update({'state_id': int(post.get('state_id')), })
        else:
            vals.update({'state_id': None})
        user_id = request.env['res.users'].sudo().search(
            [('id', '=', request.uid)])
        if user_id:
            partner_id = user_id.partner_id
            if partner_id:
                partner_id.sudo().write(vals)

        if request.session.get('sale_order_id'):
            order = request.website.get_sale_order_id()
        if request.session.get('reservation_order_id'):
            order = request.website.get_reservation()

        if not order:
            return request.redirect("/shop")
        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        values = self.checkout_values(post)
        values["error"], values["error_message"] = self.checkout_form_validate(
            values["checkout"])
        if values["error"]:
            return request.render("hotel_online.res_partner_show", values)

        self.checkout_form_save(values["checkout"])
        return request.redirect("/shop/payment")

    @http.route(['/shop/payment'], type='http', auth="public", website=True)
    def payment(self, **post):
        if request.session.get('reservation_order_id'):
            order = request.website.get_reservation()
            order_browse = request.env['hotel.reservation'].sudo().browse(order)
        else:
            order = request.website.get_sale_order_id()
            order_browse = request.env['sale.order'].sudo().browse(order)

        if order:
            redirection = self.checkout_redirection(order)
            if redirection:
                return redirection

        render_values = self._get_shop_payment_values(order_browse, **post)

        if render_values['errors']:
            render_values.pop('acquirers', '')
            render_values.pop('tokens', '')
        order = request.website.sale_get_order()
        request.session['website_sale_cart_quantity'] = order.cart_quantity
        if request.session.get('reservation_order_id'):
            return request.render("hotel_online.payment123", render_values)
        else:
            return request.render("website_sale.payment", render_values)

    def _get_shop_payment_values(self, order, **kwargs):
        logged_in = not request.env.user._is_public()
        if request.session.get('reservation_order_id'):
            providers_sudo = request.env['payment.provider'].sudo()._get_compatible_providers(
                order.company_id.id,
                order.partner_id.id,
                order.remaining_amt,
                sale_order_id=order.id
            )  # In sudo mode to read the fields of acquirers, order and partner (if not logged in)
            payment_methods_sudo = request.env['payment.method'].sudo()._get_compatible_payment_methods(
            providers_sudo.ids,
            order.partner_id.id,
            currency_id=order.currency_id.id,
            )
        else:
            providers_sudo = request.env['payment.provider'].sudo()._get_compatible_providers(
            order.company_id.id,
            order.partner_id.id,
            order.amount_total,
            currency_id=order.currency_id.id,
            sale_order_id=order.id,
            website_id=request.website.id,
            )
            payment_methods_sudo = request.env['payment.method'].sudo()._get_compatible_payment_methods(
                providers_sudo.ids,
                partner_sudo.id,
                currency_id=currency.id,
            )
        tokens = request.env['payment.token'].sudo()._get_available_tokens(
            providers_sudo.ids, order.partner_id.id, **kwargs
        ) if logged_in else request.env['payment.token']
        show_tokenize_input = logged_in \
                              and not request.env['payment.provider'].sudo()._is_tokenization_required(
            sale_order_id=order.id
        )
        checkout_vals={
            'website_sale_order': order,
            'errors': [],
            'partner': order.partner_id,
            'order': order,
            'payment_action_id': request.env.ref('payment.action_payment_provider').id,
            'payment_methods_sudo': payment_methods_sudo,
            'providers_sudo':providers_sudo,
            'tokens_sudo': tokens,
            'sale_order_id': order.id,
            'show_tokenize_input_mapping': PaymentPortal._compute_show_tokenize_input_mapping(
                providers_sudo, sale_order_id=order.id
            ),
            'currency': order.currency_id,
            'partner_id': order.partner_id.id,
            'transaction_route': f'/shop/payment/transaction/{order.id}',
            'landing_route': '/shop/payment/validate',
        }
        if request.session.get('sale_order_id'):
            checkout_vals.update({
                'amount': order.amount_total,
                'access_token': order._portal_ensure_token(),
            })
        if request.session.get('reservation_order_id'):
            if order.online_advance_amount:
                 checkout_vals.update({
                'amount': order.online_advance_amount,
                'access_token': order.access_token,
                })
            else:
                checkout_vals.update({
                    'amount': order.total_cost1,
                    'access_token': order.access_token,
                })

        return checkout_vals

    @http.route('/shop/payment/validate', type='http', auth="public", website=True, sitemap=False)
    def shop_payment_validate(self, transaction_id=None, sale_order_id=None, **post):
        order_sale_id = ''
        order_reserve_id = ''
        transaction_id = request.session.get('__website_sale_last_tx_id')
        if sale_order_id is None:
            if 'sale_last_order_id' in request.session:
                last_order_id = request.session['sale_last_order_id']
                order = request.env['sale.order'].sudo().browse(last_order_id).exists()

            if 'reservation_last_order_id' in request.session:
                last_order_id = request.session['reservation_last_order_id']
                if request.session.get('reservation_last_order_id'):
                    order = request.env['hotel.reservation'].sudo().browse(last_order_id).exists()
        else:
            if request.session.get('sale_order_id'):
                order = request.env['sale.order'].sudo().browse(sale_order_id)
                assert order.id == request.session.get('sale_last_order_id')
            if request.session.get('reservation_order_id'):
                order = request.env['hotel.reservation'].sudo().browse(sale_order_id)
                assert order.id == request.session.get('reservation_last_order_id')

        if transaction_id:
            tx = request.env['payment.transaction'].sudo().browse(transaction_id)
            # assert tx in order.transaction_ids()
        elif order:
            tx = order.get_portal_last_transaction()
        else:
            tx = None
        if request.session.get('sale_last_order_id'):
            order_sale_id = request.session.get('sale_last_order_id')
            if not order or (order.amount_total and not tx):
                return request.redirect('/shop')
        if request.session.get('reservation_last_order_id'):
            order_reserve_id = request.session.get('reservation_last_order_id')
            if order and not order.total_cost1 and not tx:
                return request.redirect(order.get_portal_url())
        if request.session.get('sale_order_id'):
            if order and not order.amount_total and not tx:
                order.with_context(send_email=True).action_confirm()
                return request.redirect(order.get_portal_url())

        if request.session.get('reservation_order_id'):
            self.payment_status()
        request.website.sale_reset()
        if tx.state == 'draft' :
            tx.sudo().write({
                'state': 'pending'
            })
        if tx and tx.state == 'draft':
            return request.redirect('/shop')

        PaymentPostProcessing.remove_transactions(tx)

        if order_sale_id:
            return request.redirect('/shop/confirmation')
        if order_reserve_id:
            return request.redirect('/shop/confirmation1')

    def payment_status(self):
        tx = request.website.sale_get_transaction()
        order_id = request.website.get_reservation()
        order_id = request.env['hotel.reservation'].sudo().search([('id', '=', order_id)])
        order = None
        if tx and tx.state == 'done':
            order = tx.reservation_id

            if order_id:
                order_id.confirmed_reservation()
                payment_vals = {
                    'amt': tx.amount,
                    'reservation_id': order_id.id,
                    'payment_date': datetime.now().date(),
                    'deposit_recv_acc': order_id.partner_id.property_account_receivable_id.id,
                    'journal_id': tx.acquirer_id.journal_id.id,
                }
                wiz_obj = request.env['advance.payment.wizard'].sudo().with_context(active_model='hotel.reservation',
                                                                                    active_id=order_id.id).create(
                    payment_vals)
                wiz_obj.with_context(active_model='hotel.reservation').payment_process()
                order = order_id
        elif order_id:
            order_obj = request.env['hotel.reservation'].sudo().browse(
                order_id)
            tx = request.env['payment.transaction'].sudo().search(
                [('sale_order_id', '=', order_obj.id.id), ('state', '=', 'draft')], limit=1)
            tx.write({'state': 'done'})
            order = tx.sale_order_id
            if order:
                order.confirmed_reservation()
                payment_vals = {
                    'amt': tx.amount,
                    'reservation_id': order.id,
                    'payment_date': datetime.now().date(),
                    'deposit_recv_acc': order.partner_id.property_account_receivable_id.id,
                    'journal_id': tx.acquirer_id.journal_id.id,
                }
                wiz_obj = request.env['advance.payment.wizard'].sudo().create(payment_vals)
                wiz_obj.with_context(active_model='hotel.reservation', active_id=order_id.id).payment_process()
            else:
                order = order_id

    @http.route(['/shop/confirmation1'], type='http', auth="public", website=True)
    def payment_confirmation(self, **post):
        sale_order_id = request.session.get('reservation_order_id')
        if sale_order_id:
            order = request.env['hotel.reservation'].sudo().browse(
                sale_order_id)
            return request.render("hotel_online.confirmation1", {'order': order})
        else:
            return request.redirect('/shop')


    @http.route('/shop/payment/token', type='http', auth='public', website=True, sitemap=False)
    def payment_token(self, pm_id=None, **kwargs):
        tx = request.website.sale_get_transaction(
        ) or request.env['payment.transaction'].sudo()
        order_id = request.website.get_reservation()
        order = request.env['hotel.reservation'].sudo().browse(order_id)
        if not request.env['payment.token'].sudo().search_count([('id', '=', pm_id)]):
            return request.redirect('/shop/?error=token_not_found')

        payment_token = request.env['payment.token'].sudo().search([
            ('id', '=', pm_id)])
        acquirer = payment_token.acquirer_id
        tx_type = 'form'
        if not acquirer.payment_flow == 's2s':
            tx_type = 'form_save'
        x = tx._check_or_create_sale_tx(
            order, acquirer, payment_token=payment_token, tx_type=tx_type)
        return request.redirect('/payment/process')

    @http.route('/shop/payment/get_status123/<int:sale_order_id>', type='json', auth="public", website=True)
    def payment_get_status(self, sale_order_id, **post):
        order = request.env['hotel.reservation'].sudo().browse(sale_order_id)
        assert order.id == request.session.get('reservation_order_id')
        if not order:
            return {
                'state': 'error',
                'message': '<p>%s</p>' % _('There seems to be an error with your request.'),
            }
        tx_ids = request.env['payment.transaction'].sudo().search([
            '|', ('sale_order_id', '=', order.id), ('reference', '=', order.name)
        ])
        if not tx_ids:
            if order.total_cost1:
                return {
                    'state': 'error',
                    'message': '<p>%s</p>' % _('There seems to be an error with your request.'),
                }
            else:
                state = 'done'
                message = ""
                validation = None
        else:
            tx = tx_ids
            state = tx.state
            if state == 'done':
                message = '<p>%s</p>' % _('Your payment has been received.')
            elif state == 'cancel':
                message = '<p>%s</p>' % _(
                    'The payment seems to have been canceled.')
            elif state == 'pending' and tx.acquirer_id.validation == 'manual':
                message = '<p>%s</p>' % _(
                    'Your transaction is waiting confirmation.')
                if tx.acquirer_id.post_msg:
                    message += tx.acquirer_id.post_msg
            else:
                message = '<p>%s</p>' % _(
                    'Your transaction is waiting confirmation.')
        return {
            'state': state,
            'message': message,
            'validation': None
        }


    @http.route(['/other/items/unlink'], type='json', auth="public", website=True)
    def other_items_unlink(self, **post):
        other_items_id = request.env['other.items'].sudo().search(
            [('id', '=', int(post.get('other_items_id')))])
        other_items_id.unlink()
        return True

    def checkout_redirection(self, order):
        if type(order) == int:
            order = request.env['hotel.reservation'].sudo().browse(order)
        if not order or order.state != 'draft':
            request.session['sale_order_id'] = None
            request.session['sale_transaction_id'] = None
        tx = request.env.context.get('website_sale_transaction')
        if tx and tx.state != 'draft':
            return request.redirect('/shop/payment/confirmation/%s' % order)
            
    @http.route('/search_hotel',type='json',auth='none')
    def get_products(self):
        res=[]
        user_id = request.session.uid
        user = request.env['res.users'].sudo().browse(user_id)
        if user.partner_id.agent:
            shop = request.env['agent.relation'].sudo().search([('agent_id','=',user.partner_id.id)])
            for i in shop:
                for s in i.shop_ids:
                    res.append({
                        'name': s.name,
                        'id':s.id
                    })  
        else:
            shop = request.env['sale.shop'].sudo().search([])
            for i in shop:
                res.append({
                    'name': i.name,
                    'id':i.id
                })
        return res

class website(models.Model):
    _inherit = 'website'
    _columns = {}

    def get_image(self, a):
        if 'image' in list(a.keys()):
            return True
        else:
            return False

    def get_type(self, record1):
        categ_type = record1['type']
        categ_ids = self.env['product.category'].sudo().search(
            [('name', '=', categ_type[0])])
        categ_records = categ_ids[0]
        return True

    def check_next_image(self, main_record, sub_record):
        if len(main_record['image']) > sub_record:
            return 1
        else:
            return 0

    def image_url_new(self, record1, field, size=None):
        lst = []
        record = self.env['hotel.room.images'].sudo().browse(record1)
        cnt = 0
        for r in record:
            cnt = cnt + 1
            model = r._name
            sudo_record = r.sudo()
            id = '%s_%s' % (r.id, hashlib.sha1(
                (str(sudo_record.write_date) or str(sudo_record.create_date) or '').encode('utf-8')).hexdigest()[0:7])

            if cnt == 1:
                size = '' if size is None else '/%s' % size
            else:
                size = '' if size is None else '%s' % size
            lst.append('/website/image/%s/%s/%s%s' % (model, id, field, size))
        return lst

    def get_reservation(self):
        reservation_order_id = request.session.get('reservation_order_id')
        if not reservation_order_id:
            part_id1 = request.env['res.partner'].sudo().search(
                [('name', '=', 'Public user'), ('active', '=', False)])
            reservation = request.env['hotel.reservation'].sudo().search(
                [('partner_id', '=', part_id1[0].id)])
            reserv_list = reservation
            if reservation:
                reservation1 = request.env['hotel.reservation'].sudo().browse(
                    reservation[0])
                request.session['reservation_order_id'] = reservation1.id
                return reservation1.id
        return reservation_order_id

    def get_sale_order_id(self):
        order_id = request.session.get('sale_order_id')
        if not order_id:
            part_id1 = request.env['res.partner'].sudo().search(
                [('name', '=', 'Public user'), ('active', '=', False)])

            sale_order_ids = request.env['sale.order'].sudo().search([('partner_id', '=', part_id1[0].id)])
            if sale_order_ids:
                sale_order_id = request.env['sale.order'].sudo().browse(sale_order_ids[0])
                request.session['sale_order_id'] = sale_order_id.id
                return sale_order_id.id
        return order_id

    def sale_get_transaction(self):
        transaction_obj = self.env['payment.transaction']
        tx_id = request.session.get('__website_sale_last_tx_id')
        if tx_id:
            tx_ids = transaction_obj.sudo().search(
                [('id', '=', tx_id), ('state', 'not in', ['cancel'])])

            if tx_ids:
                return tx_ids
            else:
                request.session['sale_transaction_id'] = False
        return False


    def sale_reset(self):
        request.session.update({
            'sale_order_id': False,
            'sale_transaction_id': False,
            'sale_order_code_pricelist_id': False,
            'reservation_order_id': False,
        })




class ResCountry(models.Model):
    _inherit = 'res.country'

    def get_website_sale_countries(self, mode='billing'):
        return self.sudo().search([])

    def get_website_sale_states(self, mode='billing'):
        return self.sudo().state_ids


class CustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'reservation_count' in counters:
            values['reservation_count'] = request.env['hotel.reservation'].sudo().search_count([
            ])
        return values

    @http.route(['/my/reservations/', '/my/reservations/<int:reservation_id>'], type='http', auth='public',
                website=True)
    def template_reservation_render(self, **kwargs):
        values = self._prepare_portal_layout_values()
        reservation_id = kwargs.get('reservation_id')
        if reservation_id:
            order = request.env['hotel.reservation'].sudo().browse(reservation_id)
            values.update({
                'order': order,
                'page_name': 'reservation',
                'default_url': '/my/reservations',
            })
            return request.render('hotel_online.portal_my_reservations_detailed', values)
        reservations = request.env['hotel.reservation'].sudo().search([])
        values.update({'reservations': reservations,
                       'default_url': '/my/reservations',
                       'page_name': 'page'
                       })
        return request.render('hotel_online.portal_my_reservations', values)
