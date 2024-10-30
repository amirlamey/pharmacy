// Copyright (c) 2024, Mekky and contributors
// For license information, please see license.txt

frappe.query_reports["Branches Employee Hours"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": "From Date",
			"fieldtype": "Date",			
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": "To Date",
			"fieldtype": "Date",			
			"reqd": 1
		},
		{
			label:"Branch",
			fieldname:"branch",
			fieldtype:"Link",
			options:"Warehouse"
		},
		{
			label:"Employee",
			fieldname:"emp",
			fieldtype:"Link",
			options:"Employee"
		}
	]
};
