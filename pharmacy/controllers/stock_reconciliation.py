
import frappe
import pandas as pd
import json
@frappe.whitelist()
def validate_items(doc,doc_event):
	# frappe.throw("kelani nbe7")
	if len(doc.items)>0:
		old_items = []
		for item in doc.items:
			old_items.append({
				'item_code':item.item_code,
				'batch_no':item.batch_no,
				'qty':item.qty,
				'warehouse':item.warehouse
			})
		items = doc.items
		doc.items = []
		new_list = pd.DataFrame(old_items).groupby(['item_code', 'batch_no','warehouse'] ,as_index=False).sum('qty').to_dict('records')
		for item in new_list:
			doc.append('items',{
				'item_code':item["item_code"],
				'batch_no':item["batch_no"],
				'qty':item["qty"],
				'warehouse':item["warehouse"]
			})
		

