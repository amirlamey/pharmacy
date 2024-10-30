# Copyright (c) 2024, Mekky and contributors
# For license information, please see license.txt

# import frappe
import frappe
from frappe import _

def execute(filters=None):
    columns, data = [], []

    columns = [
        {"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Data", "width": 100},
        {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 150},
        {"label": _("Brand"), "fieldname": "brand", "fieldtype": "Data", "width": 100},
        {"label": _("Sales UOM"), "fieldname": "sales_uom", "fieldtype": "Data", "width": 100},
        {"label": _("Sales Price for Sales UOM"), "fieldname": "sales_price_uom", "fieldtype": "Currency", "width": 100},
        {"label": _("Total Stock"), "fieldname": "total_stock", "fieldtype": "Decimal", "width": 150},
        {"label": _("Total Sales QTY"), "fieldname": "total_sales_qty", "fieldtype": "Decimal", "width": 150},
        {"label": _("Average Sales Price"), "fieldname": "avg_sales_price", "fieldtype": "Currency", "width": 100},
        {"label": _("Total Before Discount"), "fieldname": "total_before", "fieldtype": "Currency", "width": 150},
        {"label": _("Total Discount Amount"), "fieldname": "total_discount_amount", "fieldtype": "Currency", "width": 150},
        {"label": _("Total Net Sales"), "fieldname": "total_net_sales", "fieldtype": "Currency", "width": 150},
        {"label": _("Average Valuation Rate"), "fieldname": "avg_valuation_rate", "fieldtype": "Currency", "width": 150},
        {"label": _("Total Valuation Rate"), "fieldname": "total_valuation_rate", "fieldtype": "Currency", "width": 150},
        {"label": _("Total Revenue"), "fieldname": "total_revenue", "fieldtype": "Currency", "width": 150},
        {"label": _("Average Revenue Percent"), "fieldname": "avg_revenue_percent", "fieldtype": "Percent", "width": 100},
    ]

    conditions = []
    if filters.get("from_date"):
        conditions.append("si.due_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("si.due_date <= %(to_date)s")
    if filters.get("item_type"):
        conditions.append("item.item_type = %(item_type)s")
    if filters.get("brand"):
        conditions.append("item.brand = %(brand)s")
    if filters.get("warehouse"):
        conditions.append("sii.warehouse = %(warehouse)s")
    if filters.get("employee"):
        conditions.append("si.sales_man = %(employee)s")
    if filters.get("order_type"):
        conditions.append("si._order_type = %(order_type)s")

    conditions = " AND ".join(conditions)

    query = """
        SELECT 
            item.item_code,
            item.item_name,
            item.brand,
            item.sales_uom,
            (SELECT price_list_rate FROM `tabItem Price` WHERE item_code = sii.item_code AND uom = item.sales_uom ORDER BY valid_from DESC LIMIT 1) AS sales_price_uom,
            (CASE 
        WHEN item.sales_uom = item.stock_uom THEN bin.actual_qty 
        ELSE (CAST(bin.actual_qty AS DECIMAL(10, 2)) / 
              COALESCE((SELECT CAST(conversion_factor AS DECIMAL(10, 2)) 
                        FROM `tabUOM Conversion Detail` ucd 
                        WHERE ucd.parent = item.item_code 
                          AND ucd.uom = item.sales_uom 
                        LIMIT 1), 1)) 
     END) AS total_stock,
     (CASE 
        WHEN item.sales_uom = item.stock_uom THEN SUM(sii.stock_qty)
        ELSE (CAST(SUM(sii.stock_qty) AS DECIMAL(10, 2)) / 
              COALESCE((SELECT CAST(conversion_factor AS DECIMAL(10, 2)) 
                        FROM `tabUOM Conversion Detail` ucd 
                        WHERE ucd.parent = item.item_code 
                          AND ucd.uom = item.sales_uom 
                        LIMIT 1), 1)) 
     END) AS total_sales_qty,
            SUM(sii.stock_qty) AS total_sales_qty2,
            AVG(sii.rate) AS avg_sales_price,
            SUM((sii.discount_amount * sii.stock_qty)+sii.base_net_amount) AS total_before,
            SUM(sii.discount_amount * sii.stock_qty) AS total_discount_amount,
            SUM(sii.base_net_amount) AS total_net_sales,
            AVG(item.valuation_rate) AS avg_valuation_rate,
            SUM(item.valuation_rate * sii.qty) AS total_valuation_rate,
            SUM(sii.base_net_amount - (item.valuation_rate * sii.qty)) AS total_revenue,
            AVG(((sii.base_net_amount - (item.valuation_rate * sii.qty)) / sii.base_net_amount) * 100) AS avg_revenue_percent
        FROM 
            `tabSales Invoice Item` sii
        JOIN 
            `tabSales Invoice` si ON si.name = sii.parent
        JOIN 
            `tabItem` item ON item.name = sii.item_code        
        LEFT JOIN 
            `tabBin` bin ON bin.item_code = sii.item_code AND bin.warehouse = sii.warehouse
        WHERE 
            si.docstatus = 1
            {conditions}
        GROUP BY 
            item.item_code, item.item_name, item.brand, item.sales_uom
    """.format(conditions=(" AND " + conditions if conditions else ""))

    data = frappe.db.sql(query, filters, as_dict=1)

    return columns, data
