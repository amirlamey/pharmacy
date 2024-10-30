// Copyright (c) 2024, Mekky and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["المبيعات وصافى المبيعات"] = {
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
			fieldname:"branch",
			fieldtype:"MultiSelectList",
			options:"Warehouse",
			get_data: function(txt) {
				return frappe.db.get_link_options('Warehouse', txt);
			}
		}
	]
};
