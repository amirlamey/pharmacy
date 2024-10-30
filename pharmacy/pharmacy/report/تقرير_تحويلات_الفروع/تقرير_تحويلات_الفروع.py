# Copyright (c) 2023, Mekky and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	columns, data = [], []
	columns = get_columns(filters)
	item_conditions = get_item_conditions(filters)
	se_conditions = get_se_conditions(filters)
	data = data = frappe.db.sql(f"""
		select item_code,item_name,item_name_ar,item_group,stock_uom,active_ingredient,origin,item_type,brand
		from `tabItem` i
		where disabled = 0
		and (
			select count(sei.name)
			from `tabStock Entry Detail` sei, `tabStock Entry` se
			where sei.docstatus = 1
			and sei.item_code = i.name
			and sei.parent = se.name
			and se.stock_entry_type = "Material Transfer"
			{se_conditions}
		) > 0
		{item_conditions}
	""",as_dict = 1)
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	from_branch = filters.get("from_branch")
	to_branchs = frappe.parse_json(filters.get("to_branch"))
	if len(to_branchs) > 0 and from_branch:
		warehouses = str(to_branchs).replace('[','(').replace(']',')')
		for row in data:
			item_code = row.get("item_code")
			transfered_from_qty = frappe.db.sql(f"""
				select sum(sei.transfer_qty) qty
				from `tabStock Entry Detail` sei, `tabStock Entry` se
				where se.docstatus = 1
				and sei.parent = se.name
				and se.stock_entry_type = "Material Transfer"
				and sei.item_code = '{item_code}'
				and sei.s_warehouse = '{from_branch}'
				and sei.t_warehouse in {warehouses}
				and se.posting_date between '{from_date}' and '{to_date}'
				""", as_dict=1)
			row[f"{from_branch}"] = transfered_from_qty[0]['qty'] if transfered_from_qty[0]['qty'] else 0
			for branch in to_branchs:
				transfered_to_qty = frappe.db.sql(f"""
				select sum(sei.transfer_qty) qty
				from `tabStock Entry Detail` sei, `tabStock Entry` se
				where se.docstatus = 1
				and sei.parent = se.name
				and se.stock_entry_type = "Material Transfer"
				and sei.item_code = '{item_code}'
				and sei.s_warehouse = '{from_branch}'
				and sei.t_warehouse = '{branch}'
				and se.posting_date between '{from_date}' and '{to_date}'
				""", as_dict=1)
				row[f"{branch}"] = transfered_to_qty[0]['qty'] if transfered_to_qty[0]['qty'] else 0

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
		}
	]
	from_branch = filters.get("from_branch")
	to_branchs = frappe.parse_json(filters.get("to_branch"))
	if from_branch and len(to_branchs) > 0:
		cols.append({
			'label':f"{from_branch}",
			'fieldname':f"{from_branch}",
			'fieldtype':"Float",
			'width': 150
		})
		for branch in to_branchs:
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

def get_se_conditions(filters):
	conditions = ""
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	conditions += f" and se.posting_date between '{from_date}' and '{to_date}'"
	from_branch = filters.get("from_branch")
	to_branchs = frappe.parse_json(filters.get("to_branch"))
	if len(to_branchs) > 0 and from_branch:
		warehouses = str(to_branchs).replace('[','(').replace(']',')')
		conditions += f" and sei.s_warehouse = '{from_branch}' and sei.t_warehouse in {warehouses}"
	return conditions