frappe.ui.form.on('Purchase Receipt', {
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
    // refresh(frm){
    //     if(frm.doc.items&&frm.doc.docstatus==1){
    //         frm.doc.items.forEach(item => {
    //             if(item.batch_no){
    //                 console.log(item.batch_no)
    //                frappe.db.set_value("Batch",item.batch_no,'expiry_date',item.expiry_date)
    //             }
    //             frm.refresh_fields()
    //         });
    //     }
    // },
})
