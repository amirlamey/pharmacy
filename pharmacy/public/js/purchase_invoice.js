



frappe.provide("erpnext.accounts");

erpnext.accounts.PurchaseInvoice = class PurchaseInvoice extends erpnext.accounts.PurchaseInvoice {

    async item_code(doc, cdt, cdn) {
        await super.item_code(doc, cdt, cdn);
        this.get_last_purchase_rate(doc, cdt, cdn);
    }

    get_last_purchase_rate(doc, cdt, cdn) {
        let row = locals[cdt][cdn] ;
        if(row.item_code){
            frappe.db.get_value("Item Price",{'selling': 1,'item_code':row.item_code},'price_list_rate').then(r=>{
                frappe.model.set_value(cdt,cdn,'selling_price_list_rate',r.message.price_list_rate)
                frappe.model.set_value(cdt,cdn,'rate',row.selling_price_list_rate - (row.selling_price_list_rate * row.selling_price_discount )/100)
            })
            frappe.call({
                method: "pharmacy.controllers.purchase_invoice_item.pi_validate",
                args: {
                    item_code: row.item_code,
                    supplier: frm.doc.supplier
                },
                callback: function(r) {
                    if(r.message){                        
                        frappe.model.set_value(cdt,cdn,'custom_last_purchase_rate',r.message)
                        frappe.model.set_value(cdt,cdn,'rate',r.message)
                    }
                }
            })
        }
        else{            
            frappe.model.set_value(cdt,cdn,'custom_last_purchase_rate',0)
        }
        
    }

}

extend_cscript(cur_frm.cscript, new erpnext.accounts.PurchaseInvoice({ frm: cur_frm }));

frappe.ui.form.on('Purchase Invoice', {
	before_save(frm) {
		if(frm.doc.items){
            frm.doc.items.forEach(item => {
                if(item.item_code && item.selling_price_list_rate && item.selling_price_discount){
                    item.rate= item.selling_price_list_rate - ((item.selling_price_list_rate * item.selling_price_discount )/100)
                    frm.refresh_fields()
                }
            });
        }
	},
    setup(frm) {
        frm.set_query('uom','items', function(doc, cdt, cdn) {
            let row = locals[cdt][cdn];
            return {
                query: "pharmacy.controllers.purchase_invoice_item.get_item_uom",
                filters: {
                    'item_code': row.item_code
                }
            }
        })
    }
})


frappe.ui.form.on('Purchase Invoice Item', {
	// item_code(frm,cdt,cdn) {
    //     let row = locals[cdt][cdn]
    //     if(row.item_code){
    //         frappe.db.get_value("Item Price",{'selling': 1,'item_code':row.item_code},'price_list_rate').then(r=>{
    //             frappe.model.set_value(cdt,cdn,'selling_price_list_rate',r.message.price_list_rate)
    //             frappe.model.set_value(cdt,cdn,'rate',row.selling_price_list_rate - (row.selling_price_list_rate * row.selling_price_discount )/100)
    //         })
    //         frappe.call({
    //             method: "pharmacy.controllers.purchase_invoice_item.pi_validate",
    //             args: {
    //                 item_code: row.item_code,
    //                 supplier: frm.doc.supplier
    //             },
    //             callback: function(r) {
    //                 console.log(r)
    //                 if(r.message){                        
    //                     frappe.model.set_value(cdt,cdn,'custom_last_purchase_rate',r.message)
    //                     frappe.model.set_value(cdt,cdn,'rate',r.message)
    //                 }
    //             }
    //         })
    //     }
    //     else{            
    //         frappe.model.set_value(cdt,cdn,'custom_last_purchase_rate',0)
    //     }
        // else{
        //     row.selling_price_list_rate = 0
        //     row.selling_price_discount = 0
        //     frm.refresh_fields();
        // }
	// },
    
    selling_price_list_rate(frm,cdt,cdn) {
        let row = locals[cdt][cdn]
        if(row.selling_price_discount!=0){
            if(row.selling_price_list_rate){
                frappe.model.set_value(cdt,cdn,'rate',row.selling_price_list_rate - (row.selling_price_list_rate * row.selling_price_discount )/100)
                
            }
        }
        else{
            if(row.selling_price_list_rate){
                frappe.model.set_value(cdt,cdn,'rate',row.selling_price_list_rate )
            }
        }

    },
    selling_price_discount(frm,cdt,cdn) {
        let row = locals[cdt][cdn]
        if(row.selling_price_discount!=0){
            if(row.selling_price_list_rate){
                frappe.model.set_value(cdt,cdn,'rate',row.selling_price_list_rate - (row.selling_price_list_rate * row.selling_price_discount )/100)
                
            }
        }
        else{
            if(row.selling_price_list_rate){
                frappe.model.set_value(cdt,cdn,'rate',row.selling_price_list_rate )
            }
        }
    },
    
})
