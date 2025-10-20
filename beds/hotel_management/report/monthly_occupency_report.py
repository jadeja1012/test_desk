# from mx import DateTime

from operator import itemgetter
from odoo import models,fields
from datetime import datetime, timedelta


class monthly_occupency(models.AbstractModel):
    _name = 'report.hotel_management.monthly_occupency_report_view'
    _description = 'Occupancy Report View'

    def get_monthly_occupancy_information(self, data):
        
        date_start = data.start_date
        date_stop = data.end_date
        reservation_start_date = date_start
        reservation_start_date = datetime.combine(reservation_start_date, datetime.min.time())
        reservation_start_date = datetime.strptime(str(reservation_start_date), '%Y-%m-%d %H:%M:%S')
        reservation_end_date = datetime.combine(date_stop, datetime.min.time())
        reservation_end_date = datetime.strptime(str(reservation_end_date), '%Y-%m-%d %H:%M:%S')

        result_list = []
        date_list = []

        hotel_search = self.env['hotel.reservation'].search([('state', 'in', ['done']), ('shop_id', '=', data.hotel_id.id)])
        

        if hotel_search:
            total_room1 = 0
            for folio in hotel_search:

                for line in folio.reservation_line:
                    if line.checkin and line.checkout:
                        history_start_date1 = line.checkin
                        history_end_date1 = line.checkout
                        no_days = line.number_of_days
                        total_room1 = len(self.env['hotel.room'].search([('shop_id','=',data.hotel_id.id)]))
                        confirm_day_count = (history_end_date1 - history_start_date1).days
                        
                        for count in range(0, (int(confirm_day_count) + 1)):
                            room_no1 = 0.0
                            rent_amt = 0.0
                            tax = 0.0
                            if reservation_start_date < history_start_date1 < reservation_end_date:
                                single_date1 = history_start_date1 + timedelta(days=count)

                                date_list.append(single_date1)

                                for check_room in self.env['hotel.reservation.line'].search(([])):
                                    if check_room.checkin <= single_date1 <= check_room.checkout:
                                        room_no1 = room_no1 + 1
                                tax += folio.total_tax / no_days if no_days else 0
                                for lines in folio.reservation_line:
                                    rent_amt += lines.sub_total1 / no_days if no_days else 0
                                tot_sub = rent_amt
                                gross_tot = tot_sub + tax
                                if total_room1:
                                    result_dic = {
                                        'date': single_date1,
                                        'no_booked_room': room_no1,
                                        'occ_percent': (room_no1 * 100) / total_room1,
                                        'tot_rent': round(rent_amt, 2) or 0.0,
                                        'tot_service': 0.0,
                                        'tot_rest': 0.0,
                                        'tot_laundry': 0.0,
                                        'tot_sub': round(tot_sub, 2) or 0.0,
                                        'tot_tax': round(tax, 2) or 0.0,
                                        'gross_tot': round(gross_tot, 2) or 0.0,
                                    }

        updated_folio = []
        folio_search = self.env['hotel.folio'].search([('company_id','=',data.hotel_id.company_id.id)])
        if folio_search:
            for folio in folio_search:
                if folio.room_lines:
                    for date in folio.room_lines:
                        history_start_date = date.checkin_date
                        history_end_date = date.checkout_date

                        if (history_start_date <= reservation_start_date < history_end_date) or (
                                history_start_date < reservation_end_date <= history_end_date) or (
                                (reservation_start_date < history_start_date) and (
                                reservation_end_date >= history_end_date)):
                            if not (folio in updated_folio):
                                updated_folio.append(folio)
            day_count = (reservation_end_date - reservation_start_date).days
            if not updated_folio:
                for count in range(0, (int(day_count) + 1)):
                    result_dic = {}
                    single_date = reservation_start_date + timedelta(days=count)
                    single_date = str(single_date)
                    single_date = single_date[0:10]

                    result_dic = {
                        'date': single_date,
                        'no_booked_room': 0,
                        'occ_percent': 0,
                        'tot_rent': 0,
                        'tot_service': 0,
                        'tot_rest': 0,
                        'tot_laundry': 0,
                        'tot_trans': 0,
                        'tot_sub': 0,
                        'tot_tax': 0,
                        'gross_tot': 0,
                    }
                    result_list.append(result_dic)

            else:
                total_room = len(self.env['hotel.room'].search([('shop_id','=',data.hotel_id.id)]))
                for count in range(0, (int(day_count) + 1)):
                    result_dic = {}
                    single_date = (reservation_start_date + timedelta(days=count)).strftime("%Y-%m-%d")
                    if not single_date in date_list:
                        date = single_date
                        end_date = date
                        start_date = single_date
                        room_no = 0.0
                        rent_amt = 0.0
                        service_rent = 0.0
                        rest_amt = 0.0
                        laundry_amt = 0.0

                        tax = 0
                        rest_tax = 0.0
                        laundry_tax = 0.0
                        for folio in updated_folio:
                            for line_date in folio.room_lines:
                                if line_date.name != 'All Meals':
                                    history_start_date = line_date.checkin_date.strftime("%Y-%m-%d")
                                    history_end_date = line_date.checkout_date.strftime("%Y-%m-%d")
                                    if (history_start_date <= start_date < history_end_date) or (
                                        history_start_date < end_date < history_end_date) or (
                                        (start_date < history_start_date) and (end_date >= history_end_date)):

                                        no_days = int(line_date.product_uom_qty)
                                        room_no += len(line_date)
                                        if no_days > 0:
                                            tax = folio.amount_tax / no_days
                                        else:
                                            tax = 0.0
                                        if no_days > 0:
                                            rent_amt += line_date.price_subtotal / no_days
                                        else:
                                            rent_amt = 0.0
                                        for service in folio.service_lines:
                                            if no_days > 0:
                                                service_rent += service.price_subtotal / no_days
                                            else:
                                                service_rent = 0.0

                                        calculated_origins = []
                                        for laundry_data in folio.laundry_line_ids:
                                            if str(laundry_data.source_origin) not in calculated_origins:
                                                laundry_data_search = self.env['laundry.management'].search([
                                                ('name', '=', laundry_data.source_origin)])
                                                for laundry_data_id in laundry_data_search:
                                                    if str(laundry_data_id.date_order)[0:10] == date:
                                                        laundry_tax += laundry_data_id.amount_tax
                                                        laundry_amt += laundry_data_id.amount_subtotal
                                            calculated_origins.append(str(laundry_data.source_origin))

                                        for table_data in folio.food_lines:
                                            table_search = self.env['hotel.restaurant.order'].search([
                                            ('order_no', '=', table_data.source_origin)])
                                            order_search = self.env['hotel.reservation.order'].search([
                                            ('order_number', '=', table_data.source_origin)])

                                            if table_search:
                                                table_id = table_search
                                                if table_search:
                                                    if table_search.o_date == date:
                                                        rest_tax = table_search.amount_tax
                                                        rest_amt = table_search.amount_subtotal
                                            else:
                                                order_id = order_search
                                                if order_search:
                                                    if order_search.date1 == date:
                                                        rest_tax = order_search.amount_tax
                                                        rest_amt = order_search.amount_subtotal

                        tax = tax + rest_tax + laundry_tax
                        tot_sub = rent_amt + service_rent + rest_amt + laundry_amt
                        # gross_tot = tot_sub + tax
                        gross_tot = tot_sub
                        if (type('date')) == str:
                            date = fields.Datetime.from_string(date)
                        result_dic = {
                            'date': date,
                            'total_room_avail': total_room,
                            'no_booked_room': room_no,
                            'occ_percent': (room_no * 100) / total_room,
                            'tot_rent': round(rent_amt, 2),
                            'tot_service': round(service_rent, 2),
                            'tot_rest': round(rest_amt, 2),
                            'tot_laundry': round(laundry_amt, 2),
                            'tot_sub': round(tot_sub, 2),
                            # 'tot_tax': round(tax, 2),
                            'gross_tot': round(gross_tot, 2),
                        }
                    result_list.append(result_dic)
        newlist = sorted(result_list, key=itemgetter('date'))

        return newlist

    def _get_report_values(self, docids, data=None):
        order = self.env['monthly.occupancy.wizard'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'monthly.occupancy.wizard',
            'data': data,
            'docs': order,
            'get_monthly_occupancy_information': self.get_monthly_occupancy_information,
        }

    


