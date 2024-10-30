import frappe
import pandas as pd
import json
from frappe import _
from erpnext.stock.get_item_details import get_conversion_factor

class NegativeStockError(frappe.ValidationError):
	pass

@frappe.whitelist()
def validate_items(doc,doc_event):
	pass
	# frappe.throw("kelani nbe7")
	# if len(doc.items)>0:
	# 	for item in doc.items:
	# 		batchno =frappe.db.get_list('Batch',filters={'disabled': 0,'item':item.item_code},fields=['name'],order_by='expiry_date Asc')
	# 		item.batch_no = batchno[0].name
    
def before_save(doc,method):
	validate_items_expiry_dates(doc)
	validate_items_qty(doc)

def validate_items_expiry_dates(doc):
	stock_entry_types = ["Material Issue", "Material Transfer"]
	stock_entry_type = doc.stock_entry_type
	if stock_entry_type not in stock_entry_types:
		return
	invalid_items = []
	for item in doc.items:
		if item.custom_using_date_expire == 1 and not item.item_expiry_date:
			invalid_items.append(f'{item.idx}')
	
	if invalid_items:
		invalid_items_idxs = ','.join(invalid_items)
		frappe.throw(
			title='Missing Fields',
    		msg=f'Rows: {invalid_items_idxs} &emsp;&emsp; <b>Source Item Expiry Date</b> IS Missing!',
		)

def validate_items_qty(doc):
	stock_entry_type = doc.stock_entry_type
	if stock_entry_type != "Material Transfer":
		return
	
	msg_list = []
	for item in doc.items:
		if item.custom_using_date_expire == 1 and item.qty > item.custom_expiry_date_qty:
			deficiency = round(item.qty - item.custom_expiry_date_qty, 2)
			msg = _("{0} units of {1} needed in {2} to complete this transaction.").format(
					frappe.bold(abs(deficiency)),
					frappe.get_desk_link("Item", item.item_code),
					frappe.get_desk_link("Warehouse", item.s_warehouse),
				)
			msg_list.append(msg)
	
	if msg_list:
		message = '<br>'.join(msg_list)
		frappe.throw(message, NegativeStockError, title=_("Insufficient Stock"))

@frappe.whitelist()
def get_expiry_date_qty(item_code = None, warehouse = None, expiry_date = None, uom = None):
	if item_code and warehouse and expiry_date and uom:
		item_details = frappe.db.sql("""
			SELECT warehouse,item_code,stock_uom,item_expiry_date, SUM(actual_qty) AS qty 
			FROM `tabStock Ledger Entry`
			WHERE is_cancelled = 0 AND item_code = %(item_code)s AND warehouse = %(warehouse)s AND item_expiry_date = %(item_expiry_date)s
			GROUP BY warehouse,item_code,stock_uom, item_expiry_date
			HAVING SUM(actual_qty) > 0
		""", values={
			'item_code': item_code,
			'warehouse': warehouse,
			'item_expiry_date': expiry_date
		},as_dict=1)

		expiry_date_qty = item_details[0].get('qty') if item_details else 0
		if expiry_date_qty:
			if item_details[0].get('stock_uom') != uom:
				conversion_factor = get_conversion_factor(item_code, uom).get('conversion_factor') or 1
				expiry_date_qty = expiry_date_qty / conversion_factor
		return expiry_date_qty
	else:
		return 0

@frappe.whitelist()
def get_expiry_date(item_code, warehouse):
	item_details = frappe.db.sql("""
		SELECT item_expiry_date
		FROM `tabStock Ledger Entry`
		WHERE is_cancelled = 0 AND item_code = %(item_code)s AND warehouse = %(warehouse)s AND item_expiry_date >= NOW()
		GROUP BY warehouse,item_code,stock_uom, item_expiry_date
		HAVING SUM(actual_qty) > 0
		ORDER BY item_expiry_date
	""", values={
		'item_code': item_code,
		'warehouse': warehouse
	},as_dict=1)

	return item_details[0].get('item_expiry_date') if item_details else ''