# -*- coding: utf-8 -*-

from openerp.osv import fields
from openerp.osv import osv

class res_company(osv.osv):
    _inherit = 'res.company'
    
    def _default_company(self, cr, uid, context=None):
        company_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
        if not company_id:
            raise osv.except_osv(_('Error!'), _('There is no default company for the current user!'))
        return company_id
    
    _columns = {
        'to_affiliate_comm_percent': fields.float('Affiliate Commission Percentage'),
        'to_affiliate_cookie_age': fields.integer('Affiliate Cookie Lifetime'),
        'to_affiliate_payout': fields.float('Minimum Commission Payout'),
        'to_com_product_id': fields.many2one('product.product', 'Commission Product', domain=[('type','=','service')], help="The standard Odoo product object for accounting integration purpose"),
        'to_affcode_company': fields.many2one('res.company', 'Default Affiliate Company'),
        'aff_allowed': fields.boolean('Affiliate Allowed', help="Enable this option will allow clients to select this company when joining affiliate program"),
    }
    
    _defaults = {
         'to_affiliate_comm_percent': 10,
         'to_affiliate_cookie_age': 864000,
         'to_affiliate_payout': 1000000,
         'to_affcode_company': _default_company,
         'aff_allowed': True
    }
    
    def _update_affiliate_commission_product_default(self, cr, uid, ids=None, context=None):
        company_ids = self.search(cr, uid, [], context=context)
        md = self.pool.get('ir.model.data')
        dummy, res_id = md.get_object_reference(cr, uid, 'to_affiliate_manager', 'to_product_product_aff_commission')
        check_right = self.pool.get('product.product').search(cr, uid, [('id', '=', res_id)], context=context)
        if check_right:
            self.write(cr, uid, company_ids, {'to_com_product_id': res_id}, context=context)
        
