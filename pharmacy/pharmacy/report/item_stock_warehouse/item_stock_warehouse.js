// Copyright (c) 2024, Mekky and contributors
// For license information, please see license.txt

frappe.query_reports["Item Stock Warehouse"] = {
	"filters": [
		{
			label:"Item",
			fieldname:"itemcode",
			fieldtype:"Link",
			options:"Item"
		},	
		{
			label:"Warehouse",
			fieldname:"wareh",
			fieldtype:"Link",
			options:"Warehouse"
		},	
	]
};
