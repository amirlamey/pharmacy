# Copyright (c) 2023, Mekky and contributors
# For license information, please see license.txt

import frappe
from datetime import datetime
from dateutil import relativedelta
import json
import calendar
from frappe.utils import add_to_date
import math

def execute(filters=None):
	if 'from' not in filters or 'to' not in filters:
		return [],[]
	format = '%Y-%m-%d'
	from_date = datetime.strptime(filters['from'], format)
	to_date = datetime.strptime(filters['to'], format)
	if from_date > to_date or from_date == to_date:
		frappe.throw('From Date Must Be Before To Date!')
		return [],[]
	conditions = ""
	if 'to_branch' in filters:
		conditions += f""" and SII.warehouse = "{filters['to_branch']}" """
	if 'item_group' in filters:
		conditions += f""" and SII.item_group = "{filters['item_group']}" """
	if 'brand' in filters:
		conditions += f""" and SII.brand = "{filters['brand']}" """

	full_data = frappe.db.sql(f"""
		select SI.name,SI.posting_date,SII.item_name,SII.item_code,SII.qty ,SII.stock_qty, SII.warehouse,SII.brand,SII.item_group
		from `tabSales Invoice` SI, `tabSales Invoice Item` SII
		where SI.name = SII.parent
		and SI.docstatus = 1
		and SI.posting_date between "{filters['from']}" and "{filters['to']}"
		{conditions}
		order by SI.posting_date,SII.warehouse""",as_dict = 1)

	months = []
	months_dict = {}
	for record in full_data:
		month = calendar.month_abbr[record.posting_date.month]
		if month in months:
			continue
		months.append(month)
		months_dict[f"{month.lower()}"] = 0
	columns = get_columns(months)
	data = []
	items_arr = []
	start_date = add_to_date(to_date,days=-15, as_string=False)
	days_in_between = (to_date - from_date).days
	no_of_days = 0
	if 'no_of_days' in filters:
		no_of_days = filters["no_of_days"]
	for record in full_data:
		sold_last_15_days = 0
		if record.item_code in items_arr:
			continue
		items_arr.append(record.item_code)
		stock_qty = frappe.db.sql("""select sum(actual_qty) "stock_qty" from `tabStock Ledger Entry` where docstatus = 1 and item_code = %(item_code)s""",values={'item_code':record.item_code},as_dict=1)
		stock_qty = stock_qty[0].stock_qty
		if not stock_qty:
			stock_qty = 0
		stock_qty_from = 0
		if 'from_branch' in filters:
			stock_qty_from = frappe.db.sql("""select sum(actual_qty) "stock_qty" from `tabStock Ledger Entry` where docstatus = 1 and item_code = %(item_code)s and warehouse = %(warehouse)s""",values={'item_code':record.item_code,'warehouse':filters['from_branch']},as_dict=1)
			stock_qty_from = stock_qty_from[0].stock_qty
			if not stock_qty_from:
				stock_qty_from = 0
		stock_qty_to = 0
		if 'to_branch' in filters:
			stock_qty_to = frappe.db.sql("""select sum(actual_qty) "stock_qty" from `tabStock Ledger Entry` where docstatus = 1 and item_code = %(item_code)s and warehouse = %(warehouse)s""",values={'item_code':record.item_code,'warehouse':filters['to_branch']},as_dict=1)
			stock_qty_to = stock_qty_to[0].stock_qty
			if not stock_qty_to:
				stock_qty_to = 0
		selling_qty = 0
		for r in full_data:
			if r.item_code == record.item_code:
				current_month = calendar.month_abbr[r.posting_date.month].lower()
				if r.stock_qty:
					selling_qty += r.stock_qty
					months_dict[f"{current_month}"] += r.stock_qty
					if start_date.date() <= r.posting_date <= to_date.date():
						sold_last_15_days += r.stock_qty
				else:
					selling_qty += r.qty
					months_dict[f"{current_month}"] += r.qty
					if start_date.date() <= r.posting_date <= to_date.date():
						sold_last_15_days += r.qty
		required_qty = (selling_qty/days_in_between) * no_of_days
		related_to =  frappe.db.get_value("Item",record.item_code,'related_to')
		default_uom = frappe.db.get_value("Item",record.item_code,'purchase_uom')
		item_conversion_factor = frappe.db.get_value("UOM Conversion Detail",{'parent':record.item_code,'uom':default_uom},'conversion_factor')
		if not item_conversion_factor:
			item_conversion_factor = 1
		data.append({
			'item_name': record.item_name,
			'item_code': record.item_code,
			'warehouse':record.warehouse,
			'item_group': record.item_group,
			'brand': record.brand,
			'average_qty': math.ceil(selling_qty/item_conversion_factor),
			'stock_qty': math.ceil(stock_qty/item_conversion_factor),
			'stock_qty_from': math.ceil(stock_qty_from/item_conversion_factor),
			'stock_qty_to': math.ceil(stock_qty_to/item_conversion_factor),
			'last_15_days_qty': math.ceil(sold_last_15_days/item_conversion_factor),
			'max_average': math.ceil(selling_qty/item_conversion_factor) if math.ceil(selling_qty/item_conversion_factor) >= math.ceil(sold_last_15_days/item_conversion_factor) else math.ceil(sold_last_15_days/item_conversion_factor),
			'required_qty': math.ceil(required_qty/item_conversion_factor),
			'differance_qty': math.ceil((stock_qty_to - required_qty)/item_conversion_factor),
			'from_warehouse_differance_qty': math.ceil((stock_qty_from - abs(stock_qty_to - required_qty))/item_conversion_factor),
			'related_to': related_to,
			'default_uom':default_uom
		})
		for k,v in months_dict.items():
			data[-1][k] = v/item_conversion_factor
			months_dict[k] = 0
			
	related_data = []
	not_related_data = []

	for row in data:
		if row['related_to']:
			if row['related_to'] in items_arr:
				related_data.append(row)
			else:
				row['item_code'] = row['related_to']
				not_related_data.append(row)
		else:
			not_related_data.append(row)

	for row in not_related_data:
		for r in related_data:
			if r['related_to'] == row['item_code']:
				row['average_qty'] += r['average_qty']
				row['stock_qty'] += r['stock_qty']
				row['last_15_days_qty'] += r['last_15_days_qty']
				row['required_qty'] += r['required_qty']
				row['differance_qty'] += r['differance_qty']
				for month in months:
					row[f"{month.lower()}"] += r[f"{month.lower()}"]
	return columns, not_related_data






