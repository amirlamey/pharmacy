import frappe

from frappe import _
import json
from frappe.utils import getdate, today

def execute(filters=None):
    if filters is None:
        filters = {}

    columns = get_columns(filters)
    si_conditions = get_si_conditions(filters)

    query = """
    WITH EmployeeLogs AS (
        SELECT 
            employee_id,
            (SELECT employee_name FROM `tabEmployee` WHERE `tabEmployee`.`name` = employee_id) AS employee_name,            
            branch,
            log_type_in,
            date_log_in,
            log_type_out,
            date_log_out,
            FLOOR(TIMESTAMPDIFF(MINUTE, date_log_in, date_log_out) / 60) AS hours,
            CEIL(TIMESTAMPDIFF(SECOND, date_log_in, date_log_out) / 60) % 60 AS minutes
        FROM 
            `tabBranches Check IN OUT`
        WHERE
            {si_conditions}
        ORDER BY 
            employee_id, date_log_in
    ),
    EmployeeTotals AS (
        SELECT 
            employee_id,
            (SELECT employee_name FROM `tabEmployee` WHERE `tabEmployee`.`name` = employee_id) AS employee_name,
            FLOOR(SUM(CEIL(TIMESTAMPDIFF(SECOND, date_log_in, date_log_out) / 60)) / 60) AS total_hours,
            SUM(CEIL(TIMESTAMPDIFF(SECOND, date_log_in, date_log_out) / 60)) % 60 AS total_minutes
        FROM 
            `tabBranches Check IN OUT`
        WHERE
            {si_conditions}
        GROUP BY 
            employee_id
    )

    SELECT 
        el.employee_id,
        el.employee_name,
        (SELECT designation FROM `tabEmployee` WHERE `tabEmployee`.`name` = el.employee_id) AS designation,
        el.branch,
        el.log_type_in,
        el.date_log_in,
        el.log_type_out,
        el.date_log_out,
        el.hours,
        el.minutes,
        et.total_hours + FLOOR(et.total_minutes / 60) AS total_hours,
        MOD(et.total_minutes, 60) AS total_minutes
    FROM 
        EmployeeLogs el
    JOIN 
        EmployeeTotals et ON el.employee_id = et.employee_id
    ORDER BY 
        el.employee_id, el.date_log_in
    """.format(si_conditions=si_conditions)

    data = frappe.db.sql(query, as_dict=True)

    return columns, data

def get_columns(filters):
    return [
        {
            "fieldname": "employee_id",
            "label": "Employee ID",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "employee_name",
            "label": "Employee Name",
            "fieldtype": "Data",
            "width": 200
        },
        {
            "fieldname": "designation",
            "label": "Designation",
            "fieldtype": "Data",
            "width": 200
        },
         {
            "fieldname": "branch",
            "label": "Branch",
            "fieldtype": "Data",
            "width": 200
        },
        {
            "fieldname": "log_type_in",
            "label": "Type",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "date_log_in",
            "label": "Log In Date",
            "fieldtype": "Datetime",
            "width": 200
        },
        {
            "fieldname": "log_type_out",
            "label": "Type1",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "date_log_out",
            "label": "Log Out Date",
            "fieldtype": "Datetime",
            "width": 200
        },
        {
            "fieldname": "hours",
            "label": "Hours",
            "fieldtype": "Int",
            "width": 150
        },
        {
            "fieldname": "minutes",
            "label": "Minutes",
            "fieldtype": "Int",
            "width": 150
        },
        {
            "fieldname": "total_hours",
            "label": "Total Hours",
            "fieldtype": "Int",
            "width": 150
        },
        {
            "fieldname": "total_minutes",
            "label": "Total Minutes",
            "fieldtype": "Int",
            "width": 150
        }
    ]

def get_si_conditions(filters):
    from_date = frappe.utils.formatdate(filters.get("from_date"), 'yyyy-MM-dd') if filters.get("from_date") else ''
    to_date = frappe.utils.formatdate(filters.get("to_date"), 'yyyy-MM-dd') if filters.get("to_date") else ''
    emp = filters.get("emp") or ''
    branch = filters.get("branch") or ''
    
    conditions = f"""
    (branch = '{branch}' OR '{branch}' = '' OR '{branch}' IS NULL)
    AND (employee_id = '{emp}' OR '{emp}' = '' OR '{emp}' IS NULL)
    AND ('{from_date}' = '' OR '{to_date}' = '' OR date_log_in BETWEEN '{from_date}' AND '{to_date}')
    """
    return conditions
