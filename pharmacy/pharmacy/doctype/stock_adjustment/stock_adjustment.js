// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.stock");
frappe.provide("erpnext.accounts.dimensions");

frappe.ui.form.on("Stock Adjustment", {
	setup(frm) {
		frm.ignore_doctypes_on_cancel_all = ['Serial and Batch Bundle'];
		// filter uom based on item
		frm.set_query('uom','items', function(doc, cdt, cdn) {
			let row = locals[cdt][cdn];
			 return {
				 query: "pharmacy.controllers.stock_adjustment_item.get_item_uom",
				 filters: {
					 'item_code': row.item_code
				 }
			 }
		 })
	},
	validate: function(frm) {
		if(frm.doc.items) {
			frm.doc.items.forEach(function(row) {
				if(row.item_code && row.warehouse)
				{
					frappe.call({
						method: "pharmacy.pharmacy.doctype.stock_adjustment.stock_adjustment.get_items",
						args: {
							warehouse: row.warehouse,
							posting_date: frm.doc.posting_date,
							posting_time: frm.doc.posting_time,
							company: frm.doc.company,
							item_code: row.item_code,
							ignore_empty_stock: 0},
						callback: function(r) {
							row.current_valuation_rate = r.message[0].current_valuation_rate;
							if(r.message[0].qty && row.ignore_calculations == 0){
								row.current_qty = r.message[0].qty;
							}
							row.batch_no = r.message[0].batch_no;
							row.current_serial_no = r.message[0].current_serial_no;
							frm.refresh_field("items");
						}
					});
				}
			})
		}
	},

	onload: function(frm) {
		frm.add_fetch("item_code", "item_name", "item_name");

		// end of life
		frm.set_query("item_code", "items", function(doc, cdt, cdn) {
			return {
				query: "erpnext.controllers.queries.item_query",
				filters:{
					"is_stock_item": 1
				}
			}
		});
		frm.set_query("batch_no", "items", function(doc, cdt, cdn) {
			var item = locals[cdt][cdn];
			return {
				filters: {
					'item': item.item_code
				}
			};
		});

		frm.set_query("serial_and_batch_bundle", "items", (doc, cdt, cdn) => {
			let row = locals[cdt][cdn];
			return {
				filters: {
					'item_code': row.item_code,
					'voucher_type': doc.doctype,
					'voucher_no': ["in", [doc.name, ""]],
					'is_cancelled': 0,
				}
			}
		});

		let sbb_field = frm.get_docfield('items', 'serial_and_batch_bundle');
		if (sbb_field) {
			sbb_field.get_route_options_for_new_doc = (row) => {
				return {
					'item_code': row.doc.item_code,
					'warehouse': row.doc.warehouse,
					'voucher_type': frm.doc.doctype,
				}
			};
		}

		if (frm.doc.company) {
			erpnext.queries.setup_queries(frm, "Warehouse", function() {
				return erpnext.queries.warehouse(frm.doc);
			});
		}

		if (!frm.doc.expense_account) {
			frm.trigger("set_expense_account");
		}

		erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);
		if(frm.is_new()){
			frm.set_value('items',[])
		}
	},

	company: function(frm) {
		frm.trigger("toggle_display_account_head");
		erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
	},

	refresh: function(frm) {
		if(frm.doc.docstatus < 1) {
			frm.add_custom_button(__("Fetch Items from Warehouse"), function() {
				frm.events.get_items(frm);
			});
		}

		if(frm.doc.company) {
			frm.trigger("toggle_display_account_head");
		}
		frm.set_query('item_code', () => {
			return {
				filters: {
					is_stock_item: 1,
					disabled: 0
				}
			}
		})
	},

	scan_barcode: function(frm) {
		const barcode_scanner = new erpnext.utils.BarcodeScanner({frm:frm});
		barcode_scanner.process_scan();
	},

	scan_mode: function(frm) {
		if (frm.doc.scan_mode) {
			frappe.show_alert({
				message: __("Scan mode enabled, existing quantity will not be fetched."),
				indicator: "green"
			});
		}
	},

	set_warehouse: function(frm) {
		let transaction_controller = new erpnext.TransactionController({frm:frm});
		transaction_controller.autofill_warehouse(frm.doc.items, "warehouse", frm.doc.set_warehouse);
	},

	get_items: function(frm) {
		let fields = [
			{
				label: 'Warehouse',
				fieldname: 'warehouse',
				fieldtype: 'Link',
				options: 'Warehouse',
				reqd: 1,
				"get_query": function() {
					return {
						"filters": {
							"company": frm.doc.company,
						}
					};
				}
			},
			{
				label: "Item Code",
				fieldname: "item_code",
				fieldtype: "Link",
				options: "Item",
			},
			{
				label: __("Ignore Empty Stock"),
				fieldname: "ignore_empty_stock",
				fieldtype: "Check"
			}
		];

		frappe.prompt(fields, function(data) {
			frappe.call({
				method: "pharmacy.pharmacy.doctype.stock_adjustment.stock_adjustment.get_items",
				args: {
					warehouse: data.warehouse,
					posting_date: frm.doc.posting_date,
					posting_time: frm.doc.posting_time,
					company: frm.doc.company,
					item_code: data.item_code,
					ignore_empty_stock: data.ignore_empty_stock
				},
				callback: function(r) {
					if (r.exc || !r.message || !r.message.length) return;
					console.log(r)
					frm.clear_table("items");

					r.message.forEach((row) => {
						let item = frm.add_child("items");
						$.extend(item, row);

						item.qty = item.qty || 0;
						item.valuation_rate = item.valuation_rate || 0;
					});
					frm.refresh_field("items");
				}
			});
		}, __("Get Items"), __("Update"));
	},

	posting_date: function(frm) {
		frm.trigger("set_valuation_rate_and_qty_for_all_items");
	},

	posting_time: function(frm) {
		frm.trigger("set_valuation_rate_and_qty_for_all_items");
	},

	set_valuation_rate_and_qty_for_all_items: function(frm) {
		frm.doc.items.forEach(row => {
			frm.events.set_valuation_rate_and_qty(frm, row.doctype, row.name);
		});
	},

	set_valuation_rate_and_qty: function(frm, cdt, cdn) {
		var d = frappe.model.get_doc(cdt, cdn);

		if(d.item_code && d.warehouse) {
			frappe.call({
				method: "erpnext.stock.doctype.stock_reconciliation.stock_reconciliation.get_stock_balance_for",
				args: {
					item_code: d.item_code,
					warehouse: d.warehouse,
					posting_date: frm.doc.posting_date,
					posting_time: frm.doc.posting_time,
					batch_no: d.batch_no
				},
				callback: function(r) {
					const row = frappe.model.get_doc(cdt, cdn);
					if (!frm.doc.scan_mode && d.ignore_calculations == 0) {
						frappe.model.set_value(cdt, cdn, "qty", r.message.qty);
					}
					frappe.model.set_value(cdt, cdn, "valuation_rate", r.message.rate);
					if(r.message.qty && d.ignore_calculations == 0){
						frappe.model.set_value(cdt, cdn, "current_qty", r.message.qty);
						frappe.model.set_value(cdt, cdn, "current_amount", r.message.rate * r.message.qty);
					}else{
						frappe.model.set_value(cdt, cdn, "current_amount", r.message.rate * d.qty);
					}
					frappe.model.set_value(cdt, cdn, "current_valuation_rate", r.message.rate);
					frappe.model.set_value(cdt, cdn, "amount", row.qty * row.valuation_rate);
					frappe.model.set_value(cdt, cdn, "current_serial_no", r.message.serial_nos);

					if (frm.doc.purpose == "Stock Reconciliation" && !frm.doc.scan_mode) {
						frappe.model.set_value(cdt, cdn, "serial_no", r.message.serial_nos);
					}
				}
			});
		}
	},

	set_amount_quantity: function(doc, cdt, cdn) {
		var d = frappe.model.get_doc(cdt, cdn);
		if (d.qty && d.valuation_rate) {
			frappe.model.set_value(cdt, cdn, "amount", flt(d.qty) * flt(d.valuation_rate));
			frappe.model.set_value(cdt, cdn, "quantity_difference", flt(d.qty) - flt(d.current_qty));
			frappe.model.set_value(cdt, cdn, "amount_difference", flt(d.amount) - flt(d.current_amount));
		}
	},
	toggle_display_account_head: function(frm) {
		frm.toggle_display(['expense_account', 'cost_center'],
			erpnext.is_perpetual_inventory_enabled(frm.doc.company));
	},
	purpose: function(frm) {
		frm.trigger("set_expense_account");
	},
	set_expense_account: function(frm) {
		if (frm.doc.company && erpnext.is_perpetual_inventory_enabled(frm.doc.company)) {
			return frm.call({
				method: "erpnext.stock.doctype.stock_reconciliation.stock_reconciliation.get_difference_account",
				args: {
					"purpose": frm.doc.purpose,
					"company": frm.doc.company
				},
				callback: function(r) {
					if (!r.exc) {
						frm.set_value("expense_account", r.message);
					}
				}
			});
		}
	},

	item_code(frm){
		let item_code = frm.doc.item_code
		if(item_code){
			frm.call('fetch_related_items').then(r=>{
				if(r.message){
					let items = r.message
					items.forEach(item=>{
						let child = frappe.model.add_child(frm.doc,"items")
						frappe.model.set_value("Stock Adjustment Item",child.name,{
							item_code: item.item_code,
							item_name: item.item_name,
							item_expiry_date: item.item_expiry_date,
							item_expiry_date_bk: item.item_expiry_date,
							using_date_expire: item.using_expiry_date,
							uom: item.sales_uom,
							warehouse: item.warehouse,
							current_qty: parseFloat(item.qty) || 0,
							qty: parseFloat(item.qty) || 0,
							stock_sales: parseFloat(item.stock_sales) || 0,
							ignore_calculations: 1
						})
					})
					frm.refresh_field('items')
					frm.set_value('item_code',null)
				}else{
					frm.set_value('item_code',null)
				}
			})
		}
	},
	scan_barcode_new(frm){
		let barcode = frm.doc.scan_barcode_new
		if(barcode){
			frm.call('fetch_related_items_barcode').then(r=>{
				if(r.message){
					let items = r.message
					items.forEach(item=>{
						let child = frappe.model.add_child(frm.doc,"items")
						frappe.model.set_value("Stock Adjustment Item",child.name,{
							item_code: item.item_code,
							item_name: item.item_name,
							item_expiry_date: item.item_expiry_date,
							item_expiry_date_bk: item.item_expiry_date,
							using_date_expire: item.using_expiry_date,
							uom: item.sales_uom,
							warehouse: item.warehouse,
							current_qty: parseFloat(item.qty) || 0,
							qty: parseFloat(item.qty) || 0,
							stock_sales: parseFloat(item.stock_sales) || 0,
							ignore_calculations: 1
						})
					})
					frm.refresh_field('items')
					frm.set_value('scan_barcode_new',null)
				}else{
					frm.set_value('scan_barcode_new',null)
				}
			})
		}
	}
});

