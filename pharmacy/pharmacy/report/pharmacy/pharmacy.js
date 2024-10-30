// Copyright (c) 2023, Mekky and contributors
// For license information, please see license.txt
/* eslint-disable */
frappe.query_reports["Pharmacy"] = {
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
			fieldname: 'required_months',
            label: __('Required Months'),
            fieldtype: 'Float',
		},
		{
			fieldname: 'default_supplier',
            label: __('Default Supplier'),
            fieldtype: 'Select',
			options:"\nSet\nNot Set"
		}
	],
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
			if (report.data.length > 0 && checked_rows.length == 0){
				frappe.call({
					method: 'pharmacy.pharmacy.report.pharmacy.pharmacy.create_purchase_order',
					args: 
					{
						'data': report.data,
					},
					callback: function(r) {}
				});
			}
			else if(checked_rows.length > 0){
				checked_rows.forEach(row => {
					if (row.default_supplier){
						frappe.throw("Checked Rows must not have default supplier!")
					}
				});
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
								method: 'pharmacy.pharmacy.report.pharmacy.pharmacy.create_purchase_order_for_selected_rows',
								args: 
								{
									'supplier':values.supplier,
									'data': checked_rows,
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
    },
};