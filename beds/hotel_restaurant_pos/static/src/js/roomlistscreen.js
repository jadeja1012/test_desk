/* @odoo-module */

    // const { Gui } = require('point_of_sale.Gui');
    // import { PosCollection } from '@point_of_sale/app/store/models';
    import { PosOrder } from "@point_of_sale/app/models/pos_order";
    import { usePos } from "@point_of_sale/app/store/pos_hook";
    import { renderToElement } from '@web/core/utils/render';
    import { useService } from "@web/core/utils/hooks";
    // import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
    // var models = PosCollection

    // var core = require('web.core');
    // var QWeb = core.qweb;
    import {_t} from "@web/core/l10n/translation";
    import { Component, onMounted, useState, useRef, useContext  } from "@odoo/owl";
    // const PosComponent = require('point_of_sale.PosComponent');
    import { registry } from "@web/core/registry";
    // const Registries = require('point_of_sale.Registries');

    class RoomListScreenWidget extends Component {
        
        static template = 'RoomListScreenWidget';
            setup() {
                this.pos = usePos();
                
                super.setup(...arguments);
                this.loading = useState({
                    message: 'Loading',
                    skipButtonIsShown: false,
                    
                });
                this.orm = useService("orm");
                this.mainScreen = useState({ name: null, component: null });
                this.mainScreenProps = {};
    
                this.tempScreen = useState({ isShown: false, name: null, component: null });
                this.tempScreenProps = {};
    
                this.progressbar = useRef('progressbar');
                onMounted(() => {
                    
                    this.show();
                    
                });
                
                }
//       
        destroy() {
            super.destroy(...arguments);
            this.pos.destroy();
        }
        catchError(error) {
            console.error(error);
        }
        render_room_list(rooms) {
            var d = new Date();
            var current_date = new Date(String(d.getFullYear()) + "-" + String(d.getMonth() + 1) + "-" + String(d.getDate())).setHours(0, 0, 0, 0);
            var contents = document.querySelector('.room-list-contents');
            

            contents.innerHTML = "";
            var hotel_folio = this.pos.hotel_folio;
            for (var i = 0, len = Math.min(rooms.length, 1000); i < len; i++) {
               console.log("ffffffffffffffffffffffvvvvvvvvvvvvvvvvvvvvv",rooms[i].folio_id)
                var room = rooms[i];
                var checkin = room.checkin_date;
                var checkin_dt = new Date(checkin.split(" ")[0]).setHours(0, 0, 0, 0);
                var checkout = room.checkout_date;
                var checkout_dt = new Date(checkout.split(" ")[0]).setHours(0, 0, 0, 0);
                
                if (checkin_dt <= current_date ) {
                    for (var j = 0; j < hotel_folio.length; j++) {
                        if ((hotel_folio[j].state === 'draft')&&(room.folio_id[0] === hotel_folio[j].id)) {
                            if (room) {
                                var roomline_html = renderToElement('RoomLine', { room: rooms[i] });
                            
                            }
                           
                            contents.appendChild(roomline_html);
                        }
                    }
                }
            }
        }
        back() {
             var self = this;
           self.env.services.pos.showScreen("PaymentScreen", {
                    orderUuid: self.pos.selectedOrderUuid,
                });
        }
        show() {
            var poss =this.pos
            var self = this;
            this.details_visible = false;
            console.log(this.pos);
            var rooms = this.pos.hotel_folio_line_;
            var hotel_folio = this.pos.hotel_folio
            /**
                Loading partner id and partner name in room object
            */
            for (var i = 0, len = Math.min(rooms.length, 1000); i < len; i++) {
                var room = rooms[i];
                for (var j = 0; j < hotel_folio.length; j++) {
                    if (hotel_folio[j].state === 'draft') {
                        if (room.folio_id[0] === hotel_folio[j].id) {
                            room['partner_id'] = hotel_folio[j].partner_id[0];
                            room['partner_name'] = hotel_folio[j].partner_id[1];
                            break;
                        }
                    }
                }
            }

            /**
                Rendering Room object
            */
            this.render_room_list(rooms);
            

      
            document.addEventListener('click', function (event) {
                //this.orm = useService("orm");
                if (event.target.closest('.room-line')) {
                    var line_data;
                    var room_name;
                    var customer_name;
                    var pricelist_name;
                    var folio_line_id;
                    var folio_ids;
                    var partner;
        
                    var roomLine = event.target.closest('.room-line');

                    // Get partner ID from the third child
                    var partner_id = roomLine.children[2].dataset.custId;
                     
                         //const partner_new =  self.getNewPartners();
                         //console.log("1111111111111111111111111111111",partner_new)
                        var bbb = poss.models["res.partner"].getAll()
                        partner = poss.models["res.partner"].get(roomLine.children[2].dataset.custId)
                         if (partner) {
                            poss.get_order().set_partner(partner)
                         }
                          if (!partner) {
                            poss.get_order().set_partner()
                         }
                        


                    
                    customer_name = roomLine.children[2].textContent;
                    
                    room_name = roomLine.children[0].textContent;

                    folio_ids = parseInt(roomLine.children[1].dataset.folioId);

                    folio_line_id = parseInt(roomLine.dataset.id);

                    poss.get_order().set_folio_ids(folio_ids);
                    poss.get_order().set_folio_line_id(folio_line_id);
                    poss.get_order().set_room_name(room_name);
                    
                    
					document.querySelectorAll('.js_room_name').forEach(function(element) {
                        element.textContent = room_name ? room_name : _t('Room');
                    });

                    
                    document.querySelectorAll('.js_customer_name').forEach(function(element) {
                        element.textContent = customer_name ? customer_name : _t('Customer');
                    });
                    
                    
                    document.querySelectorAll('.set-customer').forEach(function(element){
                        element.textContent = customer_name ? customer_name : _t('Customer');

                    })
                    
        
                    
                    poss.get_order().updatePricelistAndFiscalPosition(partner);
                   // self.back();
                      self.env.services.pos.showScreen("PaymentScreen", {
                    orderUuid: self.pos.selectedOrderUuid,
                });
                        
                 
                    
                    
                }
            });
      
        
            
        };
       
    }
   
    registry.category("pos_screens").add("RoomListScreenWidget", RoomListScreenWidget);

   

    return RoomListScreenWidget;

