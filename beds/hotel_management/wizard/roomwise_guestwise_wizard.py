# -*- coding: utf-8 -*-

from odoo import models, fields
import io
import base64
from odoo import models
import xlsxwriter

class room_guestwise_wizard(models.TransientModel):
    _name = 'room.guestwise.wizard'
    _description = 'Room wise Guest wise Wizard'

    date_start = fields.Date('From Date', required=True)
    date_end = fields.Date('To Date', required=True)

    def print_report(self):
        datas = {}
        return self.env.ref('hotel_management.roomwise_guestwise_qweb').report_action(self, data=datas, config=False)

    def print_roomwise_guestwise_excel_report(self):
        report_obj = self.env['report.hotel_management.roomwise_guestwise_report_view']
        guest_data = report_obj.get_roomtype_guest_information(self)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Room Guest Report")

        # Set column widths
        worksheet.set_column('A:G', 25)

        # Define formats
        bold = workbook.add_format({
            'bold': True, 'border': 1, 'align': 'center',
            'valign': 'vcenter', 'bg_color': '#D3D3D3'
        })
        normal = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter'})
        datetime_format = workbook.add_format({'num_format': 'dd/mm/yyyy hh:mm', 'border': 1})

        # Title
        worksheet.merge_range('A1:G1', 'Room and Guest wise Report', bold)

        # Header Row
        headers = ['Room No', 'Check In', 'Check Out', 'Guest Name', 'Address', 'Is Checkin', 'Is Checkout']
        for col, header in enumerate(headers):
            worksheet.write(1, col, header, bold)

        # Write data rows
        row = 2
        for room_data in guest_data:
            room_name = room_data.get('room_name')
            for guest in room_data.get('data'):
                worksheet.write(row, 0, room_name, normal)
                worksheet.write(row, 1, guest.get('checkin') or '', datetime_format)
                worksheet.write(row, 2, guest.get('checkout') or '', datetime_format)
                worksheet.write(row, 3, guest.get('guest_name') or '', normal)
                worksheet.write(row, 4, guest.get('address') or '', normal)
                worksheet.write(row, 5, guest.get('is_checkin') or '', normal)
                worksheet.write(row, 6, guest.get('is_checkout') or '', normal)
                row += 1

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        output.close()

        # Save attachment
        attachment = self.env['ir.attachment'].create({
            'name': 'roomwise_guestwise_report.xlsx',
            'type': 'binary',
            'datas': file_data,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def _get_report_base_filename(self):
        return "Room-Guest-WiseReport"