frappe.ui.form.on("Stock Adjustment Item", {

	warehouse: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		if (child.batch_no && !frm.doc.scan_mode) {
			frappe.model.set_value(child.cdt, child.cdn, "batch_no", "");
		}

		frm.events.set_valuation_rate_and_qty(frm, cdt, cdn);
	},

	item_code: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		if (child.batch_no && !frm.doc.scan_mode) {
			frappe.model.set_value(cdt, cdn, "batch_no", "");
		}
		let items = frm.doc.items
		for (let i in items){
			if(items[i].item_code == child.item_code && items[i].idx != child.idx){
				frappe.model.set_value(cdt, cdn, "ignore_calculations", 1);
				break;
			}
		}
		frm.events.set_valuation_rate_and_qty(frm, cdt, cdn);
	},

	batch_no: function(frm, cdt, cdn) {
		frm.events.set_valuation_rate_and_qty(frm, cdt, cdn);
	},

	qty: function(frm, cdt, cdn) {
		frm.events.set_amount_quantity(frm, cdt, cdn);
	},

	valuation_rate: function(frm, cdt, cdn) {
		frm.events.set_amount_quantity(frm, cdt, cdn);
	},

	serial_no: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];

		if (child.serial_no) {
			const serial_nos = child.serial_no.trim().split('\n');
			frappe.model.set_value(cdt, cdn, "qty", serial_nos.length);
		}
	},

	items_add: function(frm, cdt, cdn) {
		var item = frappe.get_doc(cdt, cdn);
		if (!item.warehouse && frm.doc.set_warehouse) {
			frappe.model.set_value(cdt, cdn, "warehouse", frm.doc.set_warehouse);
		}
	},

	add_serial_batch_bundle(frm, cdt, cdn) {
		erpnext.utils.pick_serial_and_batch_bundle(frm, cdt, cdn, "Inward");
	},
	item_expiry_date(frm,cdt,cdn){
		let row = locals[cdt][cdn]
		if(!row.using_date_expire && row.item_expiry_date){
			frappe.model.set_value(cdt,cdn, 'item_expiry_date', null)
			frappe.msgprint("Item Doesn't Use Date Expire!")
		}
		if(row.item_expiry_date_bk && row.using_date_expire && row.item_expiry_date_bk != row.item_expiry_date){
			frappe.model.set_value(cdt,cdn, 'item_expiry_date', row.item_expiry_date_bk)
			frappe.msgprint("Expiry Date Can't Be Changed For This Item!")
		}
	}

});

