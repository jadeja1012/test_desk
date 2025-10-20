/* @odoo-module */
//
// import { Order} from "@point_of_sale/app/store/models";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

	patch(PosStore.prototype, {
		// @Override
		async processServerData() {
			await super.processServerData();
			this.hotel_folio = await this.data.orm.call('hotel.folio', 'search_read', [])
			this.hotel_room_book_history = await this.data.orm.call('hotel.room.booking.history', 'search_read', [])
			this.sale_shop = await this.data.orm.call('sale.shop', 'search_read', []);
			this.hotel_rest_table = await this.data.orm.call('hotel.restaurant.tables', 'search_read', []);
			this.hotel_rest_kitchen = await this.data.orm.call('hotel.restaurant.kitchen.order.tickets', 'search_read', []);
			this.hotel_rest_reserve = await this.data.orm.call('hotel.restaurant.reservation', 'search_read', []);
			this.hotel_reserve = await this.data.orm.call('hotel.reservation', 'search_read', []);
			this.hotel_folio_line_ = await this.data.orm.call('hotel_folio.line', 'search_read', []);
			console.log(this.hotel_folio)
			console.log(this.hotel_room_book_history)
			console.log(this.sale_shop)
			console.log(this.hotel_rest_table)
			console.log(this.hotel_rest_kitchen)
			console.log(this.hotel_rest_reserve)
			console.log(this.hotel_reserve)
			console.log(this.hotel_folio_line_)

		},
	});

	
	patch(PosOrder.prototype, {
		setup() {
			super.setup(...arguments);
			this.folio_line_id = this.folio_line_id || false;
			this.folio_ids = this.folio_ids || false;
			this.room_name = this.room_name || false;
			this.payatcheckout = false
			},

            // pass data from frontend to backend
			serialize() {
                const data = super.serialize(...arguments);
                data.folio_line_id = this.get_folio_line_id() || this.folio_line_id;
                data.folio_ids = this.get_folio_ids() || this.folio_ids;
                return data;
            },

			set_folio_line_id(folio) {

				this.folio_line_id = folio;
			},
			get_folio_line_id() {

				return this.folio_line_id;
			},
	
			set_folio_ids(folio_id) {

				this.folio_ids = folio_id;
			},
			get_folio_ids() {

				return this.folio_ids;
			},
	
			set_room_name(room) {

				this.room_name = room;
			},
			get_room_name() {

				return this.room_name;
			},
	
			init_from_JSON(json) {

				super.init_from_JSON(...arguments);
				this.folio_line_id = json.folio_line_id;
				this.folio_ids = json.folio_ids;
				this.room_name = json.room_name;
			},
	
			export_as_JSON() {

				let orderJson = super.export_as_JSON(...arguments);
				orderJson.folio_line_id = this.get_folio_line_id();
				orderJson.folio_ids = this.get_folio_ids();
				orderJson.room_name = this.get_room_name();
				return orderJson;
			},
	
			export_for_printing(baseUrl, headerData) {
				let Json = super.export_for_printing(...arguments);
				Json.folio_line_id = this.get_folio_line_id();
				Json.folio_ids = this.get_folio_ids();
				Json.room_name = this.get_room_name();
				return Json;
			}
		})


	