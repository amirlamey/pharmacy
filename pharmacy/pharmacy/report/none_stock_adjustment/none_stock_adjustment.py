# Copyright (c) 2024, Mekky and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today
from erpnext.stock.utils import get_stock_balance

def execute(filters=None):
	filters = frappe._dict(filters)
	from_date = filters.from_date
	to_date = filters.to_date
	warehouse = filters.warehouse
	today_date = today()
	columns = [{
		'label': 'Item',
		'fieldname': 'item_code',
		'fieldtype': 'Link',
		'options': 'Item',
		'width': 400
	}]
	data = frappe.db.sql(f"""
        select item_code, item_name
        from `tabItem` i
        where disabled = 0
		and is_stock_item = 1
		and not exists(
			select sai.name
			from `tabStock Adjustment Item` sai, `tabStock Adjustment` sa
			where sa.docstatus != 2
			and sai.parent = sa.name
			and sa.posting_date between '{from_date}' and '{to_date}'
			and sai.item_code = i.item_code
			and sai.warehouse = {frappe.db.escape(warehouse)}
		)
    """, as_dict=1)
	final_data = []
	for row in data:
		row = frappe._dict(row)
		stock_qty = get_stock_balance(row.item_code,warehouse,today_date)
		if stock_qty > 0:
			final_data.append(row)
	return columns, final_data
