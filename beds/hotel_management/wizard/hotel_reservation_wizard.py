from odoo import fields, models, api
import time
import datetime
import base64
from odoo import models, fields, http
from odoo.http import request
import io
import xlsxwriter
from odoo.http import content_disposition

class hotel_reservation_wizard(models.TransientModel):
    _name = 'hotel.reservation.wizard'

    _description = 'Hotel reservation Wizard'

    date_start = fields.Date('From Date', required=True)
    date_end = fields.Date('To Date', required=True)

    def print_report(self):
        datas = {} 
        return self.env.ref('hotel_management.hotel_reservation_details_report').report_action(self, data=datas, config=False)
        
    def print_checkin(self):
        datas = {} 
        return self.env.ref('hotel_management.hotel_checkin_details_report').report_action(self, data=datas, config=False)

    def print_checkout(self):
        datas = {} 
        return self.env.ref('hotel_management.hotel_checkout_details_report').report_action(self, data=datas, config=False)

    def print_room_used(self):
        datas = {} 
        return self.env.ref('hotel_management.max_hotel_room_report').report_action(self, data=datas, config=False)


    def print_report_excel(self):
        # Search reservations within the date range and by confirmed/done state
        reservations = self.env['hotel.reservation.line'].search([
            ('checkin', '>=', self.date_start),
            ('checkout', '<=', self.date_end),
            ('line_id.state', 'in', ['confirm', 'done'])
        ])

        # Generate Excel file in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Reservation Report")

        # Set column widths for better spacing
        worksheet.set_column('A:A', 20)  # Reservation No.
        worksheet.set_column('B:B', 25)  # Guest Name
        worksheet.set_column('C:D', 20)  # Check In / Check Out
        worksheet.set_column('E:E', 20)  # Room Type
        worksheet.set_column('F:F', 18)  # Room No

        # Define cell formats
        bold = workbook.add_format({
            'bold': True,
            'border': 1,
            'valign': 'vcenter',
            'align': 'center',
            'text_wrap': True,
            'bg_color': '#D3D3D3'
        })

        normal = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'align': 'left',
            'text_wrap': True,
            'indent': 1
        })

        date_format = workbook.add_format({
            'num_format': 'yyyy-mm-dd',
            'border': 1,
            'valign': 'vcenter',
            'align': 'center'
        })

        # Write the title in a merged row
        worksheet.merge_range('A1:F1', f'Reservations from {self.date_start} to {self.date_end}', bold)
        worksheet.set_row(1, 30)  # Optional: title row height

        # Write the headers
        headers = ["Reservation No.", "Guest Name", "Check In", "Check Out", "Room Type", "Room No"]
        worksheet.set_row(2, 30)  # Header row height
        for col, header in enumerate(headers):
            worksheet.write(2, col, header, bold)

        # Write reservation data
        row = 3
        for res in reservations:
            room_name = res.room_number.name
            if room_name in ["Breakfast", "Breakfast And Dinner", "All Meals"]:
                continue

            worksheet.set_row(row, 25)  # Set height for each data row

            worksheet.write(row, 0, res.line_id.reservation_no or '', normal)
            worksheet.write(row, 1, res.line_id.partner_id.name or '', normal)

            if res.checkin:
                worksheet.write_datetime(row, 2, res.checkin, date_format)
            else:
                worksheet.write(row, 2, '', normal)

            if res.checkout:
                worksheet.write_datetime(row, 3, res.checkout, date_format)
            else:
                worksheet.write(row, 3, '', normal)

            worksheet.write(row, 4, res.categ_id.name or '', normal)
            worksheet.write(row, 5, room_name or '', normal)
            row += 1

        # Finalize workbook
        workbook.close()
        output.seek(0)

        # Encode file and create attachment
        file_data = base64.b64encode(output.read())
        output.close()

        attachment = self.env['ir.attachment'].create({
            'name': 'reservation_report.xlsx',
            'type': 'binary',
            'datas': file_data,
            'res_model': 'reservation.report.wizard',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        # Return download action
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }


    def print_checkin_excel(self):
        # Search reservation lines for check-in within date range and confirmed/done states
        reservations = self.env['hotel.reservation.line'].search([
            ('checkin', '>=', self.date_start),
            ('checkin', '<=', self.date_end),
            ('line_id.state', 'in', ['confirm', 'done'])
        ])

        # Create an Excel file in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Check-In Report")

        # Set column widths
        worksheet.set_column('A:A', 12)  # Reservation No
        worksheet.set_column('B:B', 25)  # Guest Name
        worksheet.set_column('C:C', 20)  # Check-In-Date
        worksheet.set_column('D:D', 20)  # Room Type
        worksheet.set_column('E:E', 15)  # Room No

        # Define formats
        title_format = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#D3D3D3', 'border': 1
        })

        normal_format = workbook.add_format({
            'border': 1, 'valign': 'vcenter', 'align': 'left'
        })

        date_format = workbook.add_format({
            'num_format': 'yyyy-mm-dd', 'border': 1,
            'valign': 'vcenter', 'align': 'center'
        })

        # Write title
        worksheet.merge_range('A1:E1', f'Check-In Guest List ({self.date_start} to {self.date_end})', title_format)

        # Write headers
        headers = ['#No', 'Guest Name', 'Check-In-Date', 'Room Type', 'Room No']
        for col_num, header in enumerate(headers):
            worksheet.write(1, col_num, header, title_format)

        # Write data rows
        row = 2
        for res in reservations:
            room_name = res.room_number.name
            if room_name in ["Breakfast", "Breakfast And Dinner", "All Meals"]:
                continue  # Skip service-type rooms

            worksheet.write(row, 0, res.line_id.reservation_no or '', normal_format)
            worksheet.write(row, 1, res.line_id.partner_id.name or '', normal_format)
            if res.checkin:
                worksheet.write_datetime(row, 2, res.checkin, date_format)
            else:
                worksheet.write(row, 2, '', normal_format)
            worksheet.write(row, 3, res.categ_id.name or '', normal_format)
            worksheet.write(row, 4, room_name or '', normal_format)
            row += 1

        # Finalize workbook
        workbook.close()
        output.seek(0)

        file_data = base64.b64encode(output.read())
        output.close()

        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': 'checkin_guest_list.xlsx',
            'type': 'binary',
            'datas': file_data,
            'res_model': 'reservation.report.wizard',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        # Return download action
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def print_checkout_excel(self):
        # Search reservation lines where checkout falls within range and reservation is confirmed/done
        reservations = self.env['hotel.reservation.line'].search([
            ('checkout', '>=', self.date_start),
            ('checkout', '<=', self.date_end),
            ('line_id.state', 'in', ['confirm', 'done'])
        ])

        # Create Excel file in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Checkout Guest List")

        # Set column widths
        worksheet.set_column('A:A', 12)  # Reservation No
        worksheet.set_column('B:B', 25)  # Guest Name
        worksheet.set_column('C:C', 20)  # Check-Out-Date
        worksheet.set_column('D:D', 20)  # Room Type
        worksheet.set_column('E:E', 15)  # Room No

        # Define styles
        bold = workbook.add_format({
            'bold': True, 'border': 1, 'valign': 'vcenter', 'align': 'center',
            'bg_color': '#D3D3D3', 'text_wrap': True
        })
        normal = workbook.add_format({
            'border': 1, 'valign': 'vcenter', 'align': 'left'
        })
        date_format = workbook.add_format({
            'num_format': 'yyyy-mm-dd', 'border': 1,
            'valign': 'vcenter', 'align': 'center'
        })

        # Write title
        worksheet.merge_range('A1:E1', f'Checkout Guest List ({self.date_start} to {self.date_end})', bold)

        # Write headers
        headers = ['#No', 'Guest Name', 'Check-Out-Date', 'Room Type', 'Room No']
        for col_num, header in enumerate(headers):
            worksheet.write(1, col_num, header, bold)

        # Write data rows
        row = 2
        for res in reservations:
            room_name = res.room_number.name
            if room_name in ["Breakfast", "Breakfast And Dinner", "All Meals"]:
                continue  # Skip meal-type entries

            worksheet.write(row, 0, res.line_id.reservation_no or '', normal)
            worksheet.write(row, 1, res.line_id.partner_id.name or '', normal)
            worksheet.write_datetime(row, 2, res.checkout, date_format) if res.checkout else worksheet.write(row, 2, '', normal)
            worksheet.write(row, 3, res.categ_id.name or '', normal)
            worksheet.write(row, 4, room_name or '', normal)
            row += 1

        # Finalize and return file
        workbook.close()
        output.seek(0)

        file_data = base64.b64encode(output.read())
        output.close()

        attachment = self.env['ir.attachment'].create({
            'name': 'checkout_guest_list.xlsx',
            'type': 'binary',
            'datas': file_data,
            'res_model': 'reservation.report.wizard',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def print_room_usage_excel(self):
        # Prepare room usage data similar to `get_room1()`
        lines = self.env['hotel.reservation.line'].search([
            ('checkin', '>=', self.date_start),
            ('checkout', '<=', self.date_end),
            ('line_id.state', 'in', ['confirm', 'done']),
            ('room_number.name', '!=', False)
        ])

        # Aggregate room usage
        room_usage = {}
        skip_names = ["Breakfast", "Breakfast And Dinner", "All Meals"]

        for line in lines:
            room_name = line.room_number.name
            if room_name in skip_names:
                continue  # Skip service/meal-type rooms

            key = (room_name, line.categ_id.name)
            if key not in room_usage:
                room_usage[key] = 0
            room_usage[key] += 1

        # Create Excel file in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Room Usage Report")

        # Set column widths
        worksheet.set_column('A:A', 15)  # Room No.
        worksheet.set_column('B:B', 25)  # Room Type
        worksheet.set_column('C:C', 20)  # No. of Times Used

        # Define formats
        bold = workbook.add_format({
            'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#D3D3D3'
        })

        normal = workbook.add_format({
            'border': 1, 'align': 'left', 'valign': 'vcenter'
        })

        # Write title
        worksheet.merge_range('A1:C1', f'Room Usage Report ({self.date_start} to {self.date_end})', bold)

        # Write headers
        headers = ['Room No.', 'Room Type', 'No. of Times Used']
        for col, header in enumerate(headers):
            worksheet.write(1, col, header, bold)

        # Write room usage data
        row = 2
        for (room_no, room_type), count in sorted(room_usage.items()):
            worksheet.write(row, 0, room_no, normal)
            worksheet.write(row, 1, room_type, normal)
            worksheet.write(row, 2, count, normal)
            row += 1

        # Finalize workbook
        workbook.close()
        output.seek(0)

        file_data = base64.b64encode(output.read())
        output.close()

        # Create attachment and return download action
        attachment = self.env['ir.attachment'].create({
            'name': 'room_usage_report.xlsx',
            'type': 'binary',
            'datas': file_data,
            'res_model': 'reservation.report.wizard',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

