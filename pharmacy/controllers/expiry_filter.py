import frappe
import pandas as pd
import json

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def expiry_filter(doctype, txt, searchfield, start, page_len, filters):
	if isinstance(filters, str) :
		filters = json.loads(filters)
	return frappe.db.sql("""select item_expiry_date from `tabStock Ledger Entry` where item_code = '{item_code}' and warehouse = '{warehouse}' and item_expiry_date IS NOT NULL GROUP BY item_expiry_date HAVING SUM(actual_qty) > 0;""".format(**{'item_code': filters["item_code"], 'warehouse':filters["warehouse"]}),{'txt': "%{}%".format(txt),'_txt': txt.replace("%", ""),'start': start,'page_len': page_len})
