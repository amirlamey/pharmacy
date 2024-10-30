# Copyright (c) 2023, Mekky and contributors
# For license information, please see license.txt

import frappe


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
			select count(sii.name)
			from `tabSales Invoice Item` sii, `tabSales Invoice` si
			where sii.docstatus = 1
			and sii.item_code = i.name
			and sii.parent = si.name
			and si.is_return = 0
			and sii.sales_man is not null
			{si_conditions}
		) > 0
		{item_conditions}
	""",as_dict = 1)
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	sales_mans = frappe.parse_json(filters.get("sales_man"))
	if len(sales_mans) > 0:
		for row in data:
			item_code = row.get("item_code")
			total = 0
			for sm in sales_mans:
				sold_qty = frappe.db.sql(f"""
					select sum(sii.stock_qty) qty
					from `tabSales Invoice Item` sii, `tabSales Invoice` si
					where sii.parent = si.name
					and si.docstatus = 1
					and si.is_return = 0
					and sii.item_code = '{item_code}'
					and sii.sales_man = '{sm}'
					and si.posting_date between '{from_date}' and '{to_date}'
					""", as_dict=1)
				row[f"{sm}"] = sold_qty[0]['qty'] if sold_qty[0]['qty'] else 0
				total += row[f"{sm}"]
			row['total'] = total
	else:
		sales_mans_arr = []
		for row in data:
			item_code = row.get("item_code")
			total = 0
			sales_mans = frappe.db.sql(f"""
				select sii.sales_man, sum(sii.stock_qty) qty
				from `tabSales Invoice Item` sii, `tabSales Invoice` si
				where sii.parent = si.name
				and si.docstatus = 1
				and si.is_return = 0
				and sii.item_code = '{item_code}'
				and sii.sales_man is not null
				group by sii.sales_man
			""",as_dict = 1)
			for record in sales_mans:
				sales_man = record.get("sales_man")
				qty = record.get("qty")
				if sales_man not in sales_mans_arr:
					sales_mans_arr.append(sales_man)
					columns.append({
						'label':f"{sales_man}",
						'fieldname':f"{sales_man}",
						'fieldtype':"Float",
						'width': 150
					})
				row[f"{sales_man}"] = qty 
				total += qty
			row['total'] = total
		if len(sales_mans_arr) > 0:
			columns.append({
				'label':"Total",
				'fieldname':"total",
				'fieldtype':"Float",
				'width': 150
			})
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
	sales_mans = frappe.parse_json(filters.get("sales_man"))
	if len(sales_mans) > 0:
		for sm in sales_mans:
			cols.append({
				'label':f"{sm}",
				'fieldname':f"{sm}",
				'fieldtype':"Float",
				'width': 150
			})
		cols.append({
				'label':"Total",
				'fieldname':"total",
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
	sales_mans = frappe.parse_json(filters.get("sales_man"))
	if len(sales_mans) > 0:
		sales_mans = str(sales_mans).replace('[','(').replace(']',')')
		conditions += f" and sii.sales_man in {sales_mans}"
	return conditions