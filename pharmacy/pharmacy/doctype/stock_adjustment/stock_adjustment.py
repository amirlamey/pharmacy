# Copyright (c) 2024, Mekky and contributors
# For license information, please see license.txt

import frappe
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document
from typing import Optional

from frappe import _, bold, msgprint
from frappe.query_builder.functions import CombineDatetime, Sum
from frappe.utils import add_to_date, cint, cstr, flt

import erpnext
from erpnext.accounts.utils import get_company_default
from erpnext.controllers.stock_controller import StockController
from erpnext.stock.doctype.batch.batch import get_available_batches, get_batch_qty
from erpnext.stock.doctype.inventory_dimension.inventory_dimension import get_inventory_dimensions
from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
	get_available_serial_nos,
)
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.utils import get_stock_balance
from erpnext.stock.get_item_details import get_conversion_factor


class StockAdjustment(Document):
	def before_save(self):
		invalid_items = []
		for item in self.items:
			if item.using_date_expire and not item.item_expiry_date:
				invalid_items.append(f'{item.idx}')
		if invalid_items:
			invalid_items = ','.join(invalid_items)
			frappe.throw(f'Row#{invalid_items} Expiry Date Is Missing!')
			
		for StockAdjustment_item in self.items:
			item_doc = frappe.get_doc("Item", StockAdjustment_item.item_code)
			for uom in item_doc.uoms:
				if StockAdjustment_item.uom == uom.uom:
					factor = uom.conversion_factor
					StockAdjustment_item.conversion = factor
			StockAdjustment_item.qty = StockAdjustment_item.conversion * StockAdjustment_item.st_quantity
	
	def on_submit(self):
		create_stock_entry(self)
		create_stock_adjustment_record(self)

	@frappe.whitelist()
	def fetch_related_items(self):
		item_code = self.item_code
		for item in self.items:
			if item.item_code == item_code:
				frappe.msgprint(f"Item {frappe.bold(item_code)} Already Added!")
				return
		warehouse = self.set_warehouse
		items = frappe.db.sql("""
		SELECT warehouse,item_code,
		(
			select sales_uom
			from `tabItem` i
			where i.name = sle.item_code
		) sales_uom,
		(
			select item_name
			from `tabItem` i
			where i.name = sle.item_code
		) item_name,
		item_expiry_date, SUM(actual_qty) AS qty,
		(
			select custom_using_date_expire from `tabItem` i where i.name = sle.item_code
		) using_expiry_date
		FROM `tabStock Ledger Entry` sle
		WHERE is_cancelled = 0 AND (item_code = %(item_code)s) AND (warehouse = %(warehouse)s) 
		GROUP BY warehouse,item_code,sales_uom, item_expiry_date
		HAVING SUM(actual_qty) != 0
		""", values={
			'item_code': item_code,
			'warehouse': warehouse
		},as_dict=1)
		if not items:
			items = frappe.db.sql("""
				SELECT custom_using_date_expire using_expiry_date, sales_uom, item_code, %(warehouse)s warehouse, item_name
				FROM `tabItem`
				WHERE item_code = %(item_code)s
				""", values={
					'item_code': item_code,
					'warehouse': warehouse
				},as_dict=1)
		
		for item in items:
			conversion_factor = get_conversion_factor(item.item_code, item.sales_uom).get('conversion_factor')
			item.stock_sales = item.qty / conversion_factor if item.qty else 0
		return items
	
	@frappe.whitelist()
	def fetch_related_items_barcode(self):
		barcode = self.scan_barcode_new
		item_code = frappe.db.get_value('Item Barcode',{'parenttype': 'Item', 'barcode': barcode}, 'parent')
		if not item_code:
			frappe.msgprint('Cannot find Item with this Barcode')
			return
		for item in self.items:
			if item.item_code == item_code:
				frappe.msgprint(f"Item {frappe.bold(item_code)} Already Added!")
				return
		warehouse = self.set_warehouse
		items = frappe.db.sql("""
		SELECT warehouse,item_code,
		(
			select sales_uom
			from `tabItem` i
			where i.name = sle.item_code
		) sales_uom,
		(
			select item_name
			from `tabItem` i
			where i.name = sle.item_code
		) item_name,
		item_expiry_date, SUM(actual_qty) AS qty,
		(
			select custom_using_date_expire from `tabItem` i where i.name = sle.item_code
		) using_expiry_date
		FROM `tabStock Ledger Entry` sle
		WHERE is_cancelled = 0 AND (item_code = %(item_code)s) AND (warehouse = %(warehouse)s) 
		GROUP BY warehouse,item_code,sales_uom, item_expiry_date
		HAVING SUM(actual_qty) != 0
		""", values={
			'item_code': item_code,
			'warehouse': warehouse
		},as_dict=1)
		if not items:
			items = frappe.db.sql("""
				SELECT custom_using_date_expire using_expiry_date, sales_uom, item_code, %(warehouse)s warehouse, item_name
				FROM `tabItem`
				WHERE item_code = %(item_code)s
				""", values={
					'item_code': item_code,
					'warehouse': warehouse
				},as_dict=1)
		
		for item in items:
			conversion_factor = get_conversion_factor(item.item_code, item.sales_uom).get('conversion_factor')
			item.stock_sales = item.qty / conversion_factor if item.qty else 0
		return items

