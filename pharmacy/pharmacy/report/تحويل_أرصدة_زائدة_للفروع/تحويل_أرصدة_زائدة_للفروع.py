# Copyright (c) 2024, Mekky and contributors
# For license information, please see license.txt

# import frappe

import frappe
from erpnext.stock.utils import get_stock_balance
from frappe import _
import json
from frappe.utils import getdate, today

def execute(filters=None):
    columns, data = [], []
    columns = get_columns(filters)
    item_conditions = get_item_conditions(filters)
    si_conditions = get_si_conditions(filters)
    data = frappe.db.sql(f"""
        select item_code, item_name, item_name_ar, item_group, stock_uom, active_ingredient, origin, item_type, brand, related_to,
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
    """, as_dict=1)

    branchs = frappe.parse_json(filters.get("branch", "[]"))
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    main_branch = filters.get("main_branch")
    no_of_days = filters.get("no_of_days")
    days_diff = (getdate(to_date) - getdate(from_date)).days
    
    if branchs or main_branch:
        for row in data:
            order_qty = 0
            item_code = row.get("item_code")
            if main_branch:
                row[f"{main_branch}stock"] = get_stock_balance(item_code,main_branch,to_date)
                sold_qty = frappe.db.sql(f"""
                select sum(sii.stock_qty) qty
                from `tabSales Invoice Item` sii, `tabSales Invoice` si
                where sii.parent = si.name
                and si.docstatus = 1
                and si.is_return = 0
                and sii.item_code = '{item_code}'
                and si.set_warehouse = '{main_branch}'
                and si.posting_date between '{from_date}' and '{to_date}'
                """, as_dict=1)
                row[f"{main_branch}sales"] = sold_qty[0]['qty'] if sold_qty[0]['qty'] else 0
                diff = row[f"{main_branch}sales"] - row[f"{main_branch}stock"]
                order_qty += diff if diff > 0 else 0
            for branch in branchs:
                stock_balance = get_stock_balance(item_code, branch, to_date)
                row[f"{branch}stock"] = stock_balance if stock_balance else 0
                sold_qty = frappe.db.sql(f"""
                select sum(sii.stock_qty) qty
                from `tabSales Invoice Item` sii, `tabSales Invoice` si
                where sii.parent = si.name
                and si.docstatus = 1
                and si.is_return = 0
                and sii.item_code = '{item_code}'
                and si.set_warehouse = '{branch}'
                and si.posting_date between '{from_date}' and '{to_date}'
                """, as_dict=1)
                
                row[f"{branch}sales"] = sold_qty[0]['qty'] if sold_qty[0]['qty'] else 0
                
                avsales = row[f"{branch}sales"] / days_diff if days_diff > 0 else 0
                diff = ((avsales * no_of_days) - row[f"{branch}stock"])
                order_qty += diff if diff > 0 else 0
            row[f"{branch}reorder"]=order_qty
            row["order_qty"] = order_qty
    
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
            'label':f"{main_branch} Stock",
            'fieldname':f"{main_branch}stock",
            'fieldtype':"Float",
            'width': 150
        })
        cols.append({
            'label':f"{main_branch} Sales",
            'fieldname':f"{main_branch}sales",
            'fieldtype':"Float",
            'width': 150
        })
    branchs = frappe.parse_json(filters.get("branch"))
    for branch in branchs:
        cols.append({
            'label':f"{branch} Stock",
            'fieldname':f"{branch}stock",
            'fieldtype':"Float",
            'width': 150
        })
        cols.append({
            'label':f"{branch} Sales",
            'fieldname':f"{branch}sales",
            'fieldtype':"Float",
            'width': 150
        })
        cols.append({
            'label':f"{branch} Reorder",
            'fieldname':f"{branch}reorder",
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
    main_branch = filters.get("main_branch")
    if len(branchs) or main_branch:
        warehouses = []
        if len(branchs):
            warehouses.extend(branchs)
        if main_branch:
            warehouses.extend([main_branch])
        warehouses = str(warehouses).replace('[','(').replace(']',')')
        conditions += f" and si.set_warehouse in {warehouses}"
    return conditions

@frappe.whitelist()
def create_purchase_order(data,supplier,required_by):
    data = json.loads(data)
    po_doc = frappe.new_doc("Purchase Order")
    po_doc.supplier = supplier
    po_doc.schedule_date = required_by
    for row in data:
        if row.get('related_to'):
            row["item_code"] = get_parent_item(row.get('related_to'))
        uom = frappe.db.get_value("Item", row.get("item_code"),"purchase_uom") or row.stock_uom
        qty = row.get("order_qty")
        if qty == 0:
            continue
        
        po_doc.append('items',{
            'item_code': row.get("item_code"),
            'item_name': row.get('item_name'),
            'qty': qty if row.get('stock_uom') == uom else qty/ frappe.db.get_value("UOM Conversion Detail",{'parent': row.get("item_code"), 'uom': uom},'conversion_factor'),
            'uom': uom
        })
    po_doc.run_method("set_missing_values")
    docname = po_doc.insert().name
    frappe.msgprint(_(f'Purchase Order <strong><a href = "/app/Form/Purchase Order/{docname}">{docname} </a></strong> Created Successfully!'))

def get_parent_item(item_code):
    related_to = item_code
    while related_to:
        doc = frappe.get_doc("Item", related_to)
        if not doc.related_to:
            return doc.name
        else:
            related_to = doc.related_to
