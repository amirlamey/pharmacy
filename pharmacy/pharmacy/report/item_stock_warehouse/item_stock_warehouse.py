# Copyright (c) 2024, Mekky and contributors
# For license information, please see license.txt

# import frappe


import pymysql
import json


# Parameters
#itemcode = '96636'
#wareh = 'Sally - WH'

try:
    with connection.cursor() as cursor:
        # Fetch plus quantities
        plus_qty_query = """
        SELECT 
            warehouse,
            item_code,
            stock_uom,
            item_expiry_date,
            SUM(actual_qty) AS qty
        FROM 
            `tabStock Ledger Entry`
        WHERE 
            is_cancelled = 0 
            AND item_code = %s 
            AND warehouse = %s
        GROUP BY 
            warehouse, item_code, stock_uom, item_expiry_date
        HAVING 
            SUM(actual_qty) > 0
        ORDER BY 
            item_expiry_date
        """
        cursor.execute(plus_qty_query, (itemcode, wareh))
        plus_qty_rows = cursor.fetchall()

        # Fetch minus quantities
        minus_qty_query = """
        SELECT 
            warehouse,
            item_code,
            stock_uom,
            SUM(actual_qty) AS qty
        FROM 
            `tabStock Ledger Entry`
        WHERE 
            is_cancelled = 0 
            AND item_code = %s 
            AND warehouse = %s
        GROUP BY 
            warehouse, item_code, stock_uom
        HAVING 
            SUM(actual_qty) < 0
        """
        cursor.execute(minus_qty_query, (itemcode, wareh))
        minus_qty_row = cursor.fetchone()

        if minus_qty_row:
            minus_qty = -minus_qty_row[3]  # Convert to positive value
        else:
            minus_qty = 0

        # Adjust plus quantities by minus quantities
        adjusted_rows = []
        for row in plus_qty_rows:
            if minus_qty > 0:
                if row[4] >= minus_qty:
                    adjusted_qty = row[4] - minus_qty
                    minus_qty = 0
                else:
                    adjusted_qty = 0
                    minus_qty -= row[4]
            else:
                adjusted_qty = row[4]

            if adjusted_qty > 0:
                adjusted_rows.append((
                    row[0],  # warehouse
                    row[1],  # item_code
                    row[2],  # stock_uom
                    row[3],  # item_expiry_date
                    adjusted_qty  # qty
                ))

        # Print the result
        for adjusted_row in adjusted_rows:
            print(adjusted_row)
finally:
    connection.close()
