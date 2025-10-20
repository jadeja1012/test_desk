from odoo import fields, models, api
import pytz
from odoo.exceptions import ValidationError, UserError
import datetime


class folio_invoice_transfer_wizard(models.TransientModel):
    _name = 'folio.invoice.transfer.wizard'
    _description = 'Folio invoice transfer Wizard'

    folio_id = fields.Many2one(
        'hotel.folio', 'Folio Ref', default=lambda self: self._get_default_rec())
    trans_folio_id = fields.Many2one(
        'hotel.folio', 'Transfer Folio Ref', domain="[('state', 'not in', ['check_out','done','cancel'])]",)

    def _get_default_rec(self):
        res = {}
        if 'by_dashbord' in self._context and self._context.get('by_dashbord'):
            hotel_folio_id = self.env['hotel.folio'].search(
                [('reservation_id', '=', self._context['active_id'])])
            if hotel_folio_id:
                res = hotel_folio_id.id
                return res
        if self._context is None:
            self._context = {}
        if 'active_id' in self._context:
            res = self._context['active_id']
        return res

    def transfer_process(self):
        for obj in self:
            folio = obj.folio_id
            trans_folio = obj.trans_folio_id

            if trans_folio and trans_folio.partner_id.id == folio.partner_id.id:
                raise ValidationError("Error! Invoice can't be transferred as both folio partners are the same.")

            so = folio.order_id

            # Filter out meal products
            valid_lines = so.order_line.filtered(
                lambda l: l.product_id.name not in ['Breakfast', 'Breakfast And Dinner', 'All Meals']
            )

            if not valid_lines:
                raise ValidationError("No valid lines to invoice after skipping meal products.")

            # Prepare invoice values
            invoice_vals = so._prepare_invoice()
            invoice_vals['invoice_line_ids'] = []

            for line in valid_lines:
                line_vals = line._prepare_invoice_line(sequence=line.sequence)
                if line_vals:
                    invoice_vals['invoice_line_ids'].append((0, 0, line_vals))

            # Create the invoice
            invoice = self.env['account.move'].create(invoice_vals)

            # Add analytic account if project is linked to shop
            if folio.shop_id.project_id:
                invoice.invoice_line_ids.write({
                    'analytic_account_id': folio.shop_id.project_id.id,
                })

            # Set folio to "in progress"
            folio.write({'state': 'progress'})

            # If transferring to a different partner, update invoice partner
            if trans_folio and trans_folio.partner_id.id != folio.partner_id.id:
                invoice.write({'partner_id': trans_folio.partner_id.id})

            # Log relationship in junction table
            if trans_folio:
                self._cr.execute('''
                    INSERT INTO sale_transfer_account_invoice_rel (sale_id, invoice_id)
                    VALUES (%s, %s)
                ''', (trans_folio.order_id.id, invoice.id))

            # Handle POS orders and update `is_payatcheckout`
            for pos_order in folio.pos_order_ids:
                if pos_order.payment_status in ['paid']:
                    continue
                if pos_order.state in ['done']:
                    continue

                invoices = self.env['account.move'].search([('invoice_origin', '=', folio.name)])
                product_invoiced = any(
                    invoice_line.product_id.id == pos_line.product_id.id
                    for invoice in invoices
                    for invoice_line in invoice.invoice_line_ids
                    for pos_line in pos_order.lines
                )
                pos_order.write({
                    'is_payatcheckout': not product_invoiced
                })

                if not product_invoiced and not pos_order.payment_status =='payatcheckout':
                    invoice.write({
                        'invoice_line_ids': [(0, 0, vals) for vals in pos_order._prepare_invoice_lines()]
                    })
                if pos_order.payment_status =='payatcheckout':
                    invoice_lines = []
                    for pos_line in pos_order.lines:
                        line_vals = {
                            'product_id': pos_line.product_id.id,
                            'quantity': pos_line.qty,
                            'price_unit': pos_line.price_unit,
                            'name': pos_line.product_id.name,
                            'tax_ids': [(6, 0, pos_line.tax_ids.ids)],
                        }
                        invoice_lines.append((0, 0, line_vals))
                    invoice.write({'invoice_line_ids': invoice_lines})


        return {'type': 'ir.actions.act_window_close'}


class FolioSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    _description = 'Preparing Sale order Line'

    def _prepare_invoice_line(self, sequence):
        
        res = super(FolioSaleOrderLine, self)._prepare_invoice_line()
        hotel_folio_line_id = self._format_desc()
        if hotel_folio_line_id:
            timezone = pytz.timezone(self.env.user.tz) if self.env.user.tz else pytz.timezone(
                self._context.get('tz') or 'UTC')
            checkin_date = hotel_folio_line_id.checkin_date.astimezone(timezone)
            if checkin_date:
                checkin_date = datetime.datetime.strftime(
                    checkin_date, "%m/%d/%Y, %H:%M:%S")

                checkout_date = hotel_folio_line_id.checkout_date.astimezone(timezone)
                if checkout_date:
                    checkout_date = datetime.datetime.strftime(
                        checkout_date, "%m/%d/%Y, %H:%M:%S")
                res.update({'name': "Room: {}  From: {} To: {}".format(res.get('name'), checkin_date, checkout_date)})

        return res

    def _format_desc(self):
        hotel_folio_line = self.env['hotel_folio.line'].search(
            [('order_line_id', '=', self.id)])
        return hotel_folio_line
