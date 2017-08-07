# -*- coding: utf-8 -*-
from openerp.osv import osv, fields, expression
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)

class product_ul(osv.osv):
    _name = "product.ul"
    _inherit = "product.ul"
    _columns = {
        'type' : fields.selection([('unit','Unit'),('pack','Pack'),('box', 'Box'), ('pallet', 'Pallet')], 'Type', required=True),
    }
    _defaults = {
        'type': 'box',
    }
	
	
class stock_package(osv.osv):
    _name = "stock.quant.package"
    _inherit = "stock.quant.package"
	
    _columns = {
        'picking_id' : fields.many2one('stock.picking', 'Picking ID', ),	
    }	
	
class stock_picking(osv.osv):
    _name = "stock.picking"
    _inherit = ['stock.picking']	
	    
    
    _columns = {
        #'salesorder_id': fields.function(_get_saleorder_id, type="many2one", relation="sale.order", string="SaleOrder",fnct_search=_search_saleorder_id),		
        'packages_ids':fields.one2many('stock.quant.package', 'picking_id', string='Related Packages'),	
        'is_checked': fields.boolean('Final Check',default=False),	
        }		

	
    """	
    def show_so_delivery(self, cr, uid, ids, context=None):		

        picks = []	
        act_obj = self.pool.get('ir.actions.act_window')
        statement = "select id from stock_picking where group_id in (select procurement_group_id from sale_order where user_id=%d)"  % uid		
        cr.execute(statement)
		
        for i in cr.fetchall():
            picks.append(i[0])	
			
        result = act_obj.read(cr, uid, [483], context=context)[0]
        if ids == 0:		
            result['domain'] = "[ '&', ('state','not in',['done','draft','cancel']), ('id','in',[" + ','.join(map(str, picks)) + "])]"	
        elif  ids == 1:
            result['domain'] = "[ '&', ('state','=','done'), ('id','in',[" + ','.join(map(str, picks)) + "])]"			
		
        return result	"""	
		
		
    """		
    def emily_check(self, cr, uid, ids, context=None ):
	
        for pick in self.browse(cr, uid, ids, context=context):

            if pick.state != 'done' :
                pick.is_checked = False			
                continue
				
            if pick.is_checked == True:
                pick.is_checked = False	
            else:
                pick.is_checked = True
				
        return  """