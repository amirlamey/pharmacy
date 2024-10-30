# Copyright (c) 2023, Mekky and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	columns, data = [], []
	columns = get_columns()
	si_conditions = get_si_conditions(filters)
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	data = frappe.db.sql(f"""
		select si.set_warehouse,
		(
			select sum(total)
			from `tabSales Invoice` ssi
			where ssi._order_type = "cash"
			and ssi.is_return = 0
			and ssi.set_warehouse = si.set_warehouse
			and ssi.docstatus = 1
			and ssi.posting_date between '{from_date}' and '{to_date}'
		) cash_sales,
		(
			select sum(total)*-1
			from `tabSales Invoice` ssi
			where ssi._order_type = "cash"
			and ssi.is_return = 1
			and ssi.set_warehouse = si.set_warehouse
			and ssi.docstatus = 1
			and ssi.posting_date between '{from_date}' and '{to_date}'
		) cash_return,
		(
			select sum(total)
			from `tabSales Invoice` ssi
			where ssi._order_type = "Call Center"
			and ssi.is_return = 0
			and ssi.set_warehouse = si.set_warehouse
			and ssi.docstatus = 1
			and ssi.posting_date between '{from_date}' and '{to_date}'
		) call_center_sales,
		(
			select sum(total)*-1
			from `tabSales Invoice` ssi
			where ssi._order_type = "Call Center"
			and ssi.is_return = 1
			and ssi.set_warehouse = si.set_warehouse
			and ssi.docstatus = 1
			and ssi.posting_date between '{from_date}' and '{to_date}'
		) call_center_return,
		(
			select sum(total)
			from `tabSales Invoice` ssi
			where ssi._order_type = "Contract"
			and ssi.is_return = 0
			and ssi.set_warehouse = si.set_warehouse
			and ssi.docstatus = 1
			and ssi.posting_date between '{from_date}' and '{to_date}'
		) contract_sales,
		(
			select sum(total)*-1
			from `tabSales Invoice` ssi
			where ssi._order_type = "Contract"
			and ssi.is_return = 1
			and ssi.set_warehouse = si.set_warehouse
			and ssi.docstatus = 1
			and ssi.posting_date between '{from_date}' and '{to_date}'
		) contract_return,
		(
			select sum(total)
			from `tabSales Invoice` ssi
			where ssi._order_type in ('cash','Call Center','Contract')
			and ssi.is_return = 0
			and ssi.set_warehouse = si.set_warehouse
			and ssi.docstatus = 1
			and ssi.posting_date between '{from_date}' and '{to_date}'
		) total_sales,
		(
			select sum(total)*-1
			from `tabSales Invoice` ssi
			where ssi._order_type in ('cash','Call Center','Contract')
			and ssi.is_return = 1
			and ssi.set_warehouse = si.set_warehouse
			and ssi.docstatus = 1
			and ssi.posting_date between '{from_date}' and '{to_date}'
		) total_return,
		(
			select if(sum(total),sum(total),0)
			from `tabSales Invoice` ssi
			where ssi._order_type in ('cash','Call Center','Contract')
			and ssi.is_return = 0
			and ssi.set_warehouse = si.set_warehouse
			and ssi.docstatus = 1
			and ssi.posting_date between '{from_date}' and '{to_date}'
		) - (
			select if(sum(total)*-1,sum(total)*-1,0)
			from `tabSales Invoice` ssi
			where ssi._order_type in ('cash','Call Center','Contract')
			and ssi.is_return = 1
			and ssi.set_warehouse = si.set_warehouse
			and ssi.docstatus = 1
			and ssi.posting_date between '{from_date}' and '{to_date}'
		) net_sales
		from `tabSales Invoice` si
		where si.docstatus = 1
		{si_conditions}
		group by si.set_warehouse
	""", as_dict=1)
	return columns, data

def get_columns():
	cols =[
		{
			'label':"Branch",
			'fieldname':"set_warehouse",
			'fieldtype':"Link",
			'options':"Warehouse",
			'width': 200
		},
		{
			'label':"Cash Sales",
			'fieldname':"cash_sales",
			'fieldtype':"Float",
			'width': 150
		},
		{
			'label':"Cash Return",
			'fieldname':"cash_return",
			'fieldtype':"Float",
			'width': 150
		},
		{
			'label':"Call Center Sales",
			'fieldname':"call_center_sales",
			'fieldtype':"Float",
			'width': 150
		},
		{
			'label':"Call Center Return",
			'fieldname':"call_center_return",
			'fieldtype':"Float",
			'width': 150
		},
		{
			'label':"Contract Sales",
			'fieldname':"contract_sales",
			'fieldtype':"Float",
			'width': 150
		},
		{
			'label':"Contract Return",
			'fieldname':"contract_return",
			'fieldtype':"Float",
			'width': 150
		},
		{
			'label':"Total Sales",
			'fieldname':"total_sales",
			'fieldtype':"Float",
			'width': 150
		},
		{
			'label':"Total Return",
			'fieldname':"total_return",
			'fieldtype':"Float",
			'width': 150
		},
		{
			'label':"Net Sales",
			'fieldname':"net_sales",
			'fieldtype':"Float",
			'width': 150
		}
	]
	return cols

def get_si_conditions(filters):
	conditions = ""
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	conditions += f" and si.posting_date between '{from_date}' and '{to_date}'"
	branchs = frappe.parse_json(filters.get("branch"))
	if len(branchs):
		branchs = str(branchs).replace('[','(').replace(']',')')
		conditions += f" and si.set_warehouse in {branchs}"
	return conditions