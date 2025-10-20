/** @odoo-module */

/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { serializeDateTime } from "@web/core/l10n/dates";
import { ConnectionLostError, RPCError } from "@web/core/network/rpc";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
patch(PaymentScreen.prototype, {
    setup() {
		this.report = useService("report");
		this.pos = usePos();
        super.setup(...arguments);
		this.orm = useService("orm")
            onMounted(() => {
				const order = this.pos.get_order();
        		this.pos.addPendingOrder([order.id]);

        			for (const payment of order.payment_ids) {
            		const pmid = payment.payment_method_id.id;
					if (!this.pos.config.payment_method_ids.map((pm) => pm.id).includes(pmid)) {
						payment.delete({ backend: true });
					}
        }

        if (this.payment_methods_from_config.length == 1) {
            this.addNewPaymentLine(this.payment_methods_from_config[0]);
        }
				var self = this;
					var room = self.pos.get_order().get_room_name();
					if (room) {
						document.getElementById('payatcheckout').style.display = 'block';
						document.querySelectorAll('.js_room_name').forEach(function(element) {
							element.textContent = room ? room : _t('Room');
						});
					}
				
				})
    },
	get currentOrder() {
		
		if(this.props.orderUuid){
			console.log("bbbbbbbbbbbbbbbbbbbbbbbbbbbbb",this.props.orderUuid)
        return this.pos.models["pos.order"].getBy("uuid", this.props.orderUuid);
		}
		else{
			console.log("cccccccccccccccccccccccccccccccccc",this.pos.selectedOrderUuid)
			this.props.orderUuid = this.pos.selectedOrderUuid
			return this.pos.models["pos.order"].getBy("uuid", this.pos.selectedOrderUuid)
		}
    },
	click_set_room() {
						console.log("Set Room Function")
		
						this.pos.showScreen('RoomListScreenWidget');
						
					},
	finalize_validation() {
			var self = this;
			var order = this.pos.get_order();
			if (order.is_paid_with_cash() && this.pos.config.iface_cashdrawer) {

				this.pos.proxy.open_cashbox();
			}

			order.initialize_validation_date();
			if (order.is_to_invoice()) {
				var invoiced = this.pos.push_and_invoice_order(order);
				this.invoicing = true;

				invoiced.fail(function (error) {
					self.invoicing = false;
					if (error.message === 'Missing Customer') {
						self.gui.show_popup('confirm', {
							'title': _t('Please select the Customer'),
							'body': _t('You need to select the customer before you can invoice an order.'),
							confirm: function () {
								self.gui.show_screen('clientlist');
							},
						});
					} else if (error.code < 0) {        // XmlHttpRequest Errors
						self.gui.show_popup('error', {
							'title': _t('The order could not be sent'),
							'body': _t('Check your internet connection and try again.'),
						});
					} else if (error.code === 200) {    // OpenERP Server Errors
						self.gui.show_popup('error-traceback', {
							'title': error.data.message || _t("Server Error"),
							'body': error.data.debug || _t('The server encountered an error while receiving your order.'),
						});
					} else {                            // ???
						self.gui.show_popup('error', {
							'title': _t("Unknown Error"),
							'body': _t("The order could not be sent to the server due to an unknown error"),
						});
					}
				});

				invoiced.done(function () {
					self.invoicing = false;
					if (order.room_name != '' && order.folio_ids != '') {
						order.finalize();
						self.gui.show_screen('products');
					} else {
						self.gui.show_screen('receipt');
					}
				});
			} else {
				this.pos.push_order(order);
				this.gui.show_screen('receipt');
			}
		},


	

		async payatcheckout(isForceValidate){
			this.numberBuffer.capture();
			//if (this.pos.config.cash_rounding) {
				//if (!this.pos.get_order().check_paymentlines_rounding()) {
					//.popup.add(ErrorPopup, {
					//	title: _t("Rounding error in payment lines"),
						//body: _t(
						//	"The amount of your payment lines must be rounded to validate the transaction."
						//),
					//});
					//return;
				//}
			//}
			if (await this.isOrderValids(isForceValidate)) {
				// remove pending payments before finalizing the validation
				for (const line of this.paymentLines) {
					if (!line.is_done()) {
						this.currentOrder.remove_paymentline(line);
					}
				}
				await this._finalizeValidation();
				this.currentOrder.payatcheckout = true
			}
		},

		async isOrderValids(isForceValidate) {
			if (this.currentOrder.get_orderlines().length === 0 && this.currentOrder.is_to_invoice()) {
				this.dialog.add(AlertDialog, {
					title: _t("Empty Order"),
					body: _t(
						"There must be at least one product in your order before it can be validated and invoiced."
					),
				});
				return false;
			}
	
			if ((await this._askForCustomerIfRequired()) === false) {
				return false;
			}
	
			if (
				(this.currentOrder.is_to_invoice() || this.currentOrder.getShippingDate()) &&
				!this.currentOrder.get_partner()
			) {
				const confirmed = await ask(this.dialog, {
					title: _t("Please select the Customer"),
					body: _t(
						"You need to select the customer before you can invoice or ship an order."
					),
				});
				if (confirmed) {
					this.pos.selectPartner();
				}
				return false;
			}
	
			const partner = this.currentOrder.get_partner();
			if (
				this.currentOrder.getShippingDate() &&
				!(partner.name && partner.street && partner.city && partner.country_id)
			) {
				this.dialog.add(AlertDialog, {
					title: _t("Incorrect address for shipping"),
					body: _t("The selected customer needs an address."),
				});
				return false;
			}
	
			// if (
			// 	this.currentOrder.get_total_with_tax() != 0 &&
			// 	this.currentOrder.payment_ids.length === 0
			// ) {
			// 	this.notification.add(_t("Select a payment method to validate the order."));
			// 	return false;
			// }
	
			// if (!this.currentOrder.is_paid() || this.invoicing) {
			// 	return false;
			// }
	
			if (this.currentOrder.get_rounding_applied() && this.pos.config.cash_rounding) {
				var line = this.currentOrder.get_rounding_applied();
				this.dialog.add(AlertDialog, {
					title: _t("Incorrect rounding"),
					body: _t(
						"You have to round your payments lines." + line.amount + " is not rounded."
					),
				});
				return false;
			}
	
			// The exact amount must be paid if there is no cash payment method defined.
			if (
				Math.abs(
					this.currentOrder.get_total_with_tax() -
						this.currentOrder.get_total_paid() +
						this.currentOrder.get_rounding_applied()
				) > 0.00001
			) {
				if (!this.pos.models["pos.payment.method"].some((pm) => pm.is_cash_count)) {
					this.dialog.add(AlertDialog, {
						title: _t("Cannot return change without a cash payment method"),
						body: _t(
							"There is no cash payment method available in this point of sale to handle the change.\n\n Please pay the exact amount or add a cash payment method in the point of sale configuration"
						),
					});
					return false;
				}
			}
	
			// if the change is too large, it's probably an input error, make the user confirm.
			if (
				!isForceValidate &&
				this.currentOrder.get_total_with_tax() > 0 &&
				this.currentOrder.get_total_with_tax() * 1000 < this.currentOrder.get_total_paid()
			) {
				this.dialog.add(ConfirmationDialog, {
					title: _t("Please Confirm Large Amount"),
					body:
						_t("Are you sure that the customer wants to  pay") +
						" " +
						this.env.utils.formatCurrency(this.currentOrder.get_total_paid()) +
						" " +
						_t("for an order of") +
						" " +
						this.env.utils.formatCurrency(this.currentOrder.get_total_with_tax()) +
						" " +
						_t('? Clicking "Confirm" will validate the payment.'),
					confirm: () => this.validateOrder(true),
				});
				return false;
			}
	
			if (!this.currentOrder._isValidEmptyOrder()) {
				return false;
			}
	
			return true;

		}

		
			});



