# -*- coding: utf-8 -*-
from openerp.osv import osv, fields
from openerp.tools.translate import _

class account_journal(osv.osv):
    _name = 'account.journal'
    _inherit = 'account.journal'    
    _columns = {
            'have_partner': fields.boolean('Require Partner'),
            'account_transit': fields.many2one('account.account','Account Transit',help="Account used to make money transfers between bank and cash journals"),
        }
    _defaults = {
            'have_partner' : False,
        }


class account_invoice(osv.osv):
    _inherit = 'account.invoice'
	
    def get_price_from_priclist(self, cr, uid, ids, context=None):
        #pricelist_item_obj = self.pool.get('product.pricelist.item')
        pricelist_id = self.pool.get('product.pricelist').search(cr, uid,  [('name', '=', 'Wholesale_CNY')], context=context)[0]
        invoice = self.browse(cr, uid, ids, context=context)[0]		
        for line in invoice.invoice_line:	
		
            if line.price_unit != 0 : continue		
            cr.execute("select price_surcharge from product_pricelist_item where product_id = %d and price_version_id = ( select id from product_pricelist_version where pricelist_id=%d and active=True limit 1)" % (line.product_id.id,pricelist_id) )
		
            for res in cr.fetchall():
                line.price_unit = res[0]
				
        return True
	
class account_voucher(osv.osv):
    _name = 'account.voucher'
    _inherit = 'account.voucher'    
    _columns = {
            'transfer_id': fields.many2one('account.transfer','Money Transfer', readonly=True,
                                           states={'draft':[('readonly',False)]}, ondelete="cascade"),
            'type':fields.selection([
                                 ('sale','Sale'),
                                 ('purchase','Purchase'),
                                 ('payment','Payment'),
                                 ('receipt','Receipt'),
                                 ('transfer','Transfer'),
                                 ],'Default Type', readonly=True, states={'draft':[('readonly',False)]}),
        }

    _document_type = {
        'sale': 'Sales Receipt',
        'purchase': 'Purchase Receipt',
        'payment': 'Supplier Payment',
        'receipt': 'Customer Payment',
        'transfer': 'Money Transfer',
        False: 'Payment',
    }

    def first_move_line_get(self, cr, uid, voucher_id, move_id, company_currency, current_currency, context=None):
        if context is None:
            context = {}
        res = super(account_voucher,self).first_move_line_get(cr, uid, voucher_id, move_id, company_currency, current_currency, context=context)
        voucher = self.pool.get('account.voucher').browse(cr,uid,voucher_id,context)
        if voucher.type == 'transfer':
            #import pdb; pdb.set_trace()
            if voucher.transfer_id.src_journal_id.id == voucher.journal_id.id:
                res['credit'] = voucher.paid_amount_in_company_currency
            else:
                res['debit'] = voucher.paid_amount_in_company_currency
            if res['debit'] < 0: res['credit'] = -res['debit']; res['debit'] = 0.0
            if res['credit'] < 0: res['debit'] = -res['credit']; res['credit'] = 0.0
            sign = res['debit'] - res['credit'] < 0 and -1 or 1
            res['currency_id'] = company_currency <> current_currency and current_currency or False
            res['amount_currency'] = company_currency <> current_currency and sign * voucher.amount or 0.0
        return res
