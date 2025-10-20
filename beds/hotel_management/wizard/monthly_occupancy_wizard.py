# -*- coding: utf-8 -*-

import time
from odoo import models, fields, api
import io
import base64
from odoo import models
import xlsxwriter
from datetime import datetime  # <-- This is necessary

class monthly_occupancy_wizard(models.TransientModel):
    _name = 'monthly.occupancy.wizard'
    _description = 'monthly occupancy wizard'

    start_date = fields.Date('From Date', required=True)
    end_date = fields.Date('To Date', required=True)
    hotel_id = fields.Many2one('sale.shop','Hotel',domain=lambda self: [('company_id', '=', self.env.company.id)],)

    @api.model
    def default_get(self, fields):
        res = super(monthly_occupancy_wizard, self).default_get(fields)
        today = time.strftime("%Y-%m-01")
        if int(time.strftime('%m') == 1 or time.strftime('%m') == 3 or time.strftime('%m') == 5 or time.strftime(
                '%m') == 7 or time.strftime('%m') == 8 or time.strftime('%m') == 10 or time.strftime('%m') == 12):
            lastday = time.strftime("%Y-%m-31")
        elif int(time.strftime('%m')) == 2:
            if (int(time.strftime('%Y')) % 4) == 0:
                lastday = time.strftime("%Y-%m-29")
            else:
                lastday = time.strftime("%Y-%m-28")
        else:
            lastday = time.strftime("%Y-%m-30")
        res.update({'start_date': today, 'end_date': lastday})
        return res

    def print_report(self):
        datas = {}
        return self.env.ref('hotel_management.monthly_occupency_qweb').report_action(self, data=datas, config=False)

    def print_occupancy_excel_report(self):
        report_obj = self.env['report.hotel_management.monthly_occupency_report_view']
        occupancy_data = report_obj.get_monthly_occupancy_information(self)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Monthly Occupancy Report")

        # Set column widths
        worksheet.set_column('A:D', 25)

        # Define formats
        bold = workbook.add_format({
            'bold': True, 'border': 1, 'align': 'center',
            'valign': 'vcenter', 'bg_color': '#D3D3D3'
        })
        normal = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
        date_format = workbook.add_format({'num_format': 'dd-mm-yyyy', 'border': 1, 'align': 'center'})

        # Title
        worksheet.merge_range('A1:D1', 'Monthly Occupancy Report', bold)

        # Header Row
        headers = ['Date', 'Booked Room(s)', 'Rooms Available', 'Occupancy (%)']
        for col, header in enumerate(headers):
            worksheet.write(1, col, header, bold)

        # Write data rows
        row = 2
        for line in occupancy_data:
            worksheet.write_datetime(row, 0, line.get('date'), date_format)
            worksheet.write_number(row, 1, line.get('no_booked_room') or 0, normal)
            worksheet.write_number(row, 2, line.get('total_room_avail') or 0, normal)
            worksheet.write_number(row, 3, round(line.get('occ_percent') or 0), normal)
            row += 1

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        output.close()

        # Save and return as downloadable file
        attachment = self.env['ir.attachment'].create({
            'name': 'monthly_occupancy_report.xlsx',
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
        return "Monthly-Occupancy-Report"

class monthly_occupancy_revenue_wizard(models.TransientModel):
    _name = 'monthly.occupancy.revenue.wizard'
    _description = 'monthly occupancy wizard'

    start_date = fields.Date('From Date', required=True)
    end_date = fields.Date('To Date', required=True)
    hotel_id = fields.Many2one('sale.shop','Hotel',domain=lambda self: [('company_id', '=', self.env.company.id)],)

    @api.model
    def default_get(self, fields):
        res = super(monthly_occupancy_revenue_wizard, self).default_get(fields)
        today = time.strftime("%Y-%m-01")
        if int(time.strftime('%m') == 1 or time.strftime('%m') == 3 or time.strftime('%m') == 5 or time.strftime(
                '%m') == 7 or time.strftime('%m') == 8 or time.strftime('%m') == 10 or time.strftime('%m') == 12):
            lastday = time.strftime("%Y-%m-31")
        elif int(time.strftime('%m')) == 2:
            if (int(time.strftime('%Y')) % 4) == 0:
                lastday = time.strftime("%Y-%m-29")
            else:
                lastday = time.strftime("%Y-%m-28")
        else:
            lastday = time.strftime("%Y-%m-30")
        res.update({'start_date': today, 'end_date': lastday})
        return res

    def print_report(self):
        datas = {}
        return self.env.ref('hotel_management.monthly_occupency_revenue_qweb').report_action(self, data=datas, config=False)

    def print_occupancy_revenue_excel_report(self):
        report_obj = self.env['report.hotel_management.monthly_occupency_revenue_report_view']
        revenue_data = report_obj.get_monthly_occupancy_revenue_information(self)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Occupancy Revenue Report")

        worksheet.set_column('A:L', 18)

        bold = workbook.add_format({
            'bold': True, 'border': 1, 'align': 'center',
            'valign': 'vcenter', 'bg_color': '#D3D3D3'
        })
        normal = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
        money_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1, 'align': 'right'})
        date_format = workbook.add_format({'num_format': 'dd-mm-yyyy', 'border': 1, 'align': 'center'})

        worksheet.merge_range('A1:L1', 'Monthly Occupancy Revenue Report', bold)

        headers = [
            'Date', 'Room', 'Checked-In', 'Checked-Out', 'Room Rent', 'Hotel Service',
            'Laundry', 'Restaurant', 'Transportation', 'POS', 'Tax Amount', 'Total'
        ]
        for col, header in enumerate(headers):
            worksheet.write(1, col, header, bold)

        row = 2
        for line in revenue_data:
            date_str = line.get('date')
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            worksheet.write_datetime(row, 0, date_obj, date_format)
            worksheet.write(row, 1, line.get('room_name', ''), normal)
            worksheet.write(row, 2, line.get('checked_in', ''), normal)
            worksheet.write(row, 3, line.get('checked_out', ''), normal)
            worksheet.write_number(row, 4, line.get('room_rent', 0.0), money_format)
            worksheet.write_number(row, 5, line.get('hotel_service', 0.0), money_format)
            worksheet.write_number(row, 6, line.get('laundry', 0.0), money_format)
            worksheet.write_number(row, 7, line.get('restaurant', 0.0), money_format)
            worksheet.write_number(row, 8, line.get('transportation', 0.0), money_format)
            worksheet.write_number(row, 9, line.get('pos', 0.0), money_format)
            worksheet.write_number(row, 10, line.get('tax', 0.0), money_format)
            worksheet.write_number(row, 11, line.get('total', 0.0), money_format)
            row += 1

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        output.close()

        attachment = self.env['ir.attachment'].create({
            'name': 'monthly_occupancy_revenue_report.xlsx',
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
        return "Revenue-Report"

