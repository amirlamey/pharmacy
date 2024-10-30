// Copyright (c) 2024, Mekky and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["تقرير مبيعات افراد"] = {
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
		{
			label:"Sales Man",
			fieldname:"sales_man",
			fieldtype:"MultiSelectList",
			options:"Employee",
			get_data: function(txt) {
				return frappe.db.get_link_options('Employee', txt);
			}
		},
	]
};
