import frappe
from frappe.model.mapper import get_mapped_doc

@frappe.whitelist()
def create_salary_slip(salary_slip_doc, doc_event):
    hours = frappe.db.sql(f"""select sum(working_hours) from `tabAttendance` where employee = '{salary_slip_doc.employee}' and docstatus = 1 and attendance_date between '{salary_slip_doc.start_date}' and '{salary_slip_doc.end_date}' """, as_dict=True) 
    if hours[0]['sum(working_hours)']:
        salary_slip_doc.overtime_per_hours = hours[0]['sum(working_hours)']
    else:
        salary_slip_doc.overtime_per_hours = 0
