from odoo import api, models, fields
import time
import datetime
from odoo.tools import config
from odoo import netsvc


class hotel_restaurant_wizard(models.TransientModel):
    _name = 'hotel.restaurant.wizard'
    _description = 'hotel_restaurant_wizard'

    grouped = fields.Boolean('Group the kots')

class hotel_restaurant_reservation_wizard(models.TransientModel):
    _name = 'hotel.restaurant.reservation.wizard'

    _description = 'hotel_restaurant_reservation_wizard'

    date_start = fields.Date('From Date', required=True)
    date_end = fields.Date('To Date', required=True)

    def print_report(self):
        datas = {} 
        return self.env.ref('hotel_restaurant.hotel_restaurant_reservation_report1').report_action(self, data=datas)

