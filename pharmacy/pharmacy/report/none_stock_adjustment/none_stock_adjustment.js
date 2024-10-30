// Copyright (c) 2024, Mekky and contributors
// For license information, please see license.txt

frappe.query_reports["None Stock Adjustment"] = {
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
			label:"Warehouse",
			fieldname:"warehouse",
			fieldtype:"Link",
			options:"Warehouse",
			reqd:1
		},
	]
};
