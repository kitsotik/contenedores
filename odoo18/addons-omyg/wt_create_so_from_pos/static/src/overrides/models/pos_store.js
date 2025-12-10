import { _t } from "@web/core/l10n/translation";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { ask, makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { ConfirmationDialog, AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PosStore.prototype, {
	async onClickSaleOrder(clickedOrderId) {
		const sale_order = await this._getSaleOrder(clickedOrderId);
		const option_list = this.getSalePrderActions()
		if(['draft','sent'].includes(sale_order.state)){
			option_list.push({ id: "0", label: _t("Confirm Order"), item: "confirmOrder" })
		}
		if(sale_order.state !== 'cancel'){
			option_list.push({id: "1",label: _t("Cancel Order"),item: "cancleOrder",})
		}
		if(!option_list.length){
			await super.onClickSaleOrder(...arguments);
		}else{
			option_list.push({id: "2",label: _t("More Options"),item: "moreOptions",})
			const selectedOption = await makeAwaitable(this.dialog, SelectionPopup, {
				title: _t("What do you want to do?"),
				list: option_list,
			});
			if (!selectedOption) {
				return;
			}
			if(selectedOption === "confirmOrder"){
				await this.data.call('sale.order', 'action_confirm', [clickedOrderId]);
			}else if(selectedOption === "cancleOrder"){
				this.dialog.add(ConfirmationDialog, {
	                title: _t('Sale Confirmation'),
	                body: _t("Are you sure you want to Cancle %s Order!!!!",sale_order.name),
	                confirmLabel: _t("Cancel Order"),
	                cancelLabel: _t("Discard"),
	                confirm: () => {
	                    this.data.call('sale.order', 'action_cancel', [clickedOrderId], {context:{'disable_cancel_warning':true}});
	                },
	                cancel: async () => {},
	                dismiss: async () => {},
	            });
			}else if(selectedOption === 'moreOptions'){
				await super.onClickSaleOrder(...arguments);
			}else{
				await this.handleSaleOrderAction(selectedOption)
			}
		}
	},
	getSalePrderActions(){
		/*Add new action option*/
		// const actions = super.getSalePrderActions()
		// actions.push({ id: actions.length + 1, label: _t("Action Name"), item: "action_item" })
		return []
	},
	async handleSaleOrderAction(action){
		/*you will recive selected action item hear*/
		return;
	},
})