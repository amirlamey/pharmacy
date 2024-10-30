frappe.ui.form.on('Sales Invoice', {

    setup(frm) {
        frm.set_query('uom','items', function(doc, cdt, cdn) {
           let row = locals[cdt][cdn];
            return {
                query: "pharmacy.controllers.sales_invoice_item.get_item_uom",
                filters: {
                    'item_code': row.item_code
                }
            }
        })
    }
    
})
    