def get_columns(months):
	cols = [
		{
			'fieldname': 'item_code',
			'label': ('Item'),
			'fieldtype': 'Link',
			'options':'Item',
			'width':200
		},
		{
			'fieldname': 'warehouse',
			'label': ('Warehouse'),
			'fieldtype': 'Link',
			'options':'Warehouse',
			'width':200
		},
		{
			'fieldname': 'item_group',
			'label': ('Item Group'),
			'fieldtype': 'Link',
			'options':'Item Group',
			'width':100
		},
		{
			'fieldname': 'brand',
			'label': ('Brand'),
			'fieldtype': 'Link',
			'options':'Brand'
		},
		{
			'fieldname': 'average_qty',
			'label': ('Average Qty'),
			'fieldtype': 'Float',
		}
	]
	# Append the months
	for month in months:
		cols.append({
			'fieldname': month.lower(),
			'label': month,
			'fieldtype': 'Float',
		})

	cols.append(
		{
			'fieldname': 'last_15_days_qty',
			'label': ('Last 15 Days Qty'),
			'fieldtype': 'Float',
		})
	cols.append(
		{
			'fieldname': 'max_average',
			'label': ('Max Average'),
			'fieldtype': 'Float',
		})
	cols.append(
	{
		'fieldname': 'stock_qty',
		'label': ('Total Stock Qty'),
		'fieldtype': 'Float',
	})
	cols.append(
	{
		'fieldname': 'stock_qty_from',
		'label': ('Stock Qty (From Warehouse)'),
		'fieldtype': 'Float',
	})
	cols.append(
	{
		'fieldname': 'stock_qty_to',
		'label': ('Stock Qty (To Warehouse)'),
		'fieldtype': 'Float',
	})
	cols.append(
	{
		'fieldname': 'required_qty',
		'label': ('Required Qty'),
		'fieldtype': 'Float',
	})
	cols.append(
	{
		'fieldname': 'differance_qty',
		'label': ('Differance Qty'),
		'fieldtype': 'Float',
	})
	cols.append(
	{
		'fieldname': 'from_warehouse_differance_qty',
		'label': ('From Warehouse Differance Qty'),
		'fieldtype': 'Float',
	})
	return cols

@frappe.whitelist()
def create_purchase_order(supplier,data):
	formated_data = json.loads(data)
	po_doc = frappe.new_doc("Purchase Order")
	po_doc.supplier = supplier
	po_doc.schedule_date = frappe.utils.today()
	for record in formated_data:
		row = po_doc.append('items', {})
		row.item_code = record["item_code"]
		row.qty = abs(record["from_warehouse_differance_qty"])
		item_tax_template = frappe.db.get_value('Item Tax',{'parent':record["item_code"]},'item_tax_template')
		if item_tax_template:
			account_head = frappe.db.get_value('Item Tax Template Detail',{'parent':item_tax_template},'tax_type')
			if account_head:
				tax_row = po_doc.append('taxes', {})
				tax_row.charge_type = "On Net Total"
				tax_row.account_head = account_head
				tax_row.description = account_head
				tax_row.rate = 0
	doc_name = po_doc.insert().name
	frappe.msgprint(f'Purchase Order <strong><a href = "/app/Form/Purchase Order/{doc_name}">{doc_name} </a></strong> Created Successfully')

@frappe.whitelist()
def create_stock_entry(data,source_warehouse,target_warehouse):
	formated_data = json.loads(data)
	se_doc = frappe.new_doc("Stock Entry")
	se_doc.stock_entry_type = "Material Transfer"
	se_doc.from_warehouse = source_warehouse
	se_doc.to_warehouse = target_warehouse
	for record in formated_data:
		row = se_doc.append('items', {})
		row.item_code = record["item_code"]
		row.qty = record["required_qty"] - record["stock_qty_to"]
		row.uom = record["default_uom"]
		batches_data = frappe.db.sql("""
			select name
			from `tabBatch`
			where item = %(item_code)s
			and disabled = 0
			and expiry_date > %(now_date)s
			order by manufacturing_date
		""",values={'item_code':record["item_code"], 'now_date': frappe.utils.today()},as_dict=1)
		for batch in batches_data:
			batch_qty = frappe.db.sql("""select sum(actual_qty) "stock_qty" from `tabStock Ledger Entry` where docstatus = 1 and item_code = %(item_code)s and batch_no = %(batch_no)s and warehouse = %(warehouse)s""",values={'item_code':record["item_code"],'batch_no': batch.name,'warehouse':source_warehouse},as_dict=1)
			qty = batch_qty[0].stock_qty
			if qty:
				if qty >= row.qty:
					row.batch_no = batch.name
					break
	doc_name = se_doc.insert().name
	frappe.msgprint(f'Stock Entry <strong><a href = "/app/Form/Stock Entry/{doc_name}">{doc_name} </a></strong> Created Successfully')