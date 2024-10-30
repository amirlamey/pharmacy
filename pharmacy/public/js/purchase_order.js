frappe.ui.form.on('Purchase Order', {
	before_save(frm) {
		if(frm.doc.items){
            frm.doc.items.forEach(item => {
                if(item.item_code && item.selling_price_list_rate && item.selling_price_discount){
                    item.rate= item.selling_price_list_rate - ((item.selling_price_list_rate * item.selling_price_discount )/100)
                    frm.refresh_fields()
                }
            });
        }
	}
})

frappe.ui.form.on('Purchase Order Item', {
	item_code(frm,cdt,cdn) {
        let row = locals[cdt][cdn]
        if(row.item_code){
            frappe.db.get_value("Item Price",{'selling': 1,'item_code':row.item_code},'price_list_rate').then(r=>{
                frappe.model.set_value(cdt,cdn,'selling_price_list_rate',r.message.price_list_rate)
                frappe.model.set_value(cdt,cdn,'rate',row.selling_price_list_rate - (row.selling_price_list_rate * row.selling_price_discount )/100)
            })
        }
        // else{
        //     row.selling_price_list_rate = 0
        //     row.selling_price_discount = 0
        //     frm.refresh_fields();
        // }
	},
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