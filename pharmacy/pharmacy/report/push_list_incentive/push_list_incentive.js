// Copyright (c) 2024, Mekky and contributors
// For license information, please see license.txt

frappe.query_reports["Push List Incentive"] = {
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
		}
	]
};
