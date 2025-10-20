from odoo import models, fields, api
from datetime import datetime,date, timedelta
import pytz
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
import requests
import logging
_logger = logging.getLogger(__name__)

class Hotel_dashboard(models.Model):
    _inherit = 'hotel.reservation'



    @api.model
    def fetch_beds24_bookings(self):
        # Get the config record — assuming only one config is used
        config = self.env['beds24.config'].search([], limit=1)
        if not config:
            raise UserError("No Beds24 configuration found. Please set up credentials first.")

        url = "https://api.beds24.com/json/getBookings"

        payload = {
            "authentication": {
                "apiKey": config.api_key,
                "propKey": config.prop_key
            },
           
        }

        headers = {
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            bookings = data if isinstance(data, list) else []
            for booking in bookings:
                _logger.info("Fetched booking: %s", booking)
                # Here you can create or update reservation records
                print("444444444444444444444444444444444",booking)
                existing_res = self.env['hotel.reservation'].search([('beds_ref_id', '=', booking.get('bookId'))])
                print("5555555555555555555555555555",existing_res)
                if existing_res:
                    continue
                partner = self.env['res.partner'].search([('name', '=', booking.get('guestFirstName'))], limit=1)
                if not partner:
                    partner = self.env['res.partner'].create({'name': booking.get('guestFirstName')})
                checkin = datetime.strptime(booking.get('firstNight'), "%Y-%m-%d").strftime("%Y-%m-%d %H:%M:%S")
                checkout = (
                         datetime.strptime(booking.get('lastNight'), "%Y-%m-%d") + timedelta(days=1)
                           ).strftime("%Y-%m-%d %H:%M:%S")

                shop = self.env['sale.shop'].search([('beds_24_prop_id', '=', booking['propId'])], limit=1)
                room = self.env['hotel.room'].search([('beds24_room_id', '=', booking.get('roomId'))], limit=1)
                print("999999999999999999999999999999999",booking['numAdult'])
                reservation = self.env['hotel.reservation'].create({
                    'beds_ref_id': booking['bookId'],
                    'partner_id': partner.id,
                    'shop_id': shop.id,
                    'childs':  booking['numChild'],
                    'adults': booking['numAdult'],
                    'pricelist_id': shop.pricelist_id.id,})

                print("6666666666666666666666666666666666666",reservation)
                checkin_date = datetime.strptime(checkin, "%Y-%m-%d %H:%M:%S")
                checkout_date = datetime.strptime(checkout, "%Y-%m-%d %H:%M:%S")
                num_days = (checkout_date - checkin_date).days
                print("555555555555555555555555555",num_days)
                if num_days >= 2:
                    price = float(booking.get('price')) / num_days
                    print("666666666666666666666666666666",price)
                else:
                    price = float(booking.get('price'))
                self.env['hotel.reservation.line'].create({
                    'line_id': reservation.id,
                    'checkin': checkin,
                    'checkout': checkout,
                    'room_number': room.product_id.id,
                    'categ_id': room.product_id.categ_id.id,
                    'price': price,
                })
                
        except requests.exceptions.RequestException as e:
            _logger.error("Beds24 API error: %s", str(e))
            raise UserError(f"Beds24 API request failed: {str(e)}")
        except Exception as e:
            _logger.error("General Beds24 sync error: %s", str(e))
            raise UserError(f"Beds24 sync failed: {str(e)}")

    @api.model
    def create(self, vals):
        record = super().create(vals)
        try:
            self._push_reservation_to_bed24(record)
        except Exception as e:
            _logger.error(f"Failed to push reservation to Bed24 on create: {e}")
        return record

    def write(self, vals):
        res = super().write(vals)
        try:
            # If reservation is being cancelled, send cancellation to Beds24
            if 'state' in vals and vals['state'] == 'cancel':
                for record in self:
                    record._cancel_beds24_booking(record)
            else:
                for record in self:
                    record._push_reservation_to_bed24(record)
        except Exception as e:
            _logger.error(f"Failed to sync reservation to Beds24 on update: {e}")
        return res

    '''def _push_reservation_to_bed24(self, reservation):
        beds24 = self.env['beds24.config'].sudo().search([], limit=1)
        print("vvvvvvvvvvvvvvvvvvvvvvvvvvvv",beds24)
        if not beds24:
            _logger.warning("No Beds24 configuration found.")
            return

        for line in reservation.reservation_line:
            # Extract details from reservation line
            first_night = line.checkin.strftime('%Y-%m-%d') if line.checkin else None
            last_night = line.checkout.strftime('%Y-%m-%d') if line.checkout else None

            last_night = line.checkout - timedelta(days=1)
            last_night_str = last_night.strftime('%Y-%m-%d')
            room_id = line.room_number.beds24_room_id if line.room_number else None
            print("frrrrrrrrrrrrrrrrrrrrrrrrr",room_id)

            # Construct the payload based on Bed24 API documentation
            payload = {
                "authentication": {
                    "apiKey": beds24.api_key,
                    "propKey": beds24.prop_key
                },
                "bookId": reservation.beds_ref_id or "",  # Use existing Bed24 booking ID if available
                "guestFirstName": reservation.partner_id.name,
                "firstNight": first_night,
                "lastNight": last_night_str,
                "guests": reservation.adults,
                "roomId": room_id,
                # Add other required fields here
            }

            headers = {"Content-Type": "application/json"}
            response = requests.post("https://api.beds24.com/json/setBooking", json=payload, headers=headers)
            if response.status_code == 200:
                _logger.info(f"Reservation pushed to Beds24 successfully: {response.json()}")
                # Optionally update reservation.beds_ref_id with returned bookId if needed
            else:
                _logger.error(f"Error pushing reservation to Beds24: {response.status_code} - {response.text}")'''
    
    def _push_reservation_to_bed24(self, reservation):
        beds24 = self.env['beds24.config'].sudo().search([], limit=1)
        if not beds24:
            _logger.warning("No Beds24 configuration found.")
            return

        for line in reservation.reservation_line:
            first_night = line.checkin.strftime('%Y-%m-%d') if line.checkin else None
            last_night = (line.checkout - timedelta(days=1)).strftime('%Y-%m-%d') if line.checkout else None
            room_id = line.room_number.beds24_room_id if line.room_number else None
            _logger.info(f"Preparing payload for reservation with room_id={room_id}")

            # Prepare payload without bookId initially
            payload = {
                "authentication": {
                    "apiKey": beds24.api_key,
                    "propKey": beds24.prop_key
                },
                "guestFirstName": reservation.partner_id.name,
                "firstNight": first_night,
                "lastNight": last_night,
                "guests": reservation.adults,
                "roomId": room_id,
                # Add other required fields if needed
            }

            # If we have a bookId already saved, include it to update existing booking
            if reservation.beds_ref_id and reservation.beds_ref_id.strip():
                payload["bookId"] = reservation.beds_ref_id.strip()
                _logger.info(f"Updating existing booking with bookId={reservation.beds_ref_id.strip()}")
            else:
                _logger.info("Creating new booking (no bookId sent)")

            headers = {"Content-Type": "application/json"}
            response = requests.post("https://api.beds24.com/json/setBooking", json=payload, headers=headers)

            if response.status_code == 200:
                response_data = response.json()
                _logger.info(f"Reservation pushed to Beds24 successfully: {response_data}")

                # If this is a new booking, save the returned bookId in reservation.beds_ref_id
                if "bookId" in response_data and (not reservation.beds_ref_id or reservation.beds_ref_id.strip() == ""):
                    reservation.sudo().write({'beds_ref_id': response_data["bookId"]})
                    _logger.info(f"Saved new bookId {response_data['bookId']} in reservation.beds_ref_id")
            else:
                _logger.error(f"Error pushing reservation to Beds24: {response.status_code} - {response.text}")




    def _cancel_beds24_booking(self, reservation):
        """Send cancellation for the given reservation to Beds24.

        Requires `reservation.beds_ref_id` to be set with Beds24 bookId.
        """
        beds24 = self.env['beds24.config'].sudo().search([], limit=1)
        if not beds24:
            _logger.warning("No Beds24 configuration found. Skipping Beds24 cancellation.")
            return

        if not reservation.beds_ref_id:
            _logger.warning("Reservation %s has no Beds24 reference (beds_ref_id). Skipping Beds24 cancellation.", reservation.id)
            return

        payload = {
            "authentication": {
                "apiKey": beds24.api_key,
                "propKey": beds24.prop_key,
            },
            # Identify the booking to cancel on Beds24
            "bookId": reservation.beds_ref_id.strip(),
            # Best-effort cancellation flags according to Beds24 setBooking semantics
            "status": "cancelled",
        }

        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post("https://api.beds24.com/json/setBooking", json=payload, headers=headers)
            if response.status_code == 200:
                _logger.info("Beds24 booking %s cancelled successfully for reservation %s.", reservation.beds_ref_id, reservation.id)
            else:
                _logger.error("Beds24 cancellation failed (HTTP %s): %s", response.status_code, response.text)
        except Exception as e:
            _logger.error("Error calling Beds24 cancellation for reservation %s: %s", reservation.id, e)

    def search_reserve_room(self,room_id,cater_id,shop_id):
        room_id = int(room_id)
        cater_id = int(cater_id)
        shop_id = int(shop_id)

        hotel_reservation_id = self.env['hotel.reservation'].search([('shop_id', '=', shop_id)],limit=1)

        customer_name = ''
        if hotel_reservation_id:
            customer_name = hotel_reservation_id.partner_id.name

        categ_id = self.env['hotel.room_type'].search([('id','=',cater_id)])
        cat_id = categ_id.cat_id.id
        rooms = self.env['hotel.room'].search([('id','=',room_id)])
        room_id = rooms.product_id.id
        res = self.env['hotel.reservation.line'].search([
                ('room_number', '=', room_id),
                ('categ_id', '=', cat_id),
            ])
        reservations = []
        for line in res:
            reservation = line.line_id
            customer_name = reservation.partner_id.name
            customer_namestr = str(reservation.partner_id.name)
            first_name = customer_namestr.split()[0]
            reservations.append({
                'checkin': line.checkin,
                'checkout': line.checkout,
                'status': reservation.state,
                'id': reservation.id,
                'ref_no': reservation.reservation_no,
                'customer_name': first_name,
            })

        return {'reservations': reservations}


    def search_folio(self,shop_id):
        shop_id = int(shop_id)
        fo = self.env['hotel_folio.line'].search([('folio_id.shop_id.id','=',shop_id)])
        folio = []
        for i in fo:
            customer_namestr = str(i.folio_id.reservation_id.partner_id.name)
            first_name = customer_namestr.split()[0]
            folio.append({
                'checkin': i.checkin_date,
                'customer_name': first_name,
                'checkout':i.checkout_date,
                'status':i.folio_id.state,
                'id':i.folio_id.id,
                'room_name':i.product_id.name,
                'fol_no':i.folio_id.reservation_id.reservation_no,
            })
        return folio

    def search_cleaning(self,shop_id):
        shop_id = int(shop_id)
        clean = self.env['hotel.housekeeping'].search([('room_no.shop_id.id','=',shop_id)])
        cleans = []
        for i in clean:
            cleans.append({
                'room_no':i.room_no.name,
                'checkin':i.current_date,
                'checkout':i.end_date,
                'id':i.id,
                'status':i.state,
            })
        return cleans

    def search_repair(self,shop_id):
        shop_id = int(shop_id)
        repair = self.env['rr.housekeeping'].search([('shop_id','=',shop_id)])
        repairs = []
        for i in repair:
            repairs.append({
                'room_no':i.room_no.name,
                'date':i.date,
                'id':i.id,
                'type':i.activity,
                'status':i.state,
            })
        return repairs

    '''def create_detail(self,room_type,room,checkin,checkout):
        date_obj = datetime.strptime(checkin, "%Y-%m-%d")
        check_in = date_obj.date()
        now_time = datetime.now()
        user = self.env['res.users'].browse([self.env.user.id])
        tz = pytz.timezone(user.tz) or pytz.utc
        user_tz_date = pytz.utc.localize(now_time).astimezone(tz)
        user_hour_min = user_tz_date.strftime("%H:%M:%S")
      

        date2_date = datetime.strptime(checkout, "%Y-%m-%d")
        check_out = date2_date.date()
       
        if check_in == check_out:
            check_out = check_out + timedelta(days=1)
        room_types = int(room_type)
        room = int(room)
        categ_id = self.env['hotel.room_type'].search([('id','=',room_types)])
        cat_id = categ_id.cat_id.id
        rooms = self.env['hotel.room'].search([('id','=',room)])
        price = rooms.list_price
        room_id = rooms.product_id.id
        detail = [{
    'room': self.env['product.product'].browse(room_id),
    'cat_id': self.env['product.category'].browse(cat_id),
    'price': price,
    'checkout': check_out,
    'user_hour_min': user_hour_min,
}]
        return detail'''



    def create_detail(self, room_type, room, checkin, checkout):
        date_obj = datetime.strptime(checkin, "%Y-%m-%d")
        check_in = date_obj.date()
        now_time = datetime.now()
        user = self.env['res.users'].browse([self.env.user.id])
        tz = pytz.timezone(user.tz) or pytz.utc
        user_tz_date = pytz.utc.localize(now_time).astimezone(tz)
        user_hour_min = user_tz_date.strftime("%H:%M:%S")

        date2_date = datetime.strptime(checkout, "%Y-%m-%d")
        check_out = date2_date.date()

        if check_in == check_out:
            check_out += timedelta(days=1)

        room_type_rec = self.env['hotel.room_type'].browse(int(room_type))
        room_rec = self.env['hotel.room'].browse(int(room))

        product = room_rec.product_id
        category = room_type_rec.cat_id

        if not product.exists() or not category.exists():
            raise ValidationError("Invalid product or category reference")

        detail = [{
    'room': [product.id, product.display_name],     # ✅ JSON-safe Many2one
    'cat_id': [category.id, category.display_name], # ✅ JSON-safe Many2one
    'price': room_rec.list_price,
    'checkout': check_out.isoformat(),  # optional: string format
    'user_hour_min': user_hour_min,
}]

        return detail

    def reserve_room(self,id):
        id = int(id)
        reservation = self.env['hotel.reservation'].browse(id)
        user = self.env['res.users'].browse([self.env.user.id])
        tz = pytz.timezone(user.tz) or pytz.utc
        for line in reservation.reservation_line:
            checkin_utc = line.checkin
            checkin_utccc = line.checkin.replace(tzinfo=pytz.utc)
            checkin_local = checkin_utccc.astimezone(tz)
            check_in = checkin_local.strftime('%Y-%m-%d %H:%M:%S')
            checkout_utc = line.checkout 
            if checkout_utc:
                #check_out = checkout_utc_plus_offset
                check_out_utccc = line.checkout.replace(tzinfo=pytz.utc)
                checkout_local = check_out_utccc.astimezone(tz)
                check_out = checkout_local.strftime('%Y-%m-%d %H:%M:%S')
        res=[]
        res.append(
            {
                'res_no':reservation.reservation_no,
                'checkin':check_in,
                'checkout':check_out,
                'partner':reservation.partner_id.name,
                'state':reservation.state,
            }
        )
        return res

    def folio_detail(self,id):
        id = int(id)
        folio = self.env['hotel.folio'].browse(id)
        user = self.env['res.users'].browse([self.env.user.id])
        tz = pytz.timezone(user.tz) or pytz.utc
        for line in folio.room_lines:
            checkin_utc = line.checkin_date 
            time_offset = timedelta(hours=5, minutes=30)
            if checkin_utc:
                #checkin_utc_plus_offset = checkin_utc + time_offset
                #check_in = checkin_utc_plus_offset
                checkin_utccc = line.checkin_date.replace(tzinfo=pytz.utc)
                checkin_local = checkin_utccc.astimezone(tz)
                check_in = checkin_local.strftime('%Y-%m-%d %H:%M:%S')
            checkout_utc = line.checkout_date 
            #checkout_utc_plus_offset = checkout_utc + time_offset
            if checkout_utc:
                #check_out = checkout_utc_plus_offset
                check_out_utccc = line.checkout_date.replace(tzinfo=pytz.utc)
                checkout_local = check_out_utccc.astimezone(tz)
                check_out = checkout_local.strftime('%Y-%m-%d %H:%M:%S')
        res=[]
        res.append(
            {
                'res_no':folio.reservation_id.reservation_no,
                'checkin':check_in,
                'checkout':check_out,
                'partner':folio.partner_id.name,
                'state':folio.state,
            }
        )
        return res

    def cleaning_detail(self,id):
        id = int(id)
        clean = self.env['hotel.housekeeping'].browse(id)
        res=[]
        res.append(
            {
                'name':'Unavilable/Under Cleaning',
                'start':clean.current_date,
                'end':clean.end_date,
                'inspector':clean.inspector.name,
                'state':clean.state,
            }
        )
        return res

    def repair_repace_detail(self,id):
        id = int(id)
        repair = self.env['rr.housekeeping'].browse(id)
        res=[]
        res.append(
            {
                'name':'Repair/Repacement',
                'date':repair.date,
                'activity':repair.activity,
                'request':repair.requested_by.name,
                'approved':repair.approved_by,
                'state':repair.state,
            }
        )
        return res

    
    def get_datas(self,shop):
        shop_ids = int(shop)
        if shop_ids:
            check_in = self.env['hotel.reservation'].search([('state', '=', 'confirm'), ('shop_id', '=', shop_ids)])
            check_out = self.env['hotel.folio'].search([('state', '=','check_out'), ('shop_id', '=', shop_ids)])
            roomid = []
            room_id = self.env['hotel.room'].search([('shop_id','=',shop_ids)])
            for i in room_id:
                roomid.append(i)
            for i in room_id:
                book_his = self.env['hotel.room.booking.history'].search(
                    [('history_id', '=', i.id),('state', '!=', 'done'),('history_id.shop_id', '=',shop_ids )])
                if book_his and i in roomid:
                    roomid.remove(i)
            for i in room_id:
                prod = i.product_id.id
                housekeep = self.env['hotel.housekeeping'].search([('room_no','=',prod),('state', '!=', 'done'),('room_no.shop_id','=',shop_ids)])
                if housekeep and i in roomid:
                    roomid.remove(i)
            for i in room_id:
                repair = self.env['rr.housekeeping'].search([('room_no','=',i.id),('state', '!=', 'done'),('shop_id', '=', shop_ids)])
                if repair and i in roomid:
                    roomid.remove(i)
            booked = self.env['hotel.reservation'].search([('state', '!=', 'cancel'),('shop_id', '=', shop_ids)])

            # Check Today's Booking For Each Room
            today = date.today()
            start_of_day = datetime.combine(today, datetime.min.time())
            end_of_day = datetime.combine(today, datetime.max.time())
            for i in room_id:
                today_book_his = self.env['hotel.room.booking.history'].search(
                    [('history_id', '=', i.id), ('state', '=', 'done'),('check_in', '>=', start_of_day),
                   ('check_in', '<=', end_of_day)
                ])
                if today_book_his :
                    roomid.remove(i)
            
            return {
                'check_in': len(check_in),
                'check_out': len(check_out),
                'total': len(roomid),
                'booked': len(booked),
            }
        else:
            return {
                'check_in': '',
                'check_out': '',
                'total': '',
                'booked': '',
            }

    def get_view_reserve(self):
        view_id = self.env.ref('hotel_management.view_hotel_reservation_form1').id
        return view_id


class RoomType(models.Model):
    _inherit = 'hotel.room_type'


    def list_room_type(self,shop_id):
        shop_id = int(shop_id)
        types = self.search([])
        data=[]
        for i in types:
            check = self.list_room(i.id,shop_id)
            if check:
                data.append({
                    'name':i.name,
                    'id':i.id,
                    'sequence':i.sequence
                })
        sorted_data = sorted(data, key=lambda x: x['sequence'])
            
        return sorted_data

    def list_room(self,res,shop_id):
        shop_id = int(shop_id)
        room_types =int(res)
        categ_id = self.env['hotel.room_type'].search([('id','=',room_types)])
        cat_id = categ_id.cat_id.id
        room = self.env['hotel.room'].search([('categ_id','=',cat_id),('shop_id','=',shop_id)])
        datas=[]
        for i in room:
            datas.append({
                'name':i.name,
                'id':i.id
            })
        return datas

    def list_shop(self):
        shop = self.env['sale.shop'].search([])
        res = []
        for i in shop:
            res.append({
                'name': i.name,
                'id':i.id
            })
        return res
        

class CheckoutConfiguration(models.Model):
    _inherit = 'checkout.configuration'

    def hotel_checkout_policy(self,shop_id):

        checkout_id = self.search([('shop_id','=',shop_id),('name','=','custom')])
        if checkout_id:
            return int(checkout_id.time)
        return False


class CalendarEvent(models.Model):
    _inherit = "calendar.event"


    hotel_folio = fields.Many2one(
    'hotel.folio',
    string='Link To Folio',
    tracking=True,
    domain="[('state', 'not in', ('check_out', 'done', 'cancel'))]"
)
    hotel_folio_done = fields.Boolean("Hotel Boolean")


    def book_folio(self):
        if self.hotel_folio and self.hotel_folio_done == False:
            self.hotel_folio_done = True
            for line in self.hotel_folio.room_lines:
                if self.start.date() != line.checkin_date.date():
                    raise ValidationError("Start date does not match any room line check-in date.")
                else:
                    self.hotel_folio.service_lines = [(0, 0, {
                'product_id': self.appointment_type_id.product_id.id,
                'product_uom_qty': self.duration,
                'name': "Your " + self.appointment_type_id.name + " Reserved for "+ str(self.duration) + " Hours ",
                'price_unit':self.appointment_type_id.product_id.list_price,
                'price_subtotal':self.appointment_type_id.product_id.list_price * self.duration,
                # Add other necessary fields here
                })]


class CalendarEvent(models.Model):
    _inherit = "appointment.type"

    product_id = fields.Many2one(
    'product.product',
    string='Link To Product',
    domain="[('isservice', '=', True)]")
    
    
    
    
class Beds24Config(models.Model):
    _name = 'beds24.config'
    _description = 'Beds24 Configuration'

    name = fields.Char(string='Configuration Name', required=True)
    api_key = fields.Char(string='API Key', required=True)
    prop_key = fields.Char(string='Property Key', required=True)

    @api.model
    def get_headers(self):
        return {
            "Content-Type": "application/json"
        }

    def test_connection(self):
        self.ensure_one()
        payload = {
            "authentication": {
                "apiKey": self.api_key,
                "propKey": self.prop_key
            }
        }

        try:
            response = requests.post("https://api.beds24.com/json/getBookings", json=payload, headers=self.get_headers())
            data = response.json()

            if isinstance(data, list):
                raise UserError("✅ Connection successful. %d" % len(data))
            elif 'error' in data:
                raise UserError("❌ Connection failed: %s" % data.get('error'))
            else:
                raise UserError("⚠️ Unexpected response: %s" % data)
        except Exception as e:
            raise UserError(f" Connecting to Beds24: {str(e)}")

    def sync_properties_and_rooms(self):
        self.ensure_one()
        headers = {"Content-Type": "application/json"}

        # Fetch properties
        payload_props = {
            "authentication": {
                "apiKey": self.api_key
            }
        }

        res_props = requests.post("https://api.beds24.com/json/getProperties", json=payload_props, headers=headers)
        if res_props.status_code != 200:
            raise UserError(f"Property fetch failed: HTTP {res_props.status_code} - {res_props.text}")

        try:
            resp_json = res_props.json()
        except Exception as e:
            raise UserError(f"Invalid JSON: {e}")

        properties = resp_json.get('getProperties', [])
        if not isinstance(properties, list) or not properties:
            raise UserError(f"Property fetch failed or empty: {resp_json}")

        for prop in properties:
            print("PROPERTY >>>>", prop)
            prop_rec = self.env['sale.shop'].sudo().search([('beds_24_prop_id', '=', str(prop.get('propId')))])
            if not prop_rec:
                prop_rec = self.env['sale.shop'].sudo().create({
                    'name': prop.get('name') or prop.get('propertyName', 'Unnamed'),
                    'payment_default_id': 1,
                    'pricelist_id': 1,
                    'pricelist_id': 1,
                    'picking_type_id':2,
                    'beds_24_prop_id':prop.get('propId'),
                    #'prop_id': str(prop.get('propId')),
                    #'prop_key': prop.get('propKey', ''),
                    #'currency': prop.get('currency')
                })
            else:
                prop_rec.write({
                    'name': prop.get('name') or prop.get('propertyName', 'Unnamed'),
                    'beds_24_prop_id':prop.get('propId'),
                    #'currency': prop.get('currency')
                })

            # Process rooms from roomTypes
            for room in prop.get('roomTypes', []):
                print("ROOM >>>>", room)
                room_id = str(room.get('roomId'))
                room_rec = self.env['hotel.room'].sudo().search([('beds24_room_id', '=', room_id)], limit=1)
                room_vals = {
                    'name': room.get('name'),
                    'beds24_room_id': room_id,
                    'max_child': int(room.get('maxPeople', 0)),
                    'shop_id': prop_rec.id,
                    'company_id': prop_rec.company_id.id
                }
                print("vvvvvvvvvvvvvvvvvvvvvvvvvvvvv",prop_rec.id)

                if not room_rec:
                    print("errrrrrrrrrrrrrrrrrrrrrrrrrrr",room_rec)
                    self.env['hotel.room'].sudo().create(room_vals)
                else:
                    room_rec.write(room_vals)
