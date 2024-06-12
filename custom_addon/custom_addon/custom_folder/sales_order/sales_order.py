import frappe
from frappe import _
from frappe.utils import add_days, nowdate

def on_submit(doc, method):
    if doc.doctype == "Sales Order":  # Ensure the document type is Sales Order
        prepare_purchase_order(doc)

def on_cancel(doc, method):
    pass

def prepare_purchase_order(doc):
    item_wh_stock = get_available_stock(doc)
    supplier_wise_items = frappe._dict()
    for item in doc.items:
        available_qty = item_wh_stock.get((item.item_code, item.warehouse), 0)
        if item.qty > available_qty:
            qty = item.qty - available_qty
            default_supplier = get_default_supplier(item.item_code, doc.company)
            supplier_wise_items.setdefault(default_supplier, []).append({
                "item_code": item.item_code,
                "item_name": item.item_name,
                "description": item.description,
                "item_group": item.item_group,
                "qty": qty,
                "warehouse": item.warehouse,
                "uom": item.uom,
                "stock_uom": item.stock_uom,
                "conversion_factor": 1.0,
                "sales_order": doc.name,
                "sales_order_item": item.name,
                "schedule_date": add_days(nowdate(), 1)
            })

    if supplier_wise_items:
        make_purchase_order(doc, supplier_wise_items)

def make_purchase_order(doc, supplier_wise_items):
    for supplier, items in supplier_wise_items.items():  # Corrected syntax
        po_doc = frappe.new_doc("Purchase Order")
        po_doc.supplier = supplier
        po_doc.company = doc.company
        po_doc.currency = doc.currency
        po_doc.set("items", [])

        for item in items:
            po_doc.append("items", item)

        po_doc.save(ignore_permissions=True)
        frappe.msgprint(_("Purchase Order {0} Created").format(po_doc.name))

def get_default_supplier(item_code, company):
    return frappe.get_cached_value("Item Default", {
        "parent": item_code, "company": company
    }, "default_supplier")

def get_available_stock(doc):
    item_wh_stock = {}
    bin_data = frappe.get_all("Bin", fields=["actual_qty", "item_code", "warehouse"], filters={
        "item_code": ["in", [item.item_code for item in doc.items]],  # Corrected filter syntax
        "warehouse": ["in", [item.warehouse for item in doc.items]]   # Corrected filter syntax
    })

    for d in bin_data:
        if d.actual_qty > 0:  # Ensure only positive stock quantities are considered
            item_wh_stock[(d.item_code, d.warehouse)] = d.actual_qty
    return item_wh_stock
