import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { ConfirmationDialog, AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";

patch(ControlButtons.prototype, {
    setup(){
        super.setup()
        this.dialogService = useService("dialog");
    },
    async clickCreateSaleOrder(){
        var self = this
        const order = this.pos.get_order();
        const partner = order.get_partner();
        if(!partner){
            this.dialogService.add(AlertDialog, {
                body: _t("Select Customer."),
                title: _t("Missing Customer"),
                confirm: () => {},
                confirmLabel: _t("Close"),
            });
            return;
        }
        if(!order.get_orderlines().length){
            this.dialogService.add(AlertDialog, {
                body: _t("There are no Product for SaleOrder."),
                title: _t("Missing File"),
                confirm: () => {},
                confirmLabel: _t("Close"),
            });
            return;
        }
        const oderdetails = {};
        for (const line of order.get_orderlines()) {
            oderdetails[line.id] = { 
                product: line.get_product().id, 
                quantity: line.qty,
                price: line.price_unit,
                discount: line.discount,
            };
        }
        oderdetails['partner_id'] = order.get_partner().id
        if(order.get_total_tax() > 0){
            oderdetails['tax_amount'] = order.get_total_tax()
        }
        const result = await this.pos.data.call("sale.order", "craete_saleorder_from_pos", [oderdetails]);
        if(result){
            this.dialog.add(ConfirmationDialog, {
                title: _t('Successfully!'),
                body: _t("Sales Order %s Created Successfully!!!!",result.name),
                confirmLabel: _t("Confirm Order"),
                cancelLabel: _t("Ok"),
                confirm: () => {
                    this.pos.data.call('sale.order', 'action_confirm', [result.id]);
                },
                cancel: async () => {},
                dismiss: async () => {},
            });
            order.set_partner(false);
        }
        const lines = [];
        for (const line of order.get_orderlines()) {
            lines.push(line)
        }
        for (var l = 0; l < lines.length; l++) {
            lines[l].delete()
        }
    }
});