class monthly_occupency(models.AbstractModel):
    _name = 'report.hotel_management.monthly_occupency_revenue_report_view'
    _description = 'Occupancy Report View'

    def get_monthly_occupancy_revenue_information(self, data):
        
        date_start = data.start_date
        date_stop = data.end_date
        reservation_start_date = datetime.combine(date_start, datetime.min.time())
        reservation_end_date = datetime.combine(date_stop, datetime.min.time())
        result_list = []
        date_totals = {}  
        folio_search = self.env['hotel.folio'].search([('company_id', '=', data.hotel_id.company_id.id)])
        if folio_search:
            for folio in folio_search:
                if folio.room_lines:
                    for date in folio.room_lines:
                        history_start_date = date.checkin_date
                        history_end_date = date.checkout_date

                        if (history_start_date <= reservation_start_date < history_end_date) or (
                            history_start_date < reservation_end_date <= history_end_date) or (
                            (reservation_start_date < history_start_date) and (
                            reservation_end_date >= history_end_date)):
                            if date.product_id.name.lower() == 'Breakfast':
                                continue 
                            if date.product_id.name.lower() == 'Breakfast And Dinner':
                                continue 
                            if date.product_id.name.lower() == 'All Meals':
                                continue 

                            current_date = date.checkin_date
                            while current_date < date.checkout_date:
                                if current_date not in date_totals:
                                    date_totals[current_date] = {
                                        'room_details': [],
                                        'total_room_rent': 0,
                                        'total_service': 0,
                                        'total_laundry': 0,
                                        'total_restaurant': 0,
                                        'total_pos': 0,
                                        'total_transportation': 0,
                                        'total_tax': 0,
                                        'total_amount': 0,
                                    }
                                hotel_service = 0
                                laundry = 0
                                restaurant = 0
                                transportation = 0
                                pos = 0
                                tax = folio.amount_tax

                                for service in folio.service_lines:
                                    hotel_service += service.price_subtotal

                                for food in folio.food_lines:
                                    restaurant += food.price_subtotal

                                for laundry_line in folio.laundry_line_ids:
                                    laundry += laundry_line.price_subtotal

                                for transport in folio.transport_line_ids:
                                    transportation += transport.price_subtotal

                                for pos_id in folio.pos_order_ids:
                                    pos += pos_id.amount_total

                                date_totals[current_date]['room_details'].append({
                                    'room_name': date.product_id.name,
                                    'checked_in': 'Yes',
                                    'checked_out': 'Yes' if folio.state in('check_out','done') else 'No',
                                    'room_rent': date.price_subtotal,
                                    'hotel_service': hotel_service,  # Adjust if hotel service is available
                                    'laundry': laundry,  # Adjust if laundry charges are available
                                    'restaurant': restaurant,  # Adjust if restaurant charges are available
                                    'transportation': transportation, 
                                    'pos': pos,
                                    'tax': tax,  # Adjust if transportation charges are available
                                    'total': date.price_subtotal+ hotel_service+laundry+restaurant+transportation+pos+tax,
                                })
                                date_totals[current_date]['total_room_rent'] += date.price_subtotal
                                date_totals[current_date]['total_service'] += hotel_service
                                date_totals[current_date]['total_laundry'] += laundry
                                date_totals[current_date]['total_restaurant'] += restaurant
                                date_totals[current_date]['total_pos'] += pos
                                date_totals[current_date]['total_transportation'] += transportation
                                date_totals[current_date]['total_tax'] += tax
                                # Add additional services and charges here
                                date_totals[current_date]['total_amount'] += (date.price_subtotal + hotel_service + laundry + restaurant + transportation + pos + tax)
                                current_date += timedelta(days=1)

        for date, data in sorted(date_totals.items()):
            for room in data['room_details']:
                if room['room_name'] == 'All Meals':
                    continue
                if room['room_name'] == 'Breakfast And Dinner':
                    continue
                if room['room_name'] == 'Breakfast':
                    continue
                result_list.append({
                'date': date.strftime('%Y-%m-%d'),
                'room_name': room['room_name'],
                'checked_in': room['checked_in'],
                'checked_out': room['checked_out'],
                'room_rent': room['room_rent'],
                'hotel_service': room['hotel_service'],
                'laundry': room['laundry'],
                'restaurant': room['restaurant'],
                'transportation': room['transportation'],
                'pos': room['pos'],
                'tax': room['tax'],
                'total': room['total'],
            })
            result_list.append({
            'date': date.strftime('%Y-%m-%d'),
            'room_name': 'Total of ' + date.strftime('%d/%m/%Y'),
            'checked_in': '',
            'checked_out': '',
            'room_rent': data['total_room_rent'],
            'hotel_service': data['total_service'],
            'laundry': data['total_laundry'],
            'restaurant': data['total_restaurant'],
            'transportation': data['total_transportation'],
            'pos': data['total_pos'],
            'tax': data['total_tax'],
            'total': data['total_amount'],
        })
        return result_list

    def _get_report_values(self, docids, data=None):
        order = self.env['monthly.occupancy.revenue.wizard'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'monthly.occupancy.revenue.wizard',
            'data': data,
            'docs': order,
            'get_monthly_occupancy_revenue_information': self.get_monthly_occupancy_revenue_information,
        }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

