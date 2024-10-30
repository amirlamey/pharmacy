// Copyright (c) 2024, Mekky and contributors
// For license information, please see license.txt

frappe.query_reports["Sales Item Type"] = {
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
			label:"Branch",
			fieldname:"warehouse",
			fieldtype:"MultiSelectList",
			options:"Warehouse",
			
			get_data: function(txt) {
				return frappe.db.get_link_options('Warehouse', txt);
			}
		},			
		{
			label:"Item Type",
			fieldname:"item_type",
			fieldtype:"MultiSelectList",
			get_data: function(txt) {
				return [
					{value:"Drug",description:"Drug"},
					{value:"Cosmetic",description:"Cosmetic"},
					{value:"SERVICE",description:"SERVICE"},					
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
			label:"Employee",
			fieldname:"employee",
			fieldtype:"MultiSelectList",
			options:"Employee",
			
			get_data: function(txt) {
				return frappe.db.get_link_options('Employee', txt);
			}
		},
		{
			label:"Order Type",
			fieldname:"order_type",
			fieldtype:"MultiSelectList",
			get_data: function(txt) {
				return [
					{value:"Cash",description:"Cash"},
					{value:"Contract",description:"Contract"},
					{value:"Delivery Cash",description:"Delivery Cash"},
					{value:"Return Cash",description:"Return Cash"},
					{value:"Return Contract",description:"Return Contract"},
					{value:"Call Center",description:"Call Center"}					
				]
			}
		}		
	]
};
