# Copyright (c) 2024, Mekky and contributors
# For license information, please see license.txt

# import frappe


import frappe
from erpnext.stock.utils import get_stock_balance
from frappe import _
import json 
from frappe.utils import getdate,today


def execute(filters=None):
    if filters is None:
        filters = {}

    columns, data = [], []
    columns = get_columns(filters)
    item_conditions = get_item_conditions(filters)
    si_conditions = get_si_conditions(filters)
    
    data = frappe.db.sql(f"""
        select item_code, item_name, item_name_ar, item_group, sales_uom stock_uom, active_ingredient, origin, item_type, brand, related_to,
        (
            select max(price_list_rate)
            from `tabItem Price` ip
            where ip.selling = 1
            and ip.item_code = i.item_code
            limit 1
        ) as sales_price,
        (
            select conversion_factor from `tabUOM Conversion Detail` ucd where ucd.parent = item_code and ucd.uom = sales_uom
        ) conversion_factor
        from `tabItem` i
        where disabled = 0
        # and (
        #     select count(sii.name)
        #     from `tabSales Invoice Item` sii, `tabSales Invoice` si
        #     where sii.docstatus = 1
        #     and sii.item_code = i.name
        #     and sii.parent = si.name
        #     and si.is_return = 0
        #     {si_conditions}
        # ) > 0
        {item_conditions}
    """, as_dict=1)
    
    branchs = frappe.parse_json(filters.get("branch", "[]"))
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    no_of_days = filters.get("no_of_days")
    days_diff = (getdate(to_date) - getdate(from_date)).days
    main_branch = frappe.parse_json(filters.get("main_branch", "[]"))
    final_data = []
    if branchs or main_branch:
        for row in data:
            order_qty = 0
            totstock = 0
            totsales = 0
            item_code = row.get("item_code")
            conversion_factor = row.get('conversion_factor') or 1 
            if main_branch:	
                for branch in main_branch:                    
                    row[f"{branch}stock"] = (get_stock_balance(item_code, branch, to_date)/ conversion_factor)
                    sold_qty = frappe.db.sql(f"""
                    select sum(sii.stock_qty) as qty
                    from `tabSales Invoice Item` sii, `tabSales Invoice` si
                    where sii.parent = si.name
                    and si.docstatus = 1
                    and si.is_return = 0
                    and sii.item_code = '{item_code}'
                    and si.set_warehouse = '{branch}'
                    and si.posting_date between '{from_date}' and '{to_date}'
                    """, as_dict=1)

                    sold_qty_value = (sold_qty[0]['qty'] or 0) if sold_qty else 0
                    row[f"{branch}sales"] = sold_qty_value / conversion_factor
                    diffstock = row[f"{branch}stock"]
                    totstock += diffstock
                    row["totstock"] = totstock
                    diffsales = row[f"{branch}sales"]
                    totsales += diffsales
                    row["totsales"] = totsales

                    diff = row[f"{branch}stock"] - row[f"{branch}sales"]
                    order_qty += diff

            row["order_qty"] = order_qty
            final_data.append(row)

    return columns, final_data
    
def get_columns(filters):
    cols = [
        {
            'label':"Item Code",
            'fieldname':"item_code",
            'fieldtype':"Data",
            'width': 100
        },
        {
            'label':"Item Name",
            'fieldname':"item_name",
            'fieldtype':"Data",
            'width': 150
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
    
    branch = filters.get("branch")
    if branch:
        cols.append({
            'label': f"{branch} Stock",
            'fieldname': f"{branch}stock",
            'fieldtype': "Float",
            'width': 150
        })
        cols.append({
            'label': f"{branch} Sales",
            'fieldname': f"{branch}sales",
            'fieldtype': "Float",
            'width': 150
        })
    
    main_branch = frappe.parse_json(filters.get("main_branch"))
    for branch in main_branch:
        cols.append({
            'label': f"{branch} Stock",
            'fieldname': f"{branch}stock",
            'fieldtype': "Float",
            'width': 150
        })
        cols.append({
            'label': f"{branch} Sales",
            'fieldname': f"{branch}sales",
            'fieldtype': "Float",
            'width': 150
        })
        
    
    if branch or len(main_branch) >= 0:        
        cols.append({
            'label': "Total Stock",
            'fieldname': "totstock",
            'fieldtype': "Float",
            'width': 150
        })   
        cols.append({
            'label': "Total Sales",
            'fieldname': "totsales",
            'fieldtype': "Float",
            'width': 150
        })   
        cols.append({
            'label': "Purchase Order Qty",
            'fieldname': "order_qty",
            'fieldtype': "Float",
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

    main_branch = frappe.parse_json(filters.get("main_branch"))

    if main_branch:
        if len(main_branch) == 1:
            conditions += f" and si.set_warehouse = '{main_branch[0]}'"
        else:
            warehouses = tuple(main_branch)
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
        uom = frappe.db.get_value("Item", row.get("item_code"),"purchase_uom") or row.get('stock_uom')
        qty = row.get("order_qty")
        if qty == 0:
            continue
        
        po_doc.append('items',{
            'item_code': row.get("item_code"),
            'item_name': row.get('item_name'),
            'qty': round((qty if row.get('stock_uom') == uom else qty) or 1 ),
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