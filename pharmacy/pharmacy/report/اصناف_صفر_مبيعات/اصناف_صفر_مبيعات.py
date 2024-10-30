# Copyright (c) 2023, Mekky and contributors
# For license information, please see license.txt

import frappe
from erpnext.stock.utils import get_stock_balance


def execute(filters=None):
	columns, data = [], []
	columns = get_columns(filters)
	item_conditions = get_item_conditions(filters)
	si_conditions = get_si_conditions(filters)
	data = frappe.db.sql(f"""
		select item_code,item_name,item_name_ar,item_group,stock_uom,active_ingredient,origin,item_type,brand
		from `tabItem` i
		where disabled = 0
		and (
			select count(si.name)
			from `tabSales Invoice Item` sii, `tabSales Invoice` si
			where si.docstatus = 1
			and sii.item_code = i.name
			and sii.parent = si.name
			{si_conditions}
		) = 0
		{item_conditions}
	""",as_dict = 1)
	branchs = frappe.parse_json(filters.get("branch"))
	to_date = filters.get("to_date")

	if len(branchs):
		for row in data:
			item_code = row.get("item_code")
			for branch in branchs:
				row[f"{branch}"] = get_stock_balance(item_code,branch,to_date)
	return columns, data
	
def get_columns(filters):
	cols =[
		{
			'label':"Item Code",
			'fieldname':"item_code",
			'fieldtype':"Link",
			'options':"Item",
			'width': 200
		},
		{
			'label':"Item Name AR",
			'fieldname':"item_name_ar",
			'fieldtype':"Data",
			'width': 150
		},
		{
			'label':"Item Group",
			'fieldname':"item_group",
			'fieldtype':"Link",
			'options':"Item Group",
			'width': 150
		},
		{
			'label':"Default UOM",
			'fieldname':"stock_uom",
			'fieldtype':"Link",
			'options':"UOM"
		},
		{
			'label':"Active Ingredient",
			'fieldname':"active_ingredient",
			'fieldtype':"Link",
			'options':"Active Ingredient",
			'width': 150
		},
		{
			'label':"Origin",
			'fieldname':"origin",
			'fieldtype':"Link",
			'options':"Origin"
		},
		{
			'label':"Item Type",
			'fieldname':"item_type",
			'fieldtype':"Data",
			'width': 150
		},
		{
			'label':"Brand",
			'fieldname':"brand",
			'fieldtype':"Link",
			'options':"Brand",
			'width': 150
		},
	]
	branchs = frappe.parse_json(filters.get("branch"))
	for branch in branchs:
		cols.append({
			'label':f"{branch}",
			'fieldname':f"{branch}",
			'fieldtype':"Float",
			'width': 150
		})
	return cols

def get_item_conditions(filters):
	conditions = ""
	item_group = frappe.parse_json(filters.get("item_group"))
	origin = frappe.parse_json(filters.get("origin"))
	active_ingredient = frappe.parse_json(filters.get("active_ingredient"))
	item_type = frappe.parse_json(filters.get("item_type"))
	brand = frappe.parse_json(filters.get("brand"))
	if len(item_group):
		item_group = str(item_group).replace('[','(').replace(']',')')
		conditions += f" and item_group in {item_group}"
	if len(origin):
		origin = str(origin).replace('[','(').replace(']',')')
		conditions += f" and origin in {origin}"
	if len(active_ingredient):
		active_ingredient = str(active_ingredient).replace('[','(').replace(']',')')
		conditions += f" and active_ingredient in {active_ingredient}"
	if len(item_type):
		item_type = str(item_type).replace('[','(').replace(']',')')
		conditions += f" and item_type in {item_type}"
	if len(brand):
		brand = str(brand).replace('[','(').replace(']',')')
		conditions += f" and brand in {brand}"
	return conditions

def get_si_conditions(filters):
	conditions = ""
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	conditions += f" and si.posting_date between '{from_date}' and '{to_date}'"
	return conditions