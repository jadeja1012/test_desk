# -*- coding: utf-8 -*-

import time
from odoo import fields, models
import io
import base64
import xlsxwriter

class arrival_dept_guest_wizard(models.TransientModel):
    _name = 'arrival.dept.guest.wizard'
    _description = 'Daily Customer Arrival/ Departure List'

    date_start = fields.Date('From Date', default=lambda *a: time.strftime('%Y-%m-%d'), required=True)
    arrival_dept = fields.Selection([('arrival', 'Customer Arrival'), ('depart', 'Customer Departure')],
                                    string='Report For', default=lambda *a: 'arrival', required=True)

    def print_report(self):
        datas = {}        
        return self.env.ref('hotel_management.report_arrival_dept_guest').report_action(self, data=datas, config=False)

    def _get_report_base_filename(self):
        if self.arrival_dept == 'arrival':
            return "ArrivalReport"
        else:
            return "DepartureReport"

    def print_report_excel_ar(self):
        report_obj = self.env['report.hotel_management.arrival_dept_guest']
        guest_data = report_obj.get_guest_arrival_dept_information(self)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Arrival Departure Report")

        # Set column widths
        worksheet.set_column('A:H', 20)

        # Define formats
        bold = workbook.add_format({
            'bold': True, 'border': 1, 'align': 'center',
            'valign': 'vcenter', 'bg_color': '#D3D3D3'
        })
        normal = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter'})

        # Report title
        report_title = f"{self.arrival_dept.capitalize()} Report ({self.date_start})"
        worksheet.merge_range('A1:H1', report_title, bold)

        # Header row
        headers = [
            'SN', 'Guest Name', 'Booking Ref.', 'Adults',
            'Children', 'Comp. Breakfast', 'Room No',
            'Arrival Time' if self.arrival_dept == 'arrival' else 'Departure Time'
        ]
        for col, header in enumerate(headers):
            worksheet.write(1, col, header, bold)

        # Write data rows
        row = 2
        for line in guest_data:
            worksheet.write(row, 0, line.get('sn'), normal)
            worksheet.write(row, 1, line.get('guest_name'), normal)
            worksheet.write(row, 2, line.get('booking_ref'), normal)
            worksheet.write(row, 3, line.get('adults'), normal)
            worksheet.write(row, 4, line.get('children'), normal)
            worksheet.write(row, 5, line.get('complimentary'), normal)
            worksheet.write(row, 6, line.get('room_name'), normal)
            worksheet.write(row, 7, str(line.get('checkin')), normal)
            row += 1

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        output.close()

        # Save and return as downloadable file
        attachment = self.env['ir.attachment'].create({
            'name': f"{self.arrival_dept}_report.xlsx",
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


