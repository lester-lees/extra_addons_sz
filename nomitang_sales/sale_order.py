# -*- coding: utf-8 -*-
# request.csrf_token()
from openerp.osv import osv, fields
#from openerp import SUPERUSER_ID
#from openerp.addons.web.http import request

class sale_order(osv.Model):
    _inherit = "sale.order"
	
    _columns = {
        'country_id': fields.related('partner_id', 'country_id', type='many2one', relation='res.country', string='Country'),		
    }		
