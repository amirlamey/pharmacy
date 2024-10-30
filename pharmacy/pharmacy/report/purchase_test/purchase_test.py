import frappe
from frappe.utils import getdate

def execute(filters=None):
    if filters is None:
        filters = {}

    columns = get_columns(filters)
    item_conditions = get_item_conditions(filters)
    si_conditions = get_si_conditions(filters)

    data = frappe.db.sql("""
        SELECT 
            item_code, 
            item_name, 
            item_name_ar, 
            item_group, 
            sales_uom AS stock_uom, 
            active_ingredient, 
            origin, 
            item_type, 
            brand, 
            related_to,
            (SELECT price_list_rate
             FROM tabItem Price ip
             WHERE ip.selling = 1 AND ip.item_code = i.item_code
             LIMIT 1) AS sales_price,
            (SELECT conversion_factor 
             FROM tabUOM Conversion Detail ucd 
             WHERE ucd.parent = i.item_code AND ucd.uom = i.sales_uom AND i.sales_uom != i.stock_uom) AS conversion_factor
        FROM tabItem i
        WHERE disabled = 0 
          AND i.related_to IS NULL
          AND (SELECT COUNT(sii.name)
               FROM tabSales Invoice Item sii
               INNER JOIN tabSales Invoice si ON sii.parent = si.name
               WHERE sii.docstatus = 1
                 AND sii.item_code = i.name
                 AND si.is_return = 0
                 {si_conditions}) > 0
          {item_conditions}
    """.format(si_conditions=si_conditions, item_conditions=item_conditions), as_dict=1)

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
            item_code = row.get("item_code")
            conversion_factor = row.get('conversion_factor') or 1
            if main_branch:
                for branch in main_branch:
                    sold_qty = frappe.db.sql("""
                        WITH BinStock AS (
                            SELECT nb.item_code,
                                   ROUND(SUM(nb.actual_qty) / 
                                   (SELECT MAX(conversion_factor) FROM tabUOM Conversion Detail WHERE parent = nb.item_code), 1) AS Stock
                            FROM tabBin nb
                                INNER JOIN tabItem ON tabItem.item_code = nb.item_code 
            WHERE 
                tabItem.related_to IS NULL
            GROUP BY
                nb.item_code
                        ),
                        RelatedStock AS (
                            SELECT ni.related_to AS item_code,
                                   ROUND(SUM(nb.actual_qty) / 
                                   (SELECT MAX(conversion_factor) FROM tabUOM Conversion Detail WHERE parent = ni.related_to), 1) AS Stock
                            FROM tabBin nb
                            INNER JOIN tabItem ni ON nb.item_code = ni.item_code
                            WHERE ni.related_to IS NOT NULL
                            GROUP BY ni.related_to
                        ),
                        SalesData AS (
                            SELECT sod.item_code,
                                   SUM(CASE WHEN soh.is_return = 0 THEN ROUND(sod.stock_qty/(SELECT MAX(conversion_factor) FROM tabUOM Conversion Detail WHERE parent = sod.item_code), 1) ELSE 0 END) AS TotalSales
                            FROM tabSales Invoice Item sod
                            INNER JOIN tabSales Invoice soh ON sod.parent = soh.name
                            INNER JOIN tabItem ni ON ni.item_code = sod.item_code
                            WHERE soh.docstatus = 1 AND sod.stock_qty >0 AND ni.related_to  IS NULL
                              AND soh.set_warehouse = '{branch}'
                              AND soh.posting_date BETWEEN '{from_date}' AND '{to_date}'
                            GROUP BY sod.item_code
                        ),
                        ReturnData AS (
                            SELECT sod.item_code,
                                   SUM(CASE WHEN soh.is_return = 1 THEN ROUND(sod.stock_qty/(SELECT MAX(conversion_factor) FROM tabUOM Conversion Detail WHERE parent = sod.item_code), 1) ELSE 0 END) AS TotalReturns
                            FROM tabSales Invoice Item sod
                            INNER JOIN tabSales Invoice soh ON sod.parent = soh.name
                            INNER JOIN tabItem ni ON ni.item_code = sod.item_code
                            WHERE soh.docstatus = 1 AND sod.stock_qty >0 AND ni.related_to  IS NULL
                              AND soh.set_warehouse = '{branch}'
                              AND soh.posting_date BETWEEN '{from_date}' AND '{to_date}'
                            GROUP BY sod.item_code
                        ),
                        RelatedSalesData AS (
                            SELECT ni.related_to AS itemcode,
                                   SUM(CASE WHEN soh.is_return = 0 THEN ROUND(sod.stock_qty/(SELECT MAX(conversion_factor) FROM tabUOM Conversion Detail WHERE parent = sod.item_code), 1) ELSE 0 END) AS TotalSales
                            FROM tabSales Invoice Item sod
                            INNER JOIN tabSales Invoice soh ON sod.parent = soh.name
                            INNER JOIN tabItem ni ON sod.item_code = ni.item_code
                            WHERE ni.related_to IS NOT NULL                              
                              AND soh.set_warehouse = '{branch}'
                              AND soh.docstatus = 1 AND sod.stock_qty >0
                              AND soh.posting_date BETWEEN '{from_date}' AND '{to_date}'
                            GROUP BY ni.related_to
                        ),
                        RelatedReturnData AS (
                            SELECT ni.related_to AS itemcode,
                                   SUM(CASE WHEN soh.is_return = 1 THEN ROUND(sod.stock_qty/(SELECT MAX(conversion_factor) FROM tabUOM Conversion Detail WHERE parent = sod.item_code), 1) ELSE 0 END) AS TotalReturns
                            FROM tabSales Invoice Item sod
                            INNER JOIN tabSales Invoice soh ON sod.parent = soh.name
                            INNER JOIN tabItem ni ON sod.item_code = ni.item_code
                            WHERE ni.related_to IS NOT NULL                              
                              AND soh.set_warehouse = '{branch}'
                              AND soh.docstatus = 1 AND sod.stock_qty >0
                              AND soh.posting_date BETWEEN '{from_date}' AND '{to_date}'
                            GROUP BY ni.related_to
                        )
                        SELECT
                            ROUND(IFNULL(bs.Stock, 0) + IFNULL(rs.Stock, 0), 1) AS stock,
                            ROUND(IFNULL(sd.TotalSales, 0) + IFNULL(rsd.TotalSales, 0), 1) AS Sales,
                            ROUND(IFNULL(rd.TotalReturns, 0) + IFNULL(rrd.TotalReturns, 0), 1) AS Return,
                            ROUND(IFNULL(sd.TotalSales, 0) + IFNULL(rsd.TotalSales, 0) - IFNULL(rd.TotalReturns, 0) - IFNULL(rrd.TotalReturns, 0), 1) AS NetSales
                        FROM tabItem i
                        LEFT JOIN BinStock bs ON i.item_code = bs.item_code
                        LEFT JOIN RelatedStock rs ON i.item_code = rs.item_code
                        INNER JOIN SalesData sd ON i.item_code = sd.item_code AND sd.TotalSales > 0
                        LEFT JOIN ReturnData rd ON i.item_code = rd.item_code
                        LEFT JOIN RelatedSalesData rsd ON i.item_code = rsd.itemcode AND rsd.TotalSales > 0
                        LEFT JOIN RelatedReturnData rrd ON i.item_code = rrd.itemcode
                        WHERE (COALESCE(sd.TotalSales, 0) + COALESCE(rsd.TotalSales, 0)) > 0
                        AND i.related_to IS NULL AND i.item_code = '{item_code}'
                    """.format(branch=branch, from_date=from_date, to_date=to_date, item_code=item_code), as_dict=1)
                    if sold_qty:
                        row[f"{branch}stock"] = sold_qty[0].get('stock', 0) if sold_qty[0].get('stock') is not None else 0
                        row[f"{branch}NetSales"] = sold_qty[0].get('NetSales', 0) if sold_qty[0].get('NetSales') is not None else 0
                        avsales = row[f"{branch}NetSales"] / days_diff
                        diff = ((avsales * no_of_days) - row[f"{branch}stock"])
                        order_qty += max(diff, 0)
            row["order_qty"] = order_qty / conversion_factor
            if row["order_qty"] != 0:
                final_data.append(row)

    return columns, final_data