erpnext.stock.StockReconciliation = class StockReconciliation extends erpnext.stock.StockController {
	setup() {
		var me = this;

		this.setup_posting_date_time_check();

		if (me.frm.doc.company && erpnext.is_perpetual_inventory_enabled(me.frm.doc.company)) {
			this.frm.add_fetch("company", "cost_center", "cost_center");
		}
		this.frm.fields_dict["expense_account"].get_query = function() {
			if(erpnext.is_perpetual_inventory_enabled(me.frm.doc.company)) {
				return {
					"filters": {
						'company': me.frm.doc.company,
						"is_group": 0
					}
				}
			}
		}
		this.frm.fields_dict["cost_center"].get_query = function() {
			if(erpnext.is_perpetual_inventory_enabled(me.frm.doc.company)) {
				return {
					"filters": {
						'company': me.frm.doc.company,
						"is_group": 0
					}
				}
			}
		}
	}

	refresh() {
		if(this.frm.doc.docstatus > 0) {
			this.show_stock_ledger();
			erpnext.utils.view_serial_batch_nos(this.frm);
			if (erpnext.is_perpetual_inventory_enabled(this.frm.doc.company)) {
				this.show_general_ledger();
			}
		}
	}

};

cur_frm.cscript = new erpnext.stock.StockReconciliation({frm: cur_frm});
