// Part of Odoo. See LICENSE file for full copyright and licensing details.

import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";


patch(ProductCard.prototype, {
    get formattedPrice() {
        const product = this.props.product;

        if (product && this.pos) {
            return this.pos.getProductPriceFormatted(product);
        }
        return '';
    },

    setup() {
        this._super?.(...arguments);
        this.pos = usePos();
    },
});