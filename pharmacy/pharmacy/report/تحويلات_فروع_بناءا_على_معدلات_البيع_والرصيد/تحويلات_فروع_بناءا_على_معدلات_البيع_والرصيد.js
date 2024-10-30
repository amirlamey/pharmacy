// Copyright (c) 2024, Mekky and contributors
// For license information, please see license.txt

frappe.query_reports["تحويلات فروع بناءا على معدلات البيع والرصيد"] = {
	"filters": [
		{
			label:"From Date",
			fieldname:"from_date",
			fieldtype:"Date",
			reqd:1
		},
		{
			label:"To Date",
			fieldname:"to_date",
			fieldtype:"Date",
			reqd:1
		},
		{
			label:"Main Branch",
			fieldname:"main_branch",
			fieldtype:"Link",
			options:"Warehouse"
		},
		{
			label:"Branch",
			fieldname:"branch",
			fieldtype:"MultiSelectList",
			options:"Warehouse",
			
			get_data: function(txt) {
				return frappe.db.get_link_options('Warehouse', txt);
			}
		},
		{
			label:"No Of Days",
			fieldname:"no_of_days",
			fieldtype:"Int"
		},
		{
			label:"Item Group",
			fieldname:"item_group",
			fieldtype:"MultiSelectList",
			options:"Item Group",
			get_data: function(txt) {
				return frappe.db.get_link_options('Item Group', txt);
			}
		},
		{
			label:"Origin",
			fieldname:"origin",
			fieldtype:"MultiSelectList",
			options:"Origin",
			get_data: function(txt) {
				return frappe.db.get_link_options('Origin', txt);
			}
		},
		{
			label:"Active Ingredient",
			fieldname:"active_ingredient",
			fieldtype:"MultiSelectList",
			options:"Active Ingredient",
			get_data: function(txt) {
				return frappe.db.get_link_options('Active Ingredient', txt);
			}
		},
		{
			label:"Item Type",
			fieldname:"item_type",
			fieldtype:"MultiSelectList",
			get_data: function(txt) {
				return [
					{value:"Drug",description:"Drug"},
					{value:"Drug Imported",description:"Drug Imported"},
					{value:"Cosmetic",description:"Cosmetic"},
					{value:"Accessories",description:"Accessories"},
					{value:"Supplements",description:"Supplements"},
					{value:"Devices",description:"Devices"},
					{value:"Papers",description:"Papers"},
				]
			}
		},
		{
			label:"Brand",
			fieldname:"brand",
			fieldtype:"MultiSelectList",
			options:"Brand",
			get_data: function(txt) {
				return frappe.db.get_link_options('Brand', txt);
			}
		},
	],
	get_datatable_options(options) {
		return Object.assign(options, {
			checkboxColumn: true,
		});
	},
	onload: function(report) {
		report.page.add_inner_button(__("Create Stock Entry"), function() {
			let data = report.data
			let filters = report.get_values();
			let checked_rows_indexes = report.datatable.rowmanager.getCheckedRows();
			let checked_rows = checked_rows_indexes.map(i => report.data[i]);
			if (data.length > 0 && filters.main_branch && filters.branch.length > 0){
				let data_arr = []
				if (checked_rows.length == 0){
					report.data.forEach(row => {
						data_arr.push(row)
					});
				}else{
					checked_rows.forEach(row => {
						data_arr.push(row)
					});
				}
				
				frappe.call({
					method: 'pharmacy.pharmacy.report.تحويلات_فروع_بناءا_على_معدلات_البيع_والرصيد.تحويلات_فروع_بناءا_على_معدلات_البيع_والرصيد.intialize_stock_entries',
					args: 
					{
						'data': data_arr,
						'filters': filters
					},
					callback: function(r) {
						
					}
				});
				
			}else{
				frappe.msgprint("No Data!")
			}
		})
	}
};
