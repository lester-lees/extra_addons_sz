# -*- coding: utf-8 -*-
import logging
from openerp import api, fields, models, _
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)

class product_template(models.Model):
    _inherit = 'product.template'
	
    bundle_gifts = fields.Many2many('product.product', string="Gifts") 	
	
	

class sale_order(osv.Model):
    _inherit = "sale.order"	
	
    def _cart_update(self, cr, uid, ids, product_id=None, line_id=None, add_qty=0, set_qty=0, context=None, **kwargs):
        """ Add or set product quantity, add_qty can be negative """
        sol = self.pool.get('sale.order.line')

        quantity = 0
        for so in self.browse(cr, uid, ids, context=context):
            if so.state != 'draft':
                request.session['sale_order_id'] = None
                raise UserError(_('It is forbidden to modify a sale order which is not in draft status'))
            if line_id is not False:
                line_ids = so._cart_find_product_line(product_id, line_id, context=context, **kwargs)
                if line_ids:
                    line_id = line_ids[0]

            # Create line if no line with product_id can be located
            if not line_id:
                values = self._website_product_id_change(cr, uid, ids, so.id, product_id, qty=1, context=context)
                line_id = sol.create(cr, SUPERUSER_ID, values, context=context)
                sol._compute_tax_id(cr, SUPERUSER_ID, [line_id], context=context)
                if add_qty:
                    add_qty -= 1						
					
            # compute new quantity
            if set_qty:
                quantity = set_qty
            elif add_qty is not None:
                quantity = sol.browse(cr, SUPERUSER_ID, line_id, context=context).product_uom_qty + (add_qty or 0)

            # Remove zero of negative lines
            if quantity <= 0:
                sol.unlink(cr, SUPERUSER_ID, [line_id], context=context)
                continue				
            else:
                # update line
                values = self._website_product_id_change(cr, uid, ids, so.id, product_id, qty=quantity, context=context)
                sol.write(cr, SUPERUSER_ID, [line_id], values, context=context)

            line_obj = sol.browse(cr,SUPERUSER_ID,[line_id],context=context)					
            gifts_ids = [ p.id for p in line_obj.product_id.accessory_product_ids ]	
            if gifts_ids :
                exist_ids = sol.search(cr,1, [('order_id','=', so.id),('product_id','=',gift_id),('price_unit','=',0)], context=context )
                if 	exist_ids :
                    gift = sol.browse(cr, 1, [exist_ids[0]], context=context)
                    gift.product_uom_qty = quantity
                else: 
                    vals = self._website_product_id_change(cr, uid, ids, so.id, exist_ids[0], qty=quantity, context=context)
                    gift_id = sol.create(cr, SUPERUSER_ID, values, context=context)
                    sol._compute_tax_id(cr, SUPERUSER_ID, [gift_id], context=context)				

        return {'line_id': line_id, 'quantity': quantity}	