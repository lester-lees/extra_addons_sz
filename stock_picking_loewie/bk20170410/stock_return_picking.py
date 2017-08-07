# -*- coding: utf-8 -*-
from openerp.osv import osv, fields
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)

class stock_return_picking(osv.osv_memory):
    _inherit = 'stock.return.picking'

    def _create_returns(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        record_id = context and context.get('active_id', False) or False
        move_obj = self.pool.get('stock.move')
        pick_obj = self.pool.get('stock.picking')
        uom_obj = self.pool.get('product.uom')
        data_obj = self.pool.get('stock.return.picking.line')
        pick = pick_obj.browse(cr, uid, record_id, context=context)
        data = self.read(cr, uid, ids[0], context=context)
        returned_lines = 0

        # Cancel assignment of existing chained assigned moves
        moves_to_unreserve = []
        for move in pick.move_lines:
            to_check_moves = [move.move_dest_id] if move.move_dest_id.id else []
            while to_check_moves:
                current_move = to_check_moves.pop()
                if current_move.state not in ('done', 'cancel') and current_move.reserved_quant_ids:
                    moves_to_unreserve.append(current_move.id)
                split_move_ids = move_obj.search(cr, uid, [('split_from', '=', current_move.id)], context=context)
                if split_move_ids:
                    to_check_moves += move_obj.browse(cr, uid, split_move_ids, context=context)

        if moves_to_unreserve:
            move_obj.do_unreserve(cr, uid, moves_to_unreserve, context=context)
            #break the link between moves in order to be able to fix them later if needed
            move_obj.write(cr, uid, moves_to_unreserve, {'move_orig_ids': False}, context=context)
        #reverse_pick = pick.reverse_pick and pick.reverse_pick.id or 0
        #if 	reverse_pick : 
        #    reverse_pick = pick_obj.search(cr,uid,[('id','=',reverse_pick)],context=context)
        #    if reverse_pick :			
        #        raise osv.except_osv(_(u'警告 !'), _(u"您已经创建了一张反向转移仓库单."))
        #        return False
            #else:
            #    pick.reverse_pick = False	
				
        #Create new picking for returned products
        pick_type = pick.picking_type_id.return_picking_type_id and pick.picking_type_id.return_picking_type_id or pick.picking_type_id
        pick_type_code = pick_type.code
        pick_type_id = pick_type.id
	
        new_picking = pick_obj.copy(cr, uid, pick.id, {
            'move_lines': [],
            'picking_type_id': pick_type_id,
            'state': 'draft',
            'origin': pick.name,
            'invoice_state': '2binvoiced',			
            'source_pick': pick.id, # add by jimmy 20160707-0954			
        }, context=context)
 		
        #pick.reverse_pick = new_picking	 # add by jimmy 20160712-0610
		
        for data_get in data_obj.browse(cr, uid, data['product_return_moves'], context=context):
            move = data_get.move_id
            if not move:
                raise osv.except_osv(_('Warning !'), _("You have manually created product lines, please delete them to proceed"))
            new_qty = data_get.quantity
			
            loc_src = move.location_dest_id.id
            loc_dest = move.location_id.id			
			
            if move.handle_method.name and move.handle_method.name.find(u'换新')>=0 and pick_type_code == 'outgoing' :
                loc_src = 12			
			
            if new_qty:
                returned_lines += 1
                move_obj.copy(cr, uid, move.id, {
                    'product_id': data_get.product_id.id,
                    'product_uom_qty': new_qty,
                    'product_uos_qty': uom_obj._compute_qty(cr, uid, move.product_uom.id, new_qty, move.product_uos.id),
                    'picking_id': new_picking,
                    'state': 'draft',
                    'location_id': loc_src,
                    'location_dest_id': loc_dest,
                    #'origin_returned_move_id': move.id,
                    'procure_method': 'make_to_stock',
                    'restrict_lot_id': data_get.lot_id.id,
                })

        if not returned_lines:
            raise osv.except_osv(_('Warning!'), _("Please specify at least one non-zero quantity."))

        pick_obj.action_confirm(cr, uid, [new_picking], context=context)
        pick_obj.action_assign(cr, uid, [new_picking], context)
        return new_picking, pick_type_id