def create_stock_reconciliation(self):
	stock_reconciliation = get_mapped_doc(
		"Stock Adjustment",
		self.name,
		{
			"Stock Adjustment": {
				"doctype": "Stock Reconciliation",
				"field_map": {
					"stock_adjustment": "name",
				}
			},
			"Stock Adjustment Item": {
				"doctype": "Stock Reconciliation Item",
			},
		},
	)
	stock_reconciliation.save()
	stock_reconciliation.submit()
	frappe.db.commit()
	frappe.msgprint(f"""Stock Reconciliation <strong><a href = "/app/Form/Stock Reconciliation/{stock_reconciliation.name}">{stock_reconciliation.name} </a></strong> created<br>""")
	
def create_stock_adjustment_record(self):
	stock_adjustment = frappe.new_doc("Stock Adjustment Record")
	stock_adjustment.stock_adjustment = self.name
	stock_adjustment.posting_date = self.posting_date
	stock_adjustment.warehouse = self.set_warehouse
	# get list of items in bin doctype where warehouse is the same as the warehouse in stock adjustment
	# for each item in the list, add it to the stock adjustment record
	bin_list = frappe.get_list("Bin", filters={"warehouse": self.set_warehouse, "actual_qty": [">", 0]}, fields=["item_code", "actual_qty", "valuation_rate"])
	for bin in bin_list:
		stock_adjustment.append("items", {
			"item_code": bin.item_code,
			"qty": bin.actual_qty,
			"valuation_rate": bin.valuation_rate,
			"warehouse": self.set_warehouse,
			"amount": bin.actual_qty * bin.valuation_rate
		})
	stock_adjustment.save()
	stock_adjustment.submit()
	frappe.db.commit()
	frappe.msgprint(f"""Stock Adjustment Record <strong><a href = "/app/Form/Stock Adjustment Record/{stock_adjustment.name}">{stock_adjustment.name} </a></strong> created""")

