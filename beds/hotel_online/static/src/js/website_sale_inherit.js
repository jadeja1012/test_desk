/** @odoo-module **/
import wUtils from "@website/js/utils";
import publicWidget from "@web/legacy/js/public/public_widget";
import { WebsiteSale } from '@website_sale/js/website_sale';

$(function (require) {
    'use strict';

    // var publicWidget = require('@web/legacy/js/public/public_widget');
    // var WebsiteSale = require('website_sale.website_sale')
    // const wUtils = require('website.utils');

    publicWidget.registry.WebsiteSale.include({

        /**
         * @override
         */
        _onClickAdd: function (ev) {
            ev.preventDefault();
            var self = this
            this.getCartHandlerOptions(ev);
            var $form = $(ev.currentTarget).closest('form')
            
            var productID = $form.find('.product_id').val()
            var qty_id = $form.find('.quantity').val()
            
            wUtils.sendRequest('/shop/cart/update', {
                product_id: productID,
                add_qty:qty_id,
                express: true,

            });
            
            return self._super.apply(this, arguments)

        },
    })

});