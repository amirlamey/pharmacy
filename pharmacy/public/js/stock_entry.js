frappe.ui.form.on('Stock Entry', {
    setup(frm) {
        frm.set_query('uom','items', function(doc, cdt, cdn) {
           let row = locals[cdt][cdn];
            return {
                query: "pharmacy.controllers.stock_entry_item.get_item_uom",
                filters: {
                    'item_code': row.item_code
                }
            }
        })
    },
    validate(frm){
        if(frm.doc.stock_entry_type == 'Material Transfer'){
            frm.doc.items.forEach(item => {
                if(!item.s_warehouse){
                    frappe.model.set_value(item.doctype, item.name, 's_warehouse', frm.doc.from_warehouse)
                }
            });
        }
    }
})
    
frappe.ui.form.on('Stock Entry Detail', {
    item_code(frm,cdt,cdn){
        // frappe.model.set_value(cdt,cdn, 'qty', 0)
        // frappe.model.set_value(cdt,cdn, 'item_expiry_date', '')
        set_expiry_date(frm,cdt,cdn)
        set_expiry_date_qty(frm,cdt,cdn)
    },
    s_warehouse(frm,cdt,cdn){
        set_expiry_date(frm,cdt,cdn)
        set_expiry_date_qty(frm,cdt,cdn)
    },
    item_expiry_date(frm,cdt,cdn){
        set_expiry_date_qty(frm,cdt,cdn)
    },
    uom(frm,cdt,cdn){
        set_expiry_date_qty(frm,cdt,cdn)
    },
    qty(frm,cdt,cdn){
        if(frm.doc.stock_entry_type == 'Material Transfer'){
            set_expiry_date_qty(frm,cdt,cdn)
            setTimeout(()=>{
                let row = locals[cdt][cdn]
                if(row.custom_using_date_expire && row.qty > row.custom_expiry_date_qty){
                    frappe.model.set_value(cdt,cdn, 'qty', 0)
                    frappe.msgprint("Qty Must Be Less Than Or Equal To Expiry Date Qty!")
                }
            }, 500)
        }
    },
})

function set_expiry_date_qty(frm,cdt,cdn){
    let row = locals[cdt][cdn]
    if(row.custom_using_date_expire){
        frappe.call({
            method: 'pharmacy.controllers.stock_entry.get_expiry_date_qty',
            args:{
                item_code: row.item_code,
                warehouse: row.s_warehouse,
                expiry_date: row.item_expiry_date,
                uom: row.uom
            },
            callback:(r)=>{
                frappe.model.set_value(cdt,cdn, 'custom_expiry_date_qty', r.message)
            }
        })
    }
}

function set_expiry_date(frm,cdt,cdn){
    let row = locals[cdt][cdn]
    if(frm.doc.stock_entry_type == 'Material Transfer' && row.item_code && row.s_warehouse){
        frappe.call({
            method: 'pharmacy.controllers.stock_entry.get_expiry_date',
            args:{
                item_code: row.item_code,
                warehouse: row.s_warehouse
            },
            callback:(r)=>{
                frappe.model.set_value(cdt,cdn, 'item_expiry_date', r.message)
            }
        })
    }
}