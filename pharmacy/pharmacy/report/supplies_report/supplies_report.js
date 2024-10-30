// Copyright (c) 2023, Mekky and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Supplies Report"] = {
	"filters": [
		{
			fieldname: 'from',
            label: __('From'),
            fieldtype: 'Date',
		},
		{
			fieldname: 'to',
            label: __('To'),
            fieldtype: 'Date',
		},
		{
			fieldname: 'no_of_days',
            label: __('No Of Days'),
            fieldtype: 'Int',
		},
		{
			fieldname: 'from_branch',
            label: __('From Branch'),
            fieldtype: 'Link',
			options:"Warehouse"
		},
		{
			fieldname: 'to_branch',
            label: __('To Branch'),
            fieldtype: 'Link',
			options:"Warehouse"
		},
		{
			fieldname: 'item_group',
            label: __('Item Group'),
            fieldtype: 'Link',
			options:"Item Group"
		},
		{
			fieldname: 'brand',
            label: __('Brand'),
            fieldtype: 'Link',
			options:"Brand"
		}
	],
	"formatter": function (value, row, column, data, default_formatter) {
		let months = ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"]
		value = default_formatter(value, row, column, data);
		if (column.fieldname == "differance_qty" && data.differance_qty >= 0 ) {
			value = "<span style='color:green'>" + value + "</span>";
		}
		else if (column.fieldname == "differance_qty" && data.differance_qty < 0 ) {
			value = "<span style='color:red'>" + value + "</span>";
		}
		if (column.fieldname == "from_warehouse_differance_qty" && data.from_warehouse_differance_qty >= 0 ) {
			value = "<span style='color:green'>" + value + "</span>";
		}
		else if (column.fieldname == "from_warehouse_differance_qty" && data.from_warehouse_differance_qty < 0 ) {
			value = "<span style='color:red'>" + value + "</span>";
		}
		if (months.includes(column.fieldname)) {
			value = "<span style='color:blue'>" + value + "</span>";
		}
		return value;
	},
	get_datatable_options(options) {
		return Object.assign(options, {
			checkboxColumn: true,
		});
	},
	onload: function(report) {
	    report.page.add_inner_button(__("Create Purchase Order"), function() {
			var filters = report.get_values();
			let checked_rows_indexes = report.datatable.rowmanager.getCheckedRows();
			let checked_rows = checked_rows_indexes.map(i => report.data[i]);
			if (report.data.length > 0){
				let data_arr = []
				if (checked_rows.length == 0){
					report.data.forEach(row => {
						if (row.from_warehouse_differance_qty < 0){
							data_arr.push(row)
						}
					});
					if (data_arr.length == 0){
						frappe.throw("At Least One Record Must Have From Warehouse Differance Qty Less Than Zero!")
					}
				}else{
					checked_rows.forEach(row => {
						if (row.from_warehouse_differance_qty >= 0){
							frappe.throw("Checked Rows From Warehouse Differance Qty Must Be Less Than Zero!")
						}else{
							data_arr.push(row)
						}
					});
				}
				let d = new frappe.ui.Dialog({
					title: 'Enter Supplier Name',
					fields: [
						{
							label: 'Supplier',
							fieldname: 'supplier',
							fieldtype: 'Link',
							options:'Supplier'
						},
					],
					primary_action_label: 'Create',
					primary_action(values) {
						if(!values.supplier){
							frappe.throw("You Must Select The Supplier!")
						}else{
							frappe.call({
								method: 'pharmacy.pharmacy.report.supplies_report.supplies_report.create_purchase_order',
								args: 
								{
									'supplier':values.supplier,
									'data': data_arr,
								},
								callback: function(r) {}
							});
						}
						d.hide();
					}
				});
				d.show();
				
			}
			else{
				frappe.msgprint("No Data!")
			}
		});
		report.page.add_inner_button(__("Create Stock Entry"), function() {
			var filters = report.get_values();
			if(!filters.from_branch || !filters.to_branch){
				frappe.throw("From And To Branches Must Be Set In Filters!")
			}
			let checked_rows_indexes = report.datatable.rowmanager.getCheckedRows();
			let checked_rows = checked_rows_indexes.map(i => report.data[i]);
			if (report.data.length > 0){
				let data_arr = []
				if (checked_rows.length == 0){
					report.data.forEach(row => {
						if (row.required_qty && row.required_qty > row.stock_qty_to){
							data_arr.push(row)
						}
					});
					if (data_arr.length == 0){
						frappe.throw("At Least One Record Must Have Required Qty More Than Stock Quantity (To Warehouse)!")
					}
				}else{
					checked_rows.forEach(row => {
						if (row.required_qty  && row.required_qty > row.stock_qty_to){
							data_arr.push(row)
						}
						else{
							frappe.throw("Checked Rows Required Qty Must Be More Than Stock Quantity (To Warehouse)!")
						}
					});
				}
				frappe.call({
					method: 'pharmacy.pharmacy.report.supplies_report.supplies_report.create_stock_entry',
					args: 
					{
						'data': data_arr,
						'source_warehouse':filters.from_branch,
						'target_warehouse':filters.to_branch
					},
					callback: function(r) {}
				});
			}
			else{
				frappe.msgprint("No Data!")
			}
		});
    },
};
