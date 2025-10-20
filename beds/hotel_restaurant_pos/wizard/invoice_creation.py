import time
import logging
_logger = logging.getLogger(__name__)
# from openerp.osv import osv, fields
from odoo import fields,models
from odoo.exceptions import UserError


class InvoiceCreationPopup(models.TransientModel):
    _name = 'hotel.invoice.creation.popup'
    _description = 'Invoice Creation Popup'
    
    invoice_type = fields.Selection([
        ('folio', 'Create from Folio'),
        ('pos_order', 'Create from POS Order')
     ], string='invoice_type', required=True)
    
    
    def create_invoice(self):
        ir_model_data = self.env['ir.model.data']
        try:
           tree_id = ir_model_data._xmlid_lookup('hotel.view_hotel_folio1_tree_view')[2]
           form_id = ir_model_data._xmlid_lookup('hotel.view_hotel_folio1_form')[2]
        except (IndexError,ValueError):
            view_id = False
            tree_id = False
            form_id = False
            
            
        active_id = self.env.context.get('active_id')
        pos_order = self.env['pos.order'].browse(active_id)
        
        
        if self.invoice_type == 'folio':
            return {
                'type': 'ir.actions.act_window',
                'name': ('Hotel Folio'),
                'res_model': 'hotel.folio',
                'res_id': pos_order.folio_ids.id,
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': form_id,
                'target': 'current',
                'nodestroy': True,
            }
 
                
        
        elif  self.invoice_type == 'pos_order':
            return pos_order.action_pos_order_invoice()
