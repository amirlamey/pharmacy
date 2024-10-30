# Copyright (c) 2023, Mekky and contributors
# For license information, please see license.txt

import frappe
from erpnext.stock.utils import get_stock_balance
from frappe import _
import json
from frappe.utils import getdate,today


def execute(filters=None):
	columns, data = [], []
	columns = get_columns(filters)
	item_conditions = get_item_conditions(filters)
	si_conditions = get_si_conditions(filters)
	data = frappe.db.sql(f"""
		select item_code,item_name,item_name_ar,item_group,stock_uom,active_ingredient,origin,item_type,brand,related_to,purchase_uom,
		(
			select price_list_rate
			from `tabItem Price` ip
			where ip.selling = 1
			and ip.item_code = i.item_code
			limit 1
		) sales_price
		from `tabItem` i
		where disabled = 0
		and (
			select count(sii.name)
			from `tabSales Invoice Item` sii, `tabSales Invoice` si
			where sii.docstatus = 1
			and sii.item_code = i.name
			and sii.parent = si.name
			and si.is_return = 0
			{si_conditions}
		) > 0
		{item_conditions}
	""",as_dict = 1)
	branchs = frappe.parse_json(filters.get("branch"))
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	main_branch = filters.get("main_branch")
	no_of_days = filters.get("no_of_days")
	days_diff = (getdate(to_date) - getdate(from_date)).days
	if len(branchs) and main_branch:
		branchs = sort_branches_by_priority(branchs)
		for row in data:
			conversion_factor = 1
			total_req_for_transfer = 0
			item_code = row.get("item_code")
			stock_uom = row.get("stock_uom")
			purchase_uom = row.get("purchase_uom")
			if stock_uom != purchase_uom:
				conversion_factor = frappe.db.get_value("UOM Conversion Detail",{'parent': item_code, 'uom':purchase_uom},"conversion_factor") or 1
			row["from_branch_qty"] = get_stock_balance(item_code,main_branch,to_date)/conversion_factor
				
			for branch in branchs:
				row[f"{branch}stock_qty"] = get_stock_balance(item_code,branch,to_date)/conversion_factor
				sold_qty = frappe.db.sql(f"""
				select sum(sii.stock_qty/sii.conversion_factor) qty
				from `tabSales Invoice Item` sii, `tabSales Invoice` si
				where sii.parent = si.name
				and si.docstatus = 1
				and si.is_return = 0
				and sii.item_code = '{item_code}'
				and si.set_warehouse = '{branch}'
				and si.posting_date between '{from_date}' and '{to_date}'
				""", as_dict=1)
				row[f"{branch}sales_qty_per_day"] = sold_qty[0]['qty']/days_diff if sold_qty[0]['qty'] else 0
				if no_of_days:
					row[f"{branch}req_qty"] = row[f"{branch}sales_qty_per_day"] * no_of_days
					req_for_transfer = row[f"{branch}req_qty"] - row[f"{branch}stock_qty"]
					row[f"{branch}req_for_transfer"] = req_for_transfer if req_for_transfer > 0 else 0
					total_req_for_transfer += row[f"{branch}req_for_transfer"]
			row["total_req_for_transfer"] = total_req_for_transfer
			row["diff_in_source_warehouse"] =  row["from_branch_qty"] - total_req_for_transfer


				
			
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
		{
			'label':"Related To",
			'fieldname':"related_to",
			'fieldtype':"Link",
			'options':"Item",
			'width': 150
		},
		{
			'label':"Sales Price",
			'fieldname':"sales_price",
			'fieldtype':"Float"
		},
	]
	main_branch = filters.get("main_branch")
	if main_branch:
		cols.append({
			'label':"From Branch Actual Qty",
			'fieldname':"from_branch_qty",
			'fieldtype':"Float",
			'width': 150
		})
	branchs = frappe.parse_json(filters.get("branch"))
	if len(branchs):
		branchs = sort_branches_by_priority(branchs)
		for branch in branchs:
			cols.append({
				'label':f"{branch} => Average Sales Qty Per Day",
				'fieldname':f"{branch}sales_qty_per_day",
				'fieldtype':"Float",
				'width': 280
			})
			cols.append({
				'label':"Actual Qty",
				'fieldname':f"{branch}stock_qty",
				'fieldtype':"Float",
				'width': 150
			})
			cols.append({
				'label':"Required Qty",
				'fieldname':f"{branch}req_qty",
				'fieldtype':"Float",
				'width': 150
			})
			cols.append({
				'label':"Required For Transfer",
				'fieldname':f"{branch}req_for_transfer",
				'fieldtype':"Float",
				'width': 150
			})
		cols.append({
			'label':"Total Required For Transfer",
			'fieldname':"total_req_for_transfer",
			'fieldtype':"Float",
			'width': 150
		})
		cols.append({
			'label':"Difference In Source Warehouse",
			'fieldname':"diff_in_source_warehouse",
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
	branchs = frappe.parse_json(filters.get("branch"))
	if len(branchs):
		warehouses = []
		if len(branchs):
			warehouses.extend(branchs)
		warehouses = str(warehouses).replace('[','(').replace(']',')')
		conditions += f" and si.set_warehouse in {warehouses}"
	return conditions

def sort_branches_by_priority(branchs):
	ordered_branchs = []
	condition_branchs = str(branchs).replace('[','(').replace(']',')')
	branchs_data = frappe.db.sql(f"""
		select name
		from `tabWarehouse`
		where name in {condition_branchs}
		and priority != 0
		order by priority
	""", as_dict = 1)
	for branch in branchs_data:
		ordered_branchs.append(branch.get("name"))
	for branch in branchs:
		if branch not in ordered_branchs:
			ordered_branchs.append(branch)
	return ordered_branchs

def get_parent_item(item_code):
	related_to = item_code
	while related_to:
		doc = frappe.get_doc("Item", related_to)
		if not doc.related_to:
			return doc.name
		else:
			related_to = doc.related_to

def create_stock_entry(sw,tw,items):
	se_doc = frappe.new_doc("Stock Entry")
	se_doc.stock_entry_type = "Material Transfer"
	se_doc.from_warehouse = sw
	se_doc.to_warehouse = tw

	for item in items:
		se_doc.append('items',{
			'item_code': item.get('item_code'),
			'qty': item.get('qty'),
			'batch_no': item.get('batch_no'),
			'uom': item.get('uom')
		})
	manage_items(se_doc)
	se_doc.insert()

def get_batch_no(item_code,req_for_transfer):
	return frappe.db.sql(f"""
					select name
					from `tabBatch`
					where item = '{item_code}'
					and expiry_date > CURDATE()
					and batch_qty >= {req_for_transfer}
					and disabled = 0
					order by expiry_date
				""",as_dict=1)

def manage_items(doc):
    items = []
    item_row = doc.items[0]
    item_code = item_row.item_code
    sw = doc.from_warehouse
    tw = doc.to_warehouse
    batch = item_row.batch_no
    item_qty = item_row.qty
    qty = item_row.qty
    related_items = frappe.db.get_list("Item",{'related_to': item_code}, order_by = "creation",pluck="name")
    for item in related_items:
        if qty > 0:
            conversion_factor = 1
            stock_uom = frappe.db.get_value("Item",item,"stock_uom")
            purchase_uom = frappe.db.get_value("Item",item,"purchase_uom")
            uom = purchase_uom or stock_uom
            if stock_uom != purchase_uom:
                conversion_factor = frappe.db.get_value("UOM Conversion Detail",{'parent': item, 'uom':purchase_uom},"conversion_factor") or 1
            item_stock_qty = get_stock_balance(item,sw,doc.posting_date)/ conversion_factor
            if item_stock_qty > 0:
                if item_stock_qty >= qty:
                    batch_no = get_batch_no(item,qty)
                    items.append({
                        'item_code': item,
                        'qty': qty,
                        'batch_no': batch_no[0]["name"] if len(batch_no) else "",
                        'uom': uom
                    })
                    qty = 0
                else:
                    batch_no = get_batch_no(item,item_stock_qty)
                    items.append({
                        'item_code': item,
                        'qty': item_stock_qty,
                        'batch_no': batch_no[0]["name"] if len(batch_no) else "",
                        'uom': uom
                    })
                    qty -= item_stock_qty
    if qty != item_qty:
        doc.items = []
        for item in items:
            doc.append('items',{item})
        diff = item_qty - qty
        if diff > 0:
            item_row.qty = diff
            doc.append('items',{item_row})

@frappe.whitelist()
def intialize_stock_entries(data,filters):
	data = json.loads(data)
	filters = json.loads(filters)
	sw = filters.get("main_branch")
	branchs = frappe.parse_json(filters.get("branch"))
	branchs = sort_branches_by_priority(branchs)
	for row in data:
		item_code = row.get("item_code")
		from_branch_stock = float(row.get("from_branch_qty"))
		uom = row.get("purchase_uom") or row.get("stock_uom")
		for branch in branchs:
			items = []
			req_for_transfer = float(row[f"{branch}req_for_transfer"])
			diff_qty = from_branch_stock - req_for_transfer
			if req_for_transfer > 0 and from_branch_stock > 0:
				if diff_qty >= 0:
					batch_no = get_batch_no(item_code,req_for_transfer)
					items.append({
						'item_code': item_code,
						'qty': req_for_transfer,
						'batch_no': batch_no[0]["name"] if len(batch_no) else "",
						'uom': uom
					})
					create_stock_entry(sw,branch,items)
					from_branch_stock -= req_for_transfer
				else:
					batch_no = get_batch_no(item_code,from_branch_stock)
					items.append({
						'item_code': item_code,
						'qty': from_branch_stock,
						'batch_no': batch_no[0]["name"] if len(batch_no) else "",
						'uom': uom
					})
					create_stock_entry(sw,branch,items)
					from_branch_stock = 0
					break