patch(ReceiptScreen.prototype, {

	get orderAmountPlusTip() {
        const order = this.currentOrder;
        const orderTotalAmount = order.get_total_with_tax();
		if (orderTotalAmount){
			const tip_product_id = this.pos.config.tip_product_id?.id;
        const tipLine = order
            .get_orderlines()
            .find((line) => tip_product_id && line.product_id.id === tip_product_id);
        const tipAmount = tipLine ? tipLine.get_all_prices().priceWithTax : 0;
        const orderAmountStr = this.env.utils.formatCurrency(orderTotalAmount - tipAmount);
        if (!tipAmount) {
            return orderAmountStr;
        }
        const tipAmountStr = this.env.utils.formatCurrency(tipAmount);
        return `${orderAmountStr} + ${tipAmountStr} tip`;
		}else{
		const orderTotalAmount = order.amount_total;
		const tip_product_id = this.pos.config.tip_product_id?.id;
        const tipLine = order
            .get_orderlines()
            .find((line) => tip_product_id && line.product_id.id === tip_product_id);
        const tipAmount = tipLine ? tipLine.get_all_prices().priceWithTax : 0;
        const orderAmountStr = this.env.utils.formatCurrency(orderTotalAmount - tipAmount);
        if (!tipAmount) {
            return orderAmountStr;
        }
        const tipAmountStr = this.env.utils.formatCurrency(tipAmount);
        return `${orderAmountStr} + ${tipAmountStr} tip`;
		}
        
    }

})


