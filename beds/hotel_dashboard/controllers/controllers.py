# -*- coding: utf-8 -*-
# from odoo import http


# class HotelDashboard(http.Controller):
#     @http.route('/hotel_dashboard/hotel_dashboard', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hotel_dashboard/hotel_dashboard/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('hotel_dashboard.listing', {
#             'root': '/hotel_dashboard/hotel_dashboard',
#             'objects': http.request.env['hotel_dashboard.hotel_dashboard'].search([]),
#         })

#     @http.route('/hotel_dashboard/hotel_dashboard/objects/<model("hotel_dashboard.hotel_dashboard"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hotel_dashboard.object', {
#             'object': obj
#         })

from odoo import http
from odoo.http import request
import json
import logging
import requests
from datetime import datetime,timedelta



_logger = logging.getLogger(__name__)

class Beds24WebhookController(http.Controller):

    '''@http.route('/beds24/webhook/reservation', type='json', auth='public', csrf=False, methods=['POST'])
    def reservation_webhook(self, **kwargs):
        print("bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")
        try:
            #data = request.jsonrequest
            data = json.loads(request.httprequest.data)
            _logger.info("Beds24 Reservation Webhook received: %s", json.dumps(data, indent=2))

            # Extract key data
            booking_id = data.get('bookingId')
            prop_id = data.get('propId')
            room_id = data.get('roomId')
            guest_name = data.get('guest', {}).get('name')
            checkin = data.get('startDate')
            checkout = data.get('endDate')
            guests = data.get('guests', 1)

            # Link to property and room
            #property_rec = request.env['sale.shop'].sudo().search([('prop_id', '=', str(prop_id))], limit=1)
            room_rec = request.env['hotel.room'].sudo().search([('beds24_room_id', '=', str(room_id))], limit=1)
            print("gggggggggggggggggggggggg",data)
            # Create reservation
            reservation = request.env['hotel.reservation'].sudo().create({
                'name': f"Booking #{booking_id}",
                'booking_ref': booking_id,
                'guest_name': guest_name,
                'checkin_date': checkin,
                'checkout_date': checkout,
                'guests': guests,
                #'property_id': property_rec.id if property_rec else False,
                'room_id': room_rec.id if room_rec else False,
                # Add more fields as needed
            })

            return {'success': True, 'id': reservation.id}

        except Exception as e:
            _logger.exception("Error processing Beds24 reservation webhook")
            return {'error': str(e)}'''


    @http.route('/beds24/webhook/reservation', type='json', auth='public', csrf=False, methods=['POST'])
    def reservation_webhook(self, **kwargs):
        print("vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvcccc")
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("Beds24 Reservation Webhook received: %s", data)

            prop_id = data.get('propId')
            action = data.get('action')

            if action == "SYNC_ROOM" and prop_id:
                # Fetch latest bookings from Beds24
                account = 1
                if not account:
                    return {"error": "Property not configured in Odoo"}, 404
                beds24 = request.env['beds24.config'].sudo().search([], limit=1)
                payload = {
                    "authentication": {
                        "apiKey": beds24.api_key,
                        "propKey": beds24.prop_key
                    },
                    
                }

                headers = {"Content-Type": "application/json"}
                response = requests.post("https://api.beds24.com/json/getBookings", json=payload, headers=headers)
                bookings = response.json()
                print("sssssssssssssssssssssssssssssssssssss",bookings)

                if not isinstance(bookings, list):
                    _logger.error("Invalid booking response: %s", bookings)
                    return {"error": "Invalid booking format"}, 500

                created = 0
                for booking in bookings:
                    if not booking.get('bookId'):
                        continue
                    guest_name = str(booking.get("guestFirstName"))
                    print("222222222222222222222222222",booking.get('price'))
                    partner = request.env['res.partner'].sudo().search([('name', '=', guest_name)], limit=1)
                    if not partner:
                        partner = request.env['res.partner'].sudo().create({'name': guest_name})
                      
                    if not request.env['hotel.reservation'].sudo().search([('beds_ref_id', '=', booking['bookId'])], limit=1):
                        checkin = datetime.strptime(booking.get('firstNight'), "%Y-%m-%d").strftime("%Y-%m-%d %H:%M:%S")
                        checkout = datetime.strptime(booking.get('lastNight'), "%Y-%m-%d").strftime("%Y-%m-%d %H:%M:%S")
                        last_night = booking.get('lastNight')
                        checkoutv = (
                                datetime.strptime(last_night, "%Y-%m-%d") + timedelta(days=1)
                            ).strftime("%Y-%m-%d %H:%M:%S")
                        shop = request.env['sale.shop'].sudo().search([('beds_24_prop_id', '=', booking['propId'])], limit=1)
                        print("666666666666666666666666666666666666666",shop)
                        hotel_book = request.env['hotel.reservation'].sudo().create({
                            'beds_ref_id': booking['bookId'],
                            #'checkin': booking.get('startDate'),
                            #'checkout': booking.get('endDate'),
                            'partner_id': partner.id,
                            #'room_id': booking.get('roomId'),
                            'shop_id': shop.id,
                            'childs': booking.get('numChild'),
                            'adults': booking.get('numAdult'),
                            'pricelist_id':shop.pricelist_id.id,
                            #'source': 'Beds24',
                        })
                        print("nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn",booking.get('roomId'))
                        room_number = request.env['hotel.room'].sudo().search([('beds24_room_id', '=', booking.get('roomId'))])
                        print("4444444444444444444444444",booking.get('price'))
                        checkin_date = datetime.strptime(checkin, "%Y-%m-%d %H:%M:%S")
                        checkout_date = datetime.strptime(checkoutv, "%Y-%m-%d %H:%M:%S")

                        num_days = (checkout_date - checkin_date).days
                        print("333333333333333333333333333333",num_days)
                        if num_days >= 2:
                            price = float(booking.get('price')) / num_days
                            print("fffffffffffffffffffffffffff",price)
                        else:
                            price = float(booking.get('price'))
                        hotel_book_line = request.env['hotel.reservation.line'].sudo().create({
                            'line_id': hotel_book.id,
                            'checkin': checkin,
                            'checkout': checkoutv,
                            #'partner_id': partner.id,
                            'room_number':room_number.product_id.id,
                            'categ_id': room_number.product_id.categ_id.id,
                            'price':price,
                            #'shop_id': 3,
                            #'adults': booking.get('guests'),
                            #'source': 'Beds24',
                        })
                        created += 1

                return {"status": "fetched", "created": created}

            return {"message": "No reservation action needed"}

        except Exception as e:
            _logger.exception("Error processing Beds24 webhook")
            return {"error": str(e)}, 500


