import frappe
import pandas as pd
import json
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_item_uom(doctype, txt, searchfield, start, page_len, filters):
    if isinstance(filters, str) :
        filters = json.loads(filters)
    return frappe.db.sql("""select uom from `tabUOM Conversion Detail` where parent = '{item_code}' and uom IS NOT NULL;""".format(**{'item_code': filters["item_code"]}),{'txt': "%{}%".format(txt),'_txt': txt.replace("%", ""),'start': start,'page_len': page_len})


