# Copyright (c) 2023, Mekky and contributors
# For license information, please see license.txt

import frappe
from datetime import datetime
from dateutil import relativedelta
import json

def execute(filters=None):
	if 'from' not in filters or 'to' not in filters:
		return [],[]
	format = '%Y-%m-%d'
	from_date = datetime.strptime(filters['from'], format)
	to_date = datetime.strptime(filters['to'], format)
	if from_date > to_date or from_date == to_date:
		frappe.throw('From Date Must Be Before To Date!')
		return [],[]
	no_of_days = (to_date - from_date).days
	months_diff = no_of_days / 30
	columns = get_columns()
	full_data = frappe.db.sql("""
		select SI.name,SII.item_name,SII.item_code,SII.qty ,SII.stock_qty
		from `tabSales Invoice` SI, `tabSales Invoice Item` SII
		where SI.name = SII.parent
		and SI.docstatus = 1
		and SI.posting_date between %(from)s and %(to)s
	""",values = {'from':filters['from'],'to':filters['to']},as_dict = 1)
	data = []
	items_arr = []
	for record in full_data:
		if record.item_code in items_arr:
			continue
		items_arr.append(record.item_code)
		stock_qty = frappe.db.sql("""select sum(actual_qty) "stock_qty" from `tabStock Ledger Entry` where docstatus = 1 and item_code = %(item_code)s""",values={'item_code':record.item_code},as_dict=1)
		stock_qty = stock_qty[0].stock_qty
		if not stock_qty:
			stock_qty = 0
		selling_qty = 0
		for r in full_data:
			if r.item_code == record.item_code:
				if r.stock_qty:
					selling_qty += r.stock_qty
				else:
					selling_qty += r.qty
		selling_qty_per_month = selling_qty / months_diff
		required_qty = selling_qty_per_month * filters['required_months'] if 'required_months' in filters else 0
		required_qty_for_transaction = required_qty - stock_qty
		default_supplier = frappe.db.get_value("Item Default",{'parent':record.item_code},'default_supplier')
		related_to =  frappe.db.get_value("Item",record.item_code,'related_to')
		default_uom = frappe.db.get_value("Item",record.item_code,'purchase_uom')
		item_conversion_factor = frappe.db.get_value("UOM Conversion Detail",{'parent':record.item_code,'uom':default_uom},'conversion_factor')
		if not item_conversion_factor:
			item_conversion_factor = 1
		data.append({
			'item_name': record.item_name,
			'item_code': record.item_code,
			'uom': default_uom,
			'selling_qty': selling_qty / item_conversion_factor,
			'selling_qty_per_month': selling_qty_per_month / item_conversion_factor,
			'required_qty': required_qty / item_conversion_factor,
			'stock_qty': stock_qty / item_conversion_factor,
			'required_qty_for_transaction': required_qty_for_transaction/item_conversion_factor if required_qty_for_transaction > 0 else 0,
			'default_supplier': default_supplier,
			'related_to': related_to
		})

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
				row['selling_qty'] += r['selling_qty']
				row['selling_qty_per_month'] += r['selling_qty_per_month']
				row['required_qty'] += r['required_qty']
				row['stock_qty'] += r['stock_qty']
				row['required_qty_for_transaction'] += r['required_qty_for_transaction']
	
	filtered_data = []
	if 'default_supplier' in filters:
		if filters['default_supplier'] == "Set":
			for row in not_related_data:
				if row['default_supplier']:
					filtered_data.append(row)
			return columns, filtered_data
		elif filters['default_supplier'] == "Not Set":
			for row in not_related_data:
				if not row['default_supplier']:
					filtered_data.append(row)
			return columns, filtered_data
	return columns, not_related_data

def get_columns():
	cols = [
		{
		'fieldname': 'item_code',
		'label': ('Item'),
		'fieldtype': 'Link',
		'options':'Item',
		'width':200
		},
		{
		'fieldname': 'uom',
		'label': ('UOM'),
		'fieldtype': 'Data'
		},
		{
			'fieldname': 'selling_qty',
			'label': ('Selling Qty'),
			'fieldtype': 'Float',
		},
		{
			'fieldname': 'selling_qty_per_month',
			'label': ('Selling Qty Per Month'),
			'fieldtype': 'Float',
		},
		{
			'fieldname': 'required_qty',
			'label': ('Required Qty'),
			'fieldtype': 'Float',
		},
		{
			'fieldname': 'stock_qty',
			'label': ('Stock Qty'),
			'fieldtype': 'Float',
		},
		{
			'fieldname': 'required_qty_for_transaction',
			'label': ('Required Qty For Transaction'),
			'fieldtype': 'Float',
		},
		{
			'fieldname': 'default_supplier',
			'label': ('Default Supplier'),
			'fieldtype': 'Data',
		},
	]
	return cols

def calc_months_diff(d1,d2):
	start_date = datetime.strptime(d1, "%Y-%m-%d")
	end_date = datetime.strptime(d2, "%Y-%m-%d")
	return relativedelta.relativedelta(end_date, start_date).months

@frappe.whitelist()
def create_purchase_order(data):
	formated_data = json.loads(data)
	suppliers = []
	for record in formated_data:
		if record["default_supplier"] and record["default_supplier"] not in suppliers:
			suppliers.append(record["default_supplier"])
	if len(suppliers) == 0:
		frappe.msgprint("Thier must be at least one record with default supplier!")
	count = 0
	for supplier in suppliers:
		flag = 0
		po_doc = frappe.new_doc("Purchase Order")
		po_doc.supplier = supplier
		po_doc.schedule_date = frappe.utils.today()
		for item in formated_data:
			if item["default_supplier"] == supplier and item["required_qty_for_transaction"] != 0:
				row = po_doc.append('items', {})
				row.item_code = item["item_code"]
				row.qty = item["required_qty_for_transaction"]
				flag = 1
		if flag:
			doc_name = po_doc.insert().name
			frappe.msgprint(f'Purchase Order <strong><a href = "/app/Form/Purchase Order/{doc_name}">{doc_name} </a></strong> Created Successfully')
			count += 1
	if count == 0 and len(suppliers)>0:
		frappe.msgprint("Required Qty For Transactions is equal to Zero in all records!")

@frappe.whitelist()
def create_purchase_order_for_selected_rows(supplier,data):
	formated_data = json.loads(data)
	po_doc = frappe.new_doc("Purchase Order")
	po_doc.supplier = supplier
	po_doc.schedule_date = frappe.utils.today()
	flag = 0
	for record in formated_data:
		if record["required_qty_for_transaction"] != 0:
			row = po_doc.append('items', {})
			row.item_code = record["item_code"]
			row.qty = record["required_qty_for_transaction"]
			flag = 1
			item_tax_template = frappe.db.get_value('Item Tax',{'parent':record["item_code"]},'item_tax_template')
			if item_tax_template:
				account_head = frappe.db.get_value('Item Tax Template Detail',{'parent':item_tax_template},'tax_type')
				if account_head:
					tax_row = po_doc.append('taxes', {})
					tax_row.charge_type = "On Net Total"
					tax_row.account_head = account_head
					tax_row.description = account_head
					tax_row.rate = 0
	if flag:
		doc_name = po_doc.insert().name
		frappe.msgprint(f'Purchase Order <strong><a href = "/app/Form/Purchase Order/{doc_name}">{doc_name} </a></strong> Created Successfully')
	else:
		frappe.msgprint("Required Qty For Transactions is equal to Zero in all selected records!")