def get_columns(filters):
    cols = [
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Data", "width": 100},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 200},
        {"label": "Item Name AR", "fieldname": "item_name_ar", "fieldtype": "Data", "width": 200},
        {"label": "Item Group", "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 150},
        {"label": "Default UOM", "fieldname": "stock_uom", "fieldtype": "Link", "options": "UOM"},
        {"label": "Active Ingredient", "fieldname": "active_ingredient", "fieldtype": "Link", "options": "Active Ingredient", "width": 150},
        {"label": "Origin", "fieldname": "origin", "fieldtype": "Link", "options": "Origin"},
        {"label": "Item Type", "fieldname": "item_type", "fieldtype": "Data", "width": 150},
        {"label": "Brand", "fieldname": "brand", "fieldtype": "Link", "options": "Brand", "width": 150},
        {"label": "Related To", "fieldname": "related_to", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": "Sales Price", "fieldname": "sales_price", "fieldtype": "Float"}
    ]

    branch = filters.get("branch")
    if branch:
        cols.append({"label": "{} Stock".format(branch), "fieldname": "{}stock".format(branch), "fieldtype": "Float", "width": 150})
        cols.append({"label": "{} Sales".format(branch), "fieldname": "{}sales".format(branch), "fieldtype": "Float", "width": 150})

    main_branch = frappe.parse_json(filters.get("main_branch", "[]"))
    for branch in main_branch:
        cols.append({"label": "{} Stock".format(branch), "fieldname": "{}stock".format(branch), "fieldtype": "Float", "width": 150})
        cols.append({"label": "{} Sales".format(branch), "fieldname": "{}NetSales".format(branch), "fieldtype": "Float", "width": 150})

    if branch or len(main_branch) > 0:
        cols.append({"label": "Purchase Order Qty", "fieldname": "order_qty", "fieldtype": "Float", "width": 150})

    return cols

def get_item_conditions(filters):
    conditions = []
    item_group = frappe.parse_json(filters.get("item_group", "[]"))
    origin = frappe.parse_json(filters.get("origin", "[]"))
    active_ingredient = frappe.parse_json(filters.get("active_ingredient", "[]"))
    item_type = frappe.parse_json(filters.get("item_type", "[]"))
    brand = frappe.parse_json(filters.get("brand", "[]"))

    if item_group:
        conditions.append("item_group IN ({})".format(', '.join("'{}'".format(x) for x in item_group)))

    if origin:
        conditions.append("origin IN ({})".format(', '.join("'{}'".format(x) for x in origin)))

    if active_ingredient:
        conditions.append("active_ingredient IN ({})".format(', '.join("'{}'".format(x) for x in active_ingredient)))

    if item_type:
        conditions.append("item_type IN ({})".format(', '.join("'{}'".format(x) for x in item_type)))

    if brand:
        conditions.append("brand IN ({})".format(', '.join("'{}'".format(x) for x in brand)))

    return " AND " + " AND ".join(conditions) if conditions else ""

def get_si_conditions(filters):
    conditions = []
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    conditions.append("si.posting_date BETWEEN '{}' AND '{}'".format(from_date, to_date))

    main_branch = frappe.parse_json(filters.get("main_branch", "[]"))

    if main_branch:
        if len(main_branch) == 1:
            conditions.append("si.set_warehouse = '{}'".format(main_branch[0]))
        else:
            conditions.append("si.set_warehouse IN ({})".format(', '.join("'{}'".format(x) for x in main_branch)))

    return " AND " + " AND ".join(conditions) if conditions else ""