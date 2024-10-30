import frappe
import pandas as pd
import json

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_item_uom(doctype, txt, searchfield, start, page_len, filters):
    if isinstance(filters, str) :
        filters = json.loads(filters)
    
    return frappe.db.sql("""select uom from `tabUOM Conversion Detail` where parent = '{item_code}' and uom IS NOT NULL;""".format(**{'item_code': filters["item_code"]}),{'txt': "%{}%".format(txt),'_txt': txt.replace("%", ""),'start': start,'page_len': page_len})



@frappe.whitelist()
def pi_validate(item_code, supplier):
    if item_code:
        # get rate of this item in last purchase invoice where suplier is same and docstatus is 1
        last_pi = frappe.db.sql("""select `tabPurchase Invoice Item`.rate from `tabPurchase Invoice Item` inner join `tabPurchase Invoice` on `tabPurchase Invoice`.name = `tabPurchase Invoice Item`.parent where `tabPurchase Invoice`.supplier = '{supplier}' and `tabPurchase Invoice`.docstatus = 1 and `tabPurchase Invoice Item`.item_code = '{item_code}' order by `tabPurchase Invoice`.posting_date desc limit 1;""".format(**{'supplier':supplier, 'item_code': item_code}))
        if last_pi:
            return last_pi[0][0]
       