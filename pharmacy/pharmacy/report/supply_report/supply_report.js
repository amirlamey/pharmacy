// Copyright (c) 2024, Mekky and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Supply Report"] = {
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
			label:"From Branch",
			fieldname:"main_branch",
			fieldtype:"Link",
			options:"Warehouse",
			reqd:1
		},
		{
			label:"To Branchs",
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
	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname.includes("req_for_transfer") && column.fieldname != "total_req_for_transfer" && data && data[column.fieldname] > 0) {
			value = "<span style='color:green'>" + value + "</span>";
		}

		return value;
	},
	get_datatable_options(options) {
		return Object.assign(options, {
			checkboxColumn: true,
		});
	},
	onload: function(report) {
		report.page.add_inner_button(__("Create Stock Entries"), function() {
			let data = report.data
			let filters = report.get_values();
			let checked_rows_indexes = report.datatable.rowmanager.getCheckedRows();
			let checked_rows = checked_rows_indexes.map(i => report.data[i]);
			
			if (data.length > 0 && filters.main_branch && filters.branch.length > 0){
				let data_arr = []
				if (checked_rows.length == 0){
					report.data.forEach(row => {
						if (row.total_req_for_transfer > 0 && row.from_branch_qty > 0){
							data_arr.push(row)
						}
					});
				}else{
					checked_rows.forEach(row => {
						if (row.total_req_for_transfer > 0 && row.from_branch_qty > 0){
							data_arr.push(row)
						}
					});
				}
				if (data_arr.length == 0){
					frappe.msgprint("No Data!")
				}else{
					frappe.call({
						method:"pharmacy.pharmacy.report.report_7.report_7.intialize_stock_entries",
						args:{
							data: data_arr,
							filters: filters
						},
						callback:(r)=>{
							let msg = frappe._('<strong><a href = "/app/stock-entry">Stock Entries</a></strong> Created!')
							frappe.msgprint(msg)
						}
					})
				}
			}else{
				frappe.msgprint("No Data!")
			}
		})
	}
};
