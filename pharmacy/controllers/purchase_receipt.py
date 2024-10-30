
import frappe
import pandas as pd
import json
@frappe.whitelist()
def validate_batch_no(doc,doc_event):
	if doc.items:
		for item in doc.items:
			if (not item.serial_and_batch_bundle or item.serial_and_batch_bundle == "") and item.expiry_date:
				
				batch_no = frappe.db.get_value("Batch",{"item":item.item_code,"expiry_date":item.expiry_date},"name")
				if batch_no:
					serial_and_batch_bundle = frappe.new_doc("Serial and Batch Bundle")
					serial_and_batch_bundle.item_code = item.item_code
					serial_and_batch_bundle.warehouse = item.warehouse
					serial_and_batch_bundle.type_of_transaction = "Inward"
					serial_and_batch_bundle.voucher_type = "Purchase Receipt"
					# serial_and_batch_bundle.voucher_no = doc.name
					serial_and_batch_bundle.append("entries",{
						"batch_no": batch_no,
						"qty": item.qty
					})
					serial_and_batch_bundle.save()
					item.serial_and_batch_bundle = serial_and_batch_bundle.name
					
				

def validate_batch_no_on_submit(doc,doc_event):
	if doc.voucher_type == "Purchase Receipt":
		pr = frappe.get_doc("Purchase Receipt",doc.voucher_no)
		if pr.items:
			for item in pr.items:
				if item.name == doc.voucher_detail_no:
					if doc.entries:
						for entry in doc.entries:
							if entry.batch_no:
								batch = frappe.get_doc("Batch",entry.batch_no)
								batch.expiry_date = item.expiry_date
								batch.save()
								frappe.db.commit()
					
	