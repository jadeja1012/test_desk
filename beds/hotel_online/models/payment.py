from datetime import datetime

from odoo import models, fields, api, _
from odoo.tools.float_utils import float_compare
import logging
from . import reservation as res
from odoo import api, fields, models, _, SUPERUSER_ID
_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'
    reservation_id = fields.Many2one('hotel.reservation', string='Reservation')
    reservation_ids = fields.Many2many('hotel.reservation', 'hotel_reservation_transactions_rel','transaction_id','reservation_id',
                                    string='Reservation Orders', copy=False, readonly=True)