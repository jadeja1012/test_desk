from odoo import fields, models, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class AdvancePaymentWizard(models.TransientModel):
    _name = 'advance.payment.wizard'
    _description = 'Advance Payment Detail Wizard'

    amt = fields.Float('Amount', default=lambda self: self.advance_policy_amount())

    deposit_recv_acc = fields.Many2one('account.account', string="Deposit Account", required=True)
    journal_id = fields.Many2one('account.journal', "Journal", required=True, domain="[('type', 'in', ('cash', 'bank'))]")
    reservation_id = fields.Many2one('hotel.reservation', 'Reservation Ref', default=lambda self: self._get_default_rec())
    payment_date = fields.Date('Payment Date', required=True, default=fields.Date.context_today)

    @api.model
    def default_get(self, fields):
        res = super(AdvancePaymentWizard, self).default_get(fields)
        if self._context:
            active_model_id = self.env[self._context.get('active_model')].browse(self._context.get('active_id'))
            if active_model_id and active_model_id.partner_id.property_account_receivable_id:
                res['deposit_recv_acc'] = active_model_id.partner_id.property_account_receivable_id.id
        return res

    def _get_default_rec(self):
        return self._context.get('reservation_id', {})


    def payment_process(self):
        if self._context.get('active_model') == 'hotel.folio':
            for obj in self:
                folio_obj = self.env['hotel.folio'].search([('reservation_id', '=', obj.reservation_id.id)])
                if folio_obj:
                    folio_id = folio_obj[0]
                if not obj.deposit_recv_acc:
                    raise UserError("Account is not set for Deposit account.")
                if not obj.journal_id.default_account_id:
                    raise UserError("Account is not set for selected journal.")

                payment_id = self.env['account.payment'].create({
                    'journal_id': obj.journal_id.id,
                    'partner_id': obj.reservation_id.partner_id.id,
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'amount': obj.amt,
                })

                payment_id.move_id.ref = obj.reservation_id.name
                payment_id.action_post()

                if folio_obj and folio_id.id:
                    folio_id.write({'payment_move_ids': [(4, payment_id.id)]})
                    if payment_id.move_id:
                        self._cr.execute('insert into sale_account_move_rel(sale_id, move_id) values (%s, %s)', (
                            folio_id.id, payment_id.move_id.id))
                    else:

                        _logger.warning("Move ID is not created for payment: %s", payment_id.id)

                    sum = folio_id.total_advance + obj.amt
                    remainder = folio_id.amount_total - sum
                    self.env['hotel.folio'].write({'total_advance': sum})
                    sale = self.env['sale.order'].search([('id', '=', folio_id.order_id.id)])
        else:
            for obj in self:
                if not obj.deposit_recv_acc:
                    raise UserError("Account is not set for Deposit account.")
                if not obj.journal_id.default_account_id:
                    raise UserError("Account is not set for selected journal.")

                vals = {
                    'journal_id': obj.journal_id.id,
                    'partner_id': obj.reservation_id.partner_id.id,
                    'destination_account_id': obj.reservation_id.partner_id.property_account_receivable_id.id,
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'amount': obj.amt,
                    'memo' : obj.reservation_id.name,
                }
                
                
                payment_id = self.env['account.payment'].create(vals)
                
                journal_entry = self.env['account.move'].create({
                    'ref': obj.reservation_id.name,
                    'move_type': 'entry',
                    'name': payment_id.name,
                    'journal_id':obj.journal_id.id
                })

                move_line1 = {
                'move_id': journal_entry.id,
                'account_id': obj.journal_id.default_account_id.id,
                'debit': obj.amt,
                'credit': 0.0,
                'ref': obj.reservation_id.name,
                'journal_id': obj.journal_id.id,
                'partner_id': obj.reservation_id.partner_id.id,
                'date': obj.payment_date
            }

                move_line2 = {
                    'move_id': journal_entry.id,
                    'account_id': obj.reservation_id.partner_id.property_account_receivable_id.id,
                    'debit': 0.0,
                    'credit': obj.amt,
                    'ref': obj.reservation_id.name,
                    'journal_id': obj.journal_id.id,
                    'partner_id':obj.reservation_id.partner_id.id,
                    'date': obj.payment_date
                }
                journal_entry.write({'line_ids': [(0, 0, move_line1), (0, 0, move_line2)]})
                payment_id.move_id = journal_entry.id
                payment_id.action_post()
                obj.reservation_id.write({'payment_move_ids': [(4, payment_id.id)]})
                if payment_id.move_id:
                    self._cr.execute('insert into reservation_account_move_rel(reservation_id, move_id) values (%s, %s)', (
                        obj.reservation_id.id, payment_id.move_id.id))
                else:
                    _logger.warning("Move ID is not created for payment: %s", payment_id.id)

                sum = obj.reservation_id.total_advance + obj.amt
                remainder = obj.reservation_id.total_cost1 - sum
                obj.reservation_id.total_advance = sum

        return {'type': 'ir.actions.act_window_close'}


    def advance_policy_amount(self):
        res = self._context.get('reservation_id')
        reservation = self.env['hotel.reservation'].search([('id', '=', res)])
        policy = self.env['advance.payment.policy'].search([('type', '=', 'direct'), ('shop_id', '=', reservation.shop_id.id)], limit=1)
        return policy.amount if policy else False
