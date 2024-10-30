# Copyright (c) 2023, Mekky and contributors
# For license information, please see license.txt

import frappe
from erpnext.stock.utils import get_stock_balance
from frappe import _
import json 
from frappe.utils import getdate, today

def execute(filters=None):
    if filters is None:
        filters = {}

    columns, data = [], []
    columns = get_columns(filters)
    item_conditions = get_item_conditions(filters)
    si_conditions = get_si_conditions(filters)
    
    data = frappe.db.sql(f"""
        select item_code, item_name, item_name_ar, sales_uom uom, item_type,custom_incentive_push_list incentval,
         (
            select max(price_list_rate)
            from `tabItem Price` ip
            where ip.selling = 1
            and ip.item_code = i.item_code
            limit 1
        ) as sales_price,
        (
            select conversion_factor from `tabUOM Conversion Detail` ucd where ucd.parent = item_code and ucd.uom = sales_uom and sales_uom != stock_uom
        ) conversion_factor
        from `tabItem` i
        where disabled = 0 and custom_push_list=1
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
    no_of_days = filters.get("no_of_days")
    days_diff = (getdate(to_date) - getdate(from_date)).days
    main_branch = frappe.parse_json(filters.get("main_branch", "[]"))
    final_data = []

    if branchs or main_branch:
        for row in data:
            item_code = row.get("item_code")
            conversion_factor = row.get('conversion_factor') or 1
            incent = row.get('incentval') or 1

            for branch in (branchs + main_branch):
                row[f"{branch}stock"] = get_stock_balance(item_code, branch, to_date) / conversion_factor
                
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
                
                row[f"{branch}sales"] = sold_qty[0]['qty'] / conversion_factor if sold_qty[0]['qty'] else 0
                
                avsales = row[f"{branch}sales"]
                order_qty = (avsales * incent)
                row[f"{branch}order_qty"] = order_qty if order_qty > 0 else 0

            if any(row[f"{branch}order_qty"] != 0 for branch in (branchs + main_branch)):
                final_data.append(row)
    
    return columns, final_data

def get_columns(filters):
    cols = [
        {
            'label': "Item Code",
            'fieldname': "item_code",
            'fieldtype': "Data",
            'width': 100
        },
        {
            'label': "Item Name",
            'fieldname': "item_name",
            'fieldtype': "Data",
            'width': 300
        },
        {
            'label': "Item Name AR",
            'fieldname': "item_name_ar",
            'fieldtype': "Data",
            'width': 300
        },
        {
            'label': "UOM",
            'fieldname': "uom",
            'fieldtype': "Link",
            'options': "UOM"
        },
        {
            'label': "Item Type",
            'fieldname': "item_type",
            'fieldtype': "Data",
            'width': 150
        },
        {
            'label': "Sales Price",
            'fieldname': "sales_price",
            'fieldtype': "Float"
        }
    ]
    
    branchs = frappe.parse_json(filters.get("branch", "[]"))
    main_branch = frappe.parse_json(filters.get("main_branch", "[]"))

    for branch in (branchs + main_branch):
        cols.extend([
            {
                'label': f"{branch} Sales",
                'fieldname': f"{branch}sales",
                'fieldtype': "Float",
                'width': 220
            },
            {
                'label': f"{branch} Incentive",
                'fieldname': f"{branch}order_qty",
                'fieldtype': "Float",
                'width': 220
            }
        ])
    
    return cols

def get_item_conditions(filters):
    conditions = ""    
    item_type = frappe.parse_json(filters.get("item_type"))

    if len(item_type):
        item_type = str(item_type).replace('[', '(').replace(']', ')')
        conditions += f" and item_type in {item_type}"

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
