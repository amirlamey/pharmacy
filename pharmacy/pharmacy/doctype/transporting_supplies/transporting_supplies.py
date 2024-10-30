# Copyright (c) 2023, Mekky and contributors
# For license information, please see license.txt

import frappe
from itertools import groupby
from operator import attrgetter
from frappe.model.document import Document

class TransportingSupplies(Document):
	def on_submit(self):
		if self.items:
			# Sort students data by Target Warehouse key.
			items = sorted(self.items,key = attrgetter('t_warehouse'))
			# Iterate over the groupby object
			for key, group in groupby(items, key = attrgetter('t_warehouse')):
				stock_entry = frappe.new_doc("Stock Entry")
				stock_entry.purpose = "Material Transfer"
				stock_entry.stock_entry_type = "Material Transfer"
				stock_entry.set_posting_time = 1
				stock_entry.posting_date = self.posting_date
				stock_entry.posting_time = self.posting_time
				stock_entry.transporting_supplies = self.name
				for row in group:
					stock_entry.append("items",{
						"item_code": row.item_code,
						"qty": row.qty,
						"t_warehouse": row.t_warehouse,
						"s_warehouse": row.s_warehouse
					})
				stock_entry.save()

					