def create_stock_entry(self):
	# make 2 list of items, one for items with current_qty - qty < 0 and the other for items with current_qty - qty > 0
	# for each item in the list, create a stock entry
	material_receipt = []
	material_issue = []
	for item in self.items:
		if item.current_qty - item.qty < 0:
			material_receipt.append(item)			
		elif item.current_qty - item.qty > 0:
			material_issue.append(item)
	# create material receipt
	if material_receipt:
		mr = frappe.new_doc("Stock Entry")
		mr.custom_stock_adjustment = self.name
		mr.purpose = "Material Receipt"
		mr.stock_entry_type = "Material Receipt"
		mr.from_warehouse = self.set_warehouse
		mr.to_warehouse = self.set_warehouse
		for item in material_receipt:
			mr.append("items", {
				"item_code": item.item_code,
				"qty": item.qty - item.current_qty,
				"valuation_rate": item.valuation_rate,
				"warehouse": self.set_warehouse,
				"to_item_expiry_date": item.item_expiry_date
			})
		mr.save()
		frappe.msgprint(f"""Material Receipt <strong><a href = "/app/Form/Stock Entry/{mr.name}">{mr.name} </a></strong> created""")
	# create material issue
	if material_issue:
		mi = frappe.new_doc("Stock Entry")
		mi.custom_stock_adjustment = self.name
		mi.purpose = "Material Issue"
		mi.stock_entry_type = "Material Issue"
		mi.from_warehouse = self.set_warehouse
		mi.to_warehouse = self.set_warehouse
		for item in material_issue:
			mi.append("items", {
				"item_code": item.item_code,
				"qty": item.current_qty - item.qty,
				"valuation_rate": item.valuation_rate,
				"warehouse": self.set_warehouse,
				"item_expiry_date": item.item_expiry_date
			})
		mi.save()
		frappe.msgprint(f"""Material Issue <strong><a href = "/app/Form/Stock Entry/{mi.name}">{mi.name} </a></strong> created""")

@frappe.whitelist()
def get_items(
	warehouse, posting_date, posting_time, company, item_code=None, ignore_empty_stock=False
):
	ignore_empty_stock = cint(ignore_empty_stock)
	items = [frappe._dict({"item_code": item_code, "warehouse": warehouse})]

	if not item_code:
		items = get_items_for_stock_reco(warehouse, company)

	res = []
	itemwise_batch_data = get_itemwise_batch(warehouse, posting_date, company, item_code)

	for d in items:
		if d.item_code in itemwise_batch_data:
			valuation_rate = get_stock_balance(
				d.item_code, d.warehouse, posting_date, posting_time, with_valuation_rate=True
			)[1]

			for row in itemwise_batch_data.get(d.item_code):
				if ignore_empty_stock and not row.qty:
					continue

				args = get_item_data(row, row.qty, valuation_rate)
				res.append(args)
		else:
			stock_bal = get_stock_balance(
				d.item_code,
				d.warehouse,
				posting_date,
				posting_time,
				with_valuation_rate=True,
				with_serial_no=cint(d.has_serial_no),
			)
			qty, valuation_rate, serial_no = (
				stock_bal[0],
				stock_bal[1],
				stock_bal[2] if cint(d.has_serial_no) else "",
			)

			if ignore_empty_stock and not stock_bal[0]:
				continue

			args = get_item_data(d, qty, valuation_rate, serial_no)

			res.append(args)
	if len(res) >1:
		# get row that its batch_no will expired first
		for row in res:
			if row.get("batch_no"):
				expiry_date = frappe.get_value("Batch", row.get("batch_no"), "expiry_date")
				row["expiry_date"] = expiry_date
		# get the row with the earliest expiry date
		res = get_batch_expiry(res)
		return res
	else:
		return res
def get_batch_expiry(res):
	# sort the list of dictionary by expiry date
	res = sorted(res, key=lambda x: x.get("expiry_date"))
	return res

def get_itemwise_batch(warehouse, posting_date, company, item_code=None):
	from erpnext.stock.report.batch_wise_balance_history.batch_wise_balance_history import execute

	itemwise_batch_data = {}

	filters = frappe._dict(
		{"warehouse": warehouse, "from_date": posting_date, "to_date": posting_date, "company": company}
	)

	if item_code:
		filters.item_code = item_code

	columns, data = execute(filters)

	for row in data:
		itemwise_batch_data.setdefault(row[0], []).append(
			frappe._dict(
				{
					"item_code": row[0],
					"warehouse": warehouse,
					"qty": row[8],
					"item_name": row[1],
					"batch_no": row[4],
				}
			)
		)

	return itemwise_batch_data


def get_item_data(row, qty, valuation_rate, serial_no=None):
	return {
		"item_code": row.item_code,
		"warehouse": row.warehouse,
		"qty": qty,
		"item_name": row.item_name,
		"valuation_rate": valuation_rate,
		"current_qty": qty,
		"current_valuation_rate": valuation_rate,
		"current_serial_no": serial_no,
		"serial_no": serial_no,
		"batch_no": row.get("batch_no"),
	}
