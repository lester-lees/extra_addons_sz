# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import datetime
import csv
import time
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
import cStringIO
import base64
from openerp import api
from openerp.tools.float_utils import float_compare, float_round
from openerp.tools.translate import _

import logging

_logger = logging.getLogger(__name__)

class stock_picking_type(osv.osv):
    _inherit = "stock.picking.type"
    _columns = {
        'display': fields.boolean(string="Display?"),	
    }
	
class stock_pack_operation(osv.osv):
    _inherit = "stock.pack.operation"
	
    def split_quantities(self, cr, uid, ids, context=None ):	
	
        for operation in self.pool.get('stock.pack.operation').browse(cr, uid, ids, context=context):
			
            tmp_qty = operation.product_qty
            qty = int(tmp_qty/2)			
            if tmp_qty > 1 :
		
                operation.product_qty = qty
                new_id = operation.copy( default = {'product_qty':int(tmp_qty - qty)} )	
					
class stock_quant(osv.osv):

    def _get_so_id(self, cr, uid, ids, field_names=None, arg=False, context=None):    
        res = {}       
        reserv_objs = self.pool.get('stock.reservation')

        for quant in self.browse(cr, uid, ids, context=context):
            res[quant.id] = quant.reservation_id.picking_id.sale_id.name
            if not quant.reservation_id.picking_id.sale_id:
                #_logger.info("Jimmy:%d" % quant.reservation_id.id)				
                reserv_id = reserv_objs.search(cr, uid,  [('move_id', '=', quant.reservation_id.id)], context=context)
                if not reserv_id :	
                    continue				
                reserv = reserv_objs.browse(cr, 1, [reserv_id[0]], context=context)				
                res[quant.id] = reserv.sale_line_id.order_id.name
                #_logger.info(reserv.sale_line_id.order_id.name)				
			
        return res	

    def _get_so_user_id(self, cr, uid, ids, field_names=None, arg=False, context=None):    
        res = {}        
        reserv_objs = self.pool.get('stock.reservation')
		
        for quant in self.browse(cr, uid, ids, context=context):
            res[quant.id] = quant.reservation_id.picking_id.sale_id.user_id.login
            if not quant.reservation_id.picking_id.sale_id:
                #_logger.info("Jimmy:%d" % quant.reservation_id.id)				
                reserv_id = reserv_objs.search(cr, uid,  [('move_id', '=', quant.reservation_id.id)], context=context)
                if not reserv_id :	
                    continue				
                reserv = reserv_objs.browse(cr, 1, [reserv_id[0]], context=context)				
                res[quant.id] = reserv.sale_line_id.order_id.user_id.login
                #_logger.info(reserv.sale_line_id.order_id.user_id.login)				
        return res			
		
    _inherit = "stock.quant"
    _columns = {
        'so_id': fields.function(_get_so_id, type='char',string="Sale Order"),
        'so_user_id': fields.function(_get_so_user_id, type='char',string="Sales Person"), 	#fields.char("Sales Person"),	
    }	

class stock_quant_package_ext(osv.osv):
    _inherit = "stock.quant.package"
    _columns = {
        'dimension': fields.char('Dimension', size=16),
        'package_weight': fields.float('Weight'),
    }

class loewie_description(osv.osv):
    _name = "loewie.description"
	
    _columns = {	
        'name': fields.char(string='Problem', help=u'问题描述'),		
    }	
	
    """
    def init(self, cr):
	
        reasons = [u'短日期', u'充电器坏',u'震动时间短',u'日期模糊', u'漏液', u'震动弱',u'包装破损', u'有噪音', u'不充电', u'外观不良',u'不震动',u'震动端背后有洞']

        desc_obj = self.pool.get('loewie.description')	
		
        for x in reasons:
            ids = desc_obj.search(cr, 1,  [('name', '=', x)], context={})		
            if len(ids)> 0 : desc_obj.unlink(cr,1,ids)			
            desc_obj.create(cr,1,{'name':x})		
    """        
	
class loewie_tackle(osv.osv):
    _name = "loewie.tackle"
	
    _columns = {	
        'name': fields.char('处理方式'),		
    }
	
    """
    def init(self, cr):
	
        reasons = [u'补款换新(现付)', u'补款换新(到付)',u'原物返还(到付)',u'原物返还(现付)', u'原物返还(包邮)', u'产品换新(包邮)']

        desc_obj = self.pool.get('loewie.tackle')	
		
        for x in reasons:
            ids = desc_obj.search(cr, 1,  [('name', '=', x)], context={})		
            if len(ids)> 0 : desc_obj.unlink(cr,1,ids)			
            desc_obj.create(cr,1,{'name':x})	 
    """
				
class stock_move(osv.osv):
    _inherit = "stock.move"
	
    def _get_cost(self, cr, uid, ids, field_names=None, arg=False, context=None):   
        res = {}  	
        for move in self.browse(cr, uid, ids, context=context):	
            if move.purchase_line_id:
                res[move.id] = move.purchase_line_id.price_unit
            else:
                res[move.id] = move.product_id.standard_price			
        return res		

    def _get_hksz_total(self, cr, uid, ids, field_names=None, arg=False, context=None):
        res = {}  	
        for move in self.browse(cr, uid, ids, context=context):
            res[move.id] = move.product_uom_qty * move.price_hk_sz_exchange

        return res		
		
    _columns = {
        'sale_line_loewie': fields.many2one('sale.order.line',string='Sale Line Loewie'),	
        'state_bk':fields.char('backup state'),	
        'cost': fields.function(_get_cost, type='float', string='Cost'),
        'price_hk_sz_exchange': fields.related('product_id','price_hk_sz_exchange',readonly=True, type='float',string='Exchange Price'),		
        'price_total_hksz': fields.function(_get_hksz_total , type='float', string='Price Total'),				
        'produce_bill_id':fields.integer('Produce Bill'),
        'is_checked':fields.boolean(string=u'选择行', default=False, copy=False),	
        'return_reason':fields.many2one("loewie.description",string=u'问题描述'),	
        'handle_method':fields.many2one("loewie.tackle",string=u'处理方式')	,
        'state': fields.selection([('draft', 'New'),
                                   ('cancel', 'Cancelled'),
                                   ('waiting', 'Waiting Another Move'),								   
                                   ('confirmed', 'Waiting Availability'),
                                   ('waiting_financial', 'Waiting Financial'),									   
                                   ('assigned', 'Available'),								   
                                   ('done', 'Done'),
                                   ], 'Status', readonly=True, select=True, copy=False,
                 help= "* New: When the stock move is created and not yet confirmed.\n"\
                       "* Waiting Another Move: This state can be seen when a move is waiting for another one, for example in a chained flow.\n"\
                       "* Waiting Availability: This state is reached when the procurement resolution is not straight forward. It may need the scheduler to run, a component to me manufactured...\n"\
                       "* Available: When products are reserved, it is set to \'Available\'.\n"\
                       "* Done: When the shipment is processed, the state is \'Done\'."),		
    }		
		
    def onchange_product_id(self, cr, uid, ids, prod_id=False, loc_id=False, loc_dest_id=False, partner_id=False):

        if not prod_id:
            return {}
        user = self.pool.get('res.users').browse(cr, uid, uid)
		
        lang = user and user.lang or False
        if partner_id:
            addr_rec = self.pool.get('res.partner').browse(cr, uid, partner_id)
            if addr_rec:
                lang = addr_rec and addr_rec.lang or False
        ctx = {'lang': lang}

        product = self.pool.get('product.product').browse(cr, uid, [prod_id], context=ctx)[0]
		
        uos_id = product.uos_id and product.uos_id.id or False		
		
        result = {
            'name': product.description_sale or '.',
            'product_uom': product.uom_id.id,
            'product_uos': uos_id,
            'product_uom_qty': 1.00,
            'product_uos_qty': self.pool.get('stock.move').onchange_quantity(cr, uid, ids, prod_id, 1.00, product.uom_id.id, uos_id)['value']['product_uos_qty'],
        }
        if loc_id:
            result['location_id'] = loc_id
        if loc_dest_id:
            result['location_dest_id'] = loc_dest_id
        return {'value': result}
	
    def onchange_handle_method(self, cr, uid, ids, prod_id=False, loc_id=False, loc_dest_id=False, hdl_method=False):
        result = {}	
        if hdl_method is None: return	
		
        move_obj = self.pool.get('stock.move').browse(cr, uid, ids, context={})
        handle_method = self.pool.get('loewie.tackle').browse(cr,uid,[hdl_method],context={})
        handle_name = handle_method.name		
		
        if len(move_obj)< 1: return
        move = move_obj[0] 		
        code = move.picking_id.picking_type_id.code
        #hdl_method = move.handle_method.name		
		
        if code == 'incoming' and handle_name.find(u'原物返还') >= 0  :
            result['location_dest_id'] = 20		# 待用仓

        if code == 'incoming' and handle_name.find(u'良品入库') >= 0 :
            result['location_dest_id'] = 12  # 12 = 成品仓

        if code == 'incoming' and handle_name.find(u'换新') >= 0 :
            result['location_dest_id'] = 18  #18 不良品仓			

        if code == 'outgoing' and handle_name.find(u'换新') >= 0 :
            result['location_id'] = 12	
            move.picking_id.invoice_state = '2binvoiced'
            move.invoice_state = '2binvoiced'			

        return {'value': result}
		

    def action_scrap(self, cr, uid, ids, quantity, location_id, restrict_lot_id=False, restrict_partner_id=False, context=None):
        """ Move the scrap/damaged product into scrap location
        @param cr: the database cursor
        @param uid: the user id
        @param ids: ids of stock move object to be scrapped
        @param quantity : specify scrap qty
        @param location_id : specify scrap location
        @param context: context arguments
        @return: Scraped lines
        """
        #quantity should be given in MOVE UOM
        if quantity <= 0:
            raise osv.except_osv(_('Warning!'), _('Please provide a positive quantity to scrap.'))
        res = []
        for move in self.browse(cr, uid, ids, context=context):	
            source_location = move.location_id                			
            if move.state == 'done':
                source_location = move.location_dest_id
            #Previously used to prevent scraping from virtual location but not necessary anymore
            #if source_location.usage != 'internal':
                #restrict to scrap from a virtual location because it's meaningless and it may introduce errors in stock ('creating' new products from nowhere)
                #raise osv.except_osv(_('Error!'), _('Forbidden operation: it is not allowed to scrap products from a virtual location.'))
            if quantity > move.product_qty : continue
			
            move_qty = move.product_qty
            uos_qty = quantity / move_qty * move.product_uos_qty

            pickint_type_code = move.picking_type_id.code or move.picking_id.picking_type_id.code	
            source_location = source_location.id
            dest_location = location_id				
            if pickint_type_code == 'outgoing':
                dest_location = move.location_dest_id.id
                source_location = location_id
			
            #_logger.info("Jimmy:%s" % pickint_type_code)				
            default_val = {
                'location_id': source_location,
                'product_uom_qty': quantity,
                'product_uos_qty': uos_qty,
                'state': move.state,
                'scrapped': False, #True,
                'location_dest_id': dest_location,
                'restrict_lot_id': restrict_lot_id,
                'restrict_partner_id': restrict_partner_id,
            }
            new_move = self.copy(cr, uid, move.id, default_val)
			
            actual_qty = move.product_uom_qty - quantity
            move.product_uos_qty = actual_qty
            move.product_uom_qty = actual_qty			
			
            res += [new_move]
            product_obj = self.pool.get('product.product')
            for product in product_obj.browse(cr, uid, [move.product_id.id], context=context):
                if move.picking_id:
                    uom = product.uom_id.name if product.uom_id else ''
                    message = _("%s %s %s has been <b>moved to</b> scrap.") % (quantity, uom, product.name)
                    move.picking_id.message_post(body=message)

        #self.action_done(cr, uid, res, context=context)
        return res	


    def action_assign(self, cr, uid, ids, context=None):
        context = context or {}
        quant_obj = self.pool.get("stock.quant")
        to_assign_moves = []
        main_domain = {}
        todo_moves = []
        operations = set()
        for move in self.browse(cr, uid, ids, context=context):
            if move.state not in ('confirmed', 'waiting', 'assigned', 'waiting_financial'):  #  
                continue
            if move.location_id.usage in ('supplier', 'inventory', 'production'):
                to_assign_moves.append(move.id)
                #in case the move is returned, we want to try to find quants before forcing the assignment
                if not move.origin_returned_move_id:
                    continue
            if move.product_id.type == 'consu':
                to_assign_moves.append(move.id)
                continue
            else:
                todo_moves.append(move)

                #we always keep the quants already assigned and try to find the remaining quantity on quants not assigned only
                main_domain[move.id] = [('reservation_id', '=', False), ('qty', '>', 0)]

                #if the move is preceeded, restrict the choice of quants in the ones moved previously in original move
                ancestors = self.find_move_ancestors(cr, uid, move, context=context)
                if move.state in ['waiting','waiting_financial'] and not ancestors:
                    #if the waiting move hasn't yet any ancestor (PO/MO not confirmed yet), don't find any quant available in stock
                    main_domain[move.id] += [('id', '=', False)]
                elif ancestors:
                    main_domain[move.id] += [('history_ids', 'in', ancestors)]

                #if the move is returned from another, restrict the choice of quants to the ones that follow the returned move
                if move.origin_returned_move_id and move.picking_id.picking_type_id.id != 19:
                    main_domain[move.id] += [('history_ids', 'in', move.origin_returned_move_id.id)]
                for link in move.linked_move_operation_ids:
                    operations.add(link.operation_id)
        # Check all ops and sort them: we want to process first the packages, then operations with lot then the rest
        operations = list(operations)
        operations.sort(key=lambda x: ((x.package_id and not x.product_id) and -4 or 0) + (x.package_id and -2 or 0) + (x.lot_id and -1 or 0))
        for ops in operations:
            #first try to find quants based on specific domains given by linked operations
            for record in ops.linked_move_operation_ids:
                move = record.move_id
                if move.id in main_domain:
                    domain = main_domain[move.id] + self.pool.get('stock.move.operation.link').get_specific_domain(cr, uid, record, context=context)
                    qty = record.qty
                    if qty:
                        quants = quant_obj.quants_get_prefered_domain(cr, uid, ops.location_id, move.product_id, qty, domain=domain, prefered_domain_list=[], restrict_lot_id=move.restrict_lot_id.id, restrict_partner_id=move.restrict_partner_id.id, context=context)
                        quant_obj.quants_reserve(cr, uid, quants, move, record, context=context)
        for move in todo_moves:
            if move.linked_move_operation_ids:
                continue
            #then if the move isn't totally assigned, try to find quants without any specific domain
            if move.state != 'assigned':
                qty_already_assigned = move.reserved_availability
                qty = move.product_qty - qty_already_assigned
                quants = quant_obj.quants_get_prefered_domain(cr, uid, move.location_id, move.product_id, qty, domain=main_domain[move.id], prefered_domain_list=[], restrict_lot_id=move.restrict_lot_id.id, restrict_partner_id=move.restrict_partner_id.id, context=context)
                quant_obj.quants_reserve(cr, uid, quants, move, context=context)			

        #force assignation of consumable products and incoming from supplier/inventory/production
        if to_assign_moves:
            self.force_assign(cr, uid, to_assign_moves, context=context)

	
class stock_picking(osv.osv):
    _inherit = "stock.picking"
    #_name = "stock.picking"

    def _get_purchase_order(self, cr, uid, ids, field_names, args, context=None):
        res = {}

        query = """SELECT m.picking_id, pol.order_id from stock_move m left join purchase_order_line pol on(pol.id=m.purchase_line_id) where m.picking_id in %s group by m.picking_id, pol.order_id"""
        cr.execute( query, (tuple(ids), ) )
        picks = cr.fetchall()
		
        for pick_id, po_id in picks:
            res[pick_id] = po_id
			
        return res	
	
    def _state_get(self, cr, uid, ids, field_name, arg, context=None):
        '''The state of a picking depends on the state of its related stock.move
            draft: the picking has no line or any one of the lines is draft
            done, draft, cancel: all lines are done / draft / cancel
            confirmed, waiting, assigned, partially_available depends on move_type (all at once or partial)
        '''
        res = {}
        for pick in self.browse(cr, uid, ids, context=context):
            if (not pick.move_lines) or any([x.state == 'draft' for x in pick.move_lines]):
                res[pick.id] = 'draft'
                continue
            if all([x.state == 'cancel' for x in pick.move_lines]):
                res[pick.id] = 'cancel'
                continue
            if all([x.state in ('cancel', 'done') for x in pick.move_lines]):
                res[pick.id] = 'done'
                continue

            order = {'confirmed': 0, 'waiting': 1, 'waiting_financial':2, 'assigned': 3}
            order_inv = {0: 'confirmed', 1: 'waiting', 2: 'waiting_financial', 3: 'assigned'}
            lst = [order[x.state] for x in pick.move_lines if x.state not in ('cancel', 'done')]
            if pick.move_type == 'one':
                res[pick.id] = order_inv[min(lst)]
            else:
                #we are in the case of partial delivery, so if all move are assigned, picking
                #should be assign too, else if one of the move is assigned, or partially available, picking should be
                #in partially available state, otherwise, picking is in waiting or confirmed state
                res[pick.id] = order_inv[max(lst)]
                if not all(x == 2 for x in lst):
                    if any(x == 2 for x in lst):
                        res[pick.id] = 'partially_available'
                    else:
                        #if all moves aren't assigned, check if we have one product partially available
                        for move in pick.move_lines:
                            if move.partially_available:
                                res[pick.id] = 'partially_available'
                                break
        return res
	
    def _get_pickings(self, cr, uid, ids, context=None):
        res = set()
        for move in self.browse(cr, uid, ids, context=context):
            if move.picking_id:
                res.add(move.picking_id.id)
        return list(res)  
	
    _columns = {
        'reconcile_saleorder': fields.many2one('sale.order', string=u'冲减销售单', copy=False),	
        #'reverse_pick': fields.many2one('stock.picking', 'Picks to', copy=False, readonly=True ),	# fields.one2many('stock.location', 'location_id', 'Contains'),	
        'reverse_pick': fields.one2many('stock.picking', 'source_pick', string='Pickings to'),			
        'source_pick': fields.many2one('stock.picking', 'Pick From', copy=False, readonly=True ),	
        'purchase_order': fields.function(_get_purchase_order, method=True, type='many2one', relation='purchase.order', string='Purchase Order'),	
        'upload_file':fields.binary('Upload & Download lines', copy=False),	
        'can_ship': fields.boolean(string="Inform shipping",default=False, copy=False),	
        #'check_all': fields.boolean(string="Check All",default=False),			
        'location_tmp': fields.many2one('stock.location', 'Warehouse Location'),
        'loc_id': fields.many2one('stock.location', 'Select Source'),		
        'loc_dest_id': fields.many2one('stock.location', 'Select Destination'),	
        'so_reference':fields.related('sale_id','client_order_ref',type='char',string='SO Reference', readonly=True),	
        'note_delivery': fields.related('sale_id','note_delivery',type='text', string=u'备注信息', readonly=True),
        'note_financial': fields.related('sale_id','note_financial',type='char', string=u'付款信息', readonly=True),			
        'so_note':fields.related('sale_id','note',type='text',string='Sales Note'),		
        'state': fields.function(_state_get, type="selection", copy=False,
            store={
                'stock.picking': (lambda self, cr, uid, ids, ctx: ids, ['move_type'], 20),
                'stock.move': (_get_pickings, ['state', 'picking_id', 'partially_available'], 20)},
            selection=[
                ('draft', 'Draft'),
                ('cancel', 'Cancelled'),
                ('waiting', 'Waiting Another Operation'),
                ('confirmed', 'Waiting Availability'),
                ('waiting_financial', u'等待财务审核'),					
                ('partially_available', 'Partially Available'),						
                ('assigned', 'Ready to Transfer'),				
                ('done', 'Transferred'),
                ], string='Status', readonly=True, select=True, track_visibility='onchange',
            help="""
                * Draft: not confirmed yet and will not be scheduled until confirmed\n
                * Waiting Another Operation: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows)\n
                * Waiting Availability: still waiting for the availability of products\n
                * Waiting Financial: still waiting for the Approvation of v\n				
                * Partially Available: some products are available and reserved\n
                * Ready to Transfer: products reserved, simply waiting for confirmation.\n
                * Transferred: has been processed, can't be modified or cancelled anymore\n
                * Cancelled: has been cancelled, can't be confirmed anymore"""
        ),		
    }

    def do_unreserve_specified_lines(self, cr, uid, ids, context=None):
	
        quant_obj = self.pool.get("stock.quant")

        picking = self.browse(cr, uid, ids[0], context=context)		
        for move in picking.move_lines:
		
            if not move.is_checked : continue	
			
            if move.state in ('done', 'cancel'):
                raise osv.except_osv(_('Operation Forbidden!'), _('Cannot unreserve a done move'))
				
            quant_obj.quants_unreserve(cr, uid, move, context=context)

            ancestors = []
            move2 = move
            while move2:
                ancestors += [x.id for x in move2.move_orig_ids]
                move2 = not move2.move_orig_ids and move2.split_from or False
			
            if ancestors:
                move.write({'state': 'waiting', 'is_checked': False})
            else:
                move.write({'state': 'confirmed', 'is_checked': False})
				
    # below three functions are for financial checking							
    def force_assign(self, cr, uid, ids, context=None):

        for pick in self.browse(cr, uid, ids, context=context):
            move_ids = [x.id for x in pick.move_lines if x.state in ['confirmed', 'waiting','waiting_financial']]
            self.pool.get('stock.move').force_assign(cr, uid, move_ids, context=context)
        #pack_operation might have changed and need to be recomputed
        self.write(cr, uid, ids, {'recompute_pack_op': True}, context=context)
        return True	
	
    def emily_known(self, cr, uid, ids, context=None):	
	
        for pick in self.pool.get('stock.picking').browse(cr, uid, ids, context=context):

            if pick.state == 'draft': self.action_confirm(cr, uid, [pick.id], context=context) 
            avail = False            			
            for x in pick.move_lines :
                if x.availability : 
                    avail = True
                    break					

            if not avail: return False
			
            for x in pick.move_lines :				
                x.state = x.state_bk				
				
            super(stock_picking,self).action_assign(cr,uid,[pick.id],context=context)				
		
        return True		
		
    def action_assign(self, cr, uid, ids, context=None):
        approved_list = ['linda','nola','emily','manager.mirror','lois','vivien','aileen','andy','jack','emma','sara' ]	
		
        user_obj = self.pool.get('res.users').browse(cr,uid,uid,context=context)
        is_hr_manager =  False		
        for obj in user_obj.groups_id:
            if obj.id == 55: is_hr_manager = True  # group_id of HR_Manager is 55
			
        #is_hr_manager = user_obj.sel_groups_5_54_55 == '55' or 0
        #statement = "select uid,gid from res_groups_users_rel where gid=55 and uid=%d" % uid
        #cr.execute(statement)
        		
        for pick in self.browse(cr, uid, ids, context=context):
		
            if pick.picking_type_id.code == 'incoming' :
                self.force_assign(cr,uid,[pick.id],context=context)	
                continue			
				
            # 应该在此判断用户是否属于 某个权限组，而不是 把用户名 硬编码进来	Human Resources --- sel_groups_5_54_55, HR_Manager:55	
            if is_hr_manager or pick.create_uid.login in approved_list or pick.picking_type_id.code != 'outgoing' or ( pick.sale_id and pick.backorder_id ): 
                super(stock_picking,self).action_assign(cr,uid,[pick.id],context=context)				
                continue				
			
            if pick.state == 'draft':
                self.action_confirm(cr, uid, [pick.id], context=context)

            avail = False            			
            for x in pick.move_lines :
                if x.availability : 
                    avail = True
                    break					
            if not avail: return False
				
            for x in pick.move_lines  :
                if x.state not in ('draft', 'cancel', 'done')	:		
                    x.state_bk = x.state
                    x.state = 'waiting_financial'				

        return True	
	
	
    def inform_warehouse_shipping(self, cr, uid, ids, context=None ):
	
        for pick in self.browse(cr, uid, ids, context=context):

            if not ( pick.state in ['partially_available','assigned','confirmed']) :				
                continue
				
            if pick.can_ship == True:
                pick.can_ship = False	
            else:
                pick.can_ship = True
				
        return
		
    def export_lines(self, cr, uid, ids, context=None ):
	
        this = self.browse(cr, uid, ids, context=context)[0]	
        buf = cStringIO.StringIO()
        writer = csv.writer(buf)		
		
        for line in this.move_lines:
            writer.writerow([line.product_id.name_template,line.product_uom_qty])		
			
        out = base64.encodestring(buf.getvalue())
        this.write({'upload_file':out})	
				
        return	

    def import_lines(self, cr, uid, ids, context=None ):
	
        this = self.browse(cr, uid, ids, context=context)[0]
        sol_obj = self.pool.get('stock.move')		
        buf = cStringIO.StringIO(base64.decodestring(this.upload_file))
        reader = csv.reader(buf)		
		
        for line in reader:  
            product_id = self.pool.get('product.product').search(cr, uid,  [('name_template', '=', line[0])], context=context)[0]
            if not product_id : continue			
            statement = "insert into stock_move(picking_id, picking_type_id, product_id, name, product_uom_qty, product_uom, invoice_state, date,location_id,location_dest_id,company_id,procure_method,date_expected,weight_uom_id) values(%d,%d,%d,'.',%s,1,'%s','%s',%d,%d,%d,'make_to_stock','%s',4)" % ( this.id, this.picking_type_id.id, product_id, line[1], this.invoice_state, datetime.datetime.now(),this.location_id.id, this.location_dest_id.id,this.company_id.id,datetime.datetime.now())			
            cr.execute(statement)			
        """		
        for line in this.move_lines:
            vals = sol_obj.product_id_change(
                cr, uid, line.id, this.pricelist_id.id,
                product=line.product_id.id, qty=line.product_uom_qty,
                uom=line.product_uom.id, qty_uos=line.product_uos_qty,
                uos=line.product_uos.id, name=line.name,
                partner_id=this.partner_id.id,
                lang=False, update_tax=True, date_order=this.date_order,
                packaging=False, fiscal_position=False, flag=False, context=context)
            sol_obj.write(cr, uid, line.id, vals['value'], context=context)    
        """				
        return			
		
    def change_location(self, cr, uid, ids, context=None ):
	
        location_id = self.pool.get('stock.location').search(cr, uid,  [('usage', '=', 'customer')], context=context)[0]	
        for pick in self.browse(cr, uid, ids, context=context):
  
            group_id = 1  
            for line in pick.move_lines:
                if line.group_id is not None:
                    group_id = line.group_id
                    break					
					
            for line in pick.move_lines:
                line.location_id = location_id
                #line.location_dest_id = pick.loc_dest_id
                line.invoice_state = '2binvoiced'	#2binvoiced			
                line.group_id = group_id					

        return		

    def set_to_draft(self, cr, uid, ids, context=None ):	
	
        for pick in self.browse(cr, uid, ids, context=context):
            if pick.state != 'cancel' : continue		
            for line in pick.move_lines:
                line.write({'state': 'draft'}, context=context)			
        	
    #'RMA' marked products' Description in sales order, will delivery from standby location.		
    def set_from_standby_location(self, cr, uid, ids, context=None ):
	
        for pick in self.browse(cr, uid, ids, context=context):
            for line in pick.move_lines:
                if line.name and line.name.find('RMA')>=0:			
                    line.location_id = 20 # Standby Location ID = 20

        return		
		
    def set_location(self, cr, uid, ids, context=None ):	
		
        for pick in self.browse(cr, uid, ids, context=context):
            loc_dest_id = pick.loc_dest_id.id
            loc_id = pick.loc_id.id	
            if not loc_id and not loc_dest_id : return
		
            val = {}
            if loc_dest_id : val.update({'location_dest_id':loc_dest_id}) 
            if loc_id : val.update({'location_id':loc_id}) 	
            pick.move_lines.write(val)
			
            #pick.picking_type_id = 1	# Stock Reciepts ID = 1
            #for line in pick.move_lines:
                #if pick.picking_type_id.code =='incoming' and line.is_checked : line.location_dest_id = dest_id
                #if pick.picking_type_id.code =='outgoing' and line.is_checked : line.location_id = loc_id
                #if line.is_checked : line.is_checked = False
				
        return   

    def set_checked(self, cr, uid, ids, context=None ):	
		
        for pick in self.browse(cr, uid, ids, context=context):	
		
            for line in pick.move_lines:
                if not pick.location_tmp : 
                    line.is_checked = True
                    continue					
				
                if pick.picking_type_id.code =='incoming' and line.location_dest_id.id == pick.location_tmp.id: 
                    line.is_checked = True
                    continue					
					
                if pick.picking_type_id.code =='outgoing' and  line.location_id.id == pick.location_tmp.id : 
                    line.is_checked = True
                    continue			

        return  

    def set_unchecked(self, cr, uid, ids, context=None ):	
		
        for pick in self.browse(cr, uid, ids, context=context):	
		
            for line in pick.move_lines:
                if not pick.location_tmp : 
                    line.is_checked = False
                    continue					
				
                if pick.picking_type_id.code =='incoming' and line.location_dest_id.id == pick.location_tmp.id: 
                    line.is_checked = False
                    continue					
					
                if pick.picking_type_id.code =='outgoing' and  line.location_id.id == pick.location_tmp.id : 
                    line.is_checked = False
                    continue			

        return   		
	    
    def create(self, cr, user, vals, context=None):
        context = context or {}		
        id = super(stock_picking, self).create(cr, user, vals, context)	
        self.message_subscribe_users(cr, user, [id], user_ids=[29,30], context=context)	 #29,30,36  adam,ben,jojo  悦汇
        		
        return id

    def add_followers(self, cr, uid, vals, context=None):	
        return self.message_subscribe_users(cr, uid, vals['ids'], user_ids=vals['user_ids'], context=context)    		
				
    def create_negative_so(self, cr, uid, ids, context=None ):		
        sale_order_obj = self.pool.get('sale.order')
        sale_order_line_obj = self.pool.get('sale.order.line')
		
        this = self.browse(cr, uid, ids, context=context)[0]		

        vals = {
            'client_order_ref': u'冲减销售单',		
            'picking_policy': 'direct',
            'order_policy': 'manual',			
            'company_id': this.company_id.id,
            'all_discounts': 0,
            'partner_id': this.partner_id.id,
            'pricelist_id': this.sale_id and this.sale_id.pricelist_id.id or 42,
            'warehouse_id': 3,
            'user_id': this.sale_id and this.sale_id.user_id.id or this.create_uid.id, 
            'state':'draft',
            'partner_invoice_id': this.sale_id and this.sale_id.partner_invoice_id.id or this.partner_id.id,
            'partner_shipping_id': this.sale_id and this.sale_id.partner_shipping_id.id or this.partner_id.id,		
            'date_order': datetime.datetime.now(),	
            'return_pick':ids[0],			
        }
			
        new_id = sale_order_obj.create(cr, uid, vals, context=context)
        sale_order = sale_order_obj.browse(cr, uid, new_id, context=context)
        sale_order_obj.onchange_partner_id(
            cr, uid, new_id, sale_order.partner_id.id, context=context)		
        sale_order_name = sale_order.name		
		
        for line in this.move_lines:
            saleline = 	line.procurement_id and line.procurement_id.sale_line_id or line.sale_line_loewie or False	
            discount = 	saleline and saleline.discount or 0	
            price_unit = saleline and saleline.price_unit or 0			
            order_line = {
                'order_id': new_id,				
                'product_uos_qty': -line.product_uom_qty,
                'product_id': line.product_id.id,
                'product_uom': line.product_uom.id,
                'price_unit': price_unit,
                'discount': discount,			
                'product_uom_qty': -line.product_uom_qty,
                'name': line.name or "-" , # line.name and line.express_id2 and line.name + "," + line.express_id2.name or 
                'delay': 7,	
                #'tax_id': [(4, 0, [7])],
            }	

            sale_order_line_obj.create(cr, uid, order_line)			
        """
        for line in sale_order.order_line:
            vals = sale_order_line_obj.product_id_change(
                cr, uid, [line.id], sale_order.pricelist_id.id,
                product=line.product_id.id, qty=line.product_uom_qty,
                uom=line.product_uom.id, qty_uos=line.product_uos_qty,
                uos=line.product_uos.id, name=line.name,
                partner_id=sale_order.partner_id.id,
                lang=False, update_tax=True, date_order=sale_order.date_order,
                packaging=False, fiscal_position=False, flag=False, context=context)
            sale_order_line_obj.write(cr, uid, line.id, vals['value'], context=context) """
			
        this.reconcile_saleorder = new_id
        if this.sale_id : 
            client_order_ref = this.sale_id.client_order_ref or ""
            this.sale_id.client_order_ref = client_order_ref +	"-" + u"冲减销售单:" + sale_order_name
			
        return {'type': 'ir.actions.act_url', 'url': "web#id=%s&view_type=form&model=sale.order&action=359" % new_id, 'target': 'self'} 	
	
    @api.cr_uid_ids_context
    def do_prepare_partial(self, cr, uid, picking_ids, context=None):
        context = context or {}
        pack_operation_obj = self.pool.get('stock.pack.operation')
        #used to avoid recomputing the remaining quantities at each new pack operation created
        ctx = context.copy()
        ctx['no_recompute'] = True

        #get list of existing operations and delete them
        existing_package_ids = pack_operation_obj.search(cr, uid, [('picking_id', 'in', picking_ids)], context=context)
        if existing_package_ids:
            pack_operation_obj.unlink(cr, uid, existing_package_ids, context)
        for picking in self.browse(cr, uid, picking_ids, context=context):
            forced_qties = {}  # Quantity remaining after calculating reserved quants
            picking_quants = []
			
            if picking.picking_type_id.code == 'incoming' :# or picking.picking_type_id.id == 19 :
                for move in picking.move_lines:	
                    if move.state not in ('assigned', 'confirmed'):
                        continue				
                    values = {'picking_id':picking.id, 'product_qty':move.product_uom_qty, 'product_id':move.product_id.id, 'location_id':move.location_id.id, 'location_dest_id':move.location_dest_id.id, 'product_uom_id':move.product_uom.id}						
                    pack_id = pack_operation_obj.create(cr, uid, values, context=ctx)							
			
                continue		

            #if picking.picking_type_id.id == 19 :
            #    for move in picking.move_lines:	
            #        if move.reserved_availability < 1 : continue	#### 这里有问题			
            #        values = {'picking_id':picking.id, 'product_qty': move.reserved_availability, 'product_id':move.product_id.id, 'location_id':move.location_id.id, 'location_dest_id':move.location_dest_id.id, 'product_uom_id':move.product_uom.id}						
            #        pack_id = pack_operation_obj.create(cr, uid, values, context=ctx)							
			
            #    continue					
			
            #Calculate packages, reserved quants, qtys of this picking's moves	
            for move in picking.move_lines:
			
                usage = move.location_id.usage			
                if move.state not in ('assigned', 'confirmed')  or ( not move.reserved_availability and usage == 'internal' ) :
                    continue					

                if usage == 'internal' : product_qty = move.reserved_availability
                else: product_qty = move.product_uom_qty
				
                vals = {'picking_id':picking.id, 'product_qty':product_qty, 'product_id':move.product_id.id, 'location_id':move.location_id.id, 'location_dest_id':move.location_dest_id.id, 'product_uom_id':move.product_uom.id}	
                pack_operation_obj.create(cr, uid, vals, context=ctx)
                continue
					
                move_quants = move.reserved_quant_ids
                picking_quants += move_quants	
                						
                sum_val = sum([x.qty for x in move_quants])								
                forced_qty = (move.state == 'assigned') and move.product_qty - sum_val or 0
                #if we used force_assign() on the move, or if the move is incoming, forced_qty > 0               				
                if float_compare(forced_qty, 0, precision_rounding=move.product_id.uom_id.rounding) > 0:
                    if forced_qties.get(move.product_id):
                        forced_qties[move.product_id] += forced_qty
                    else:
                        forced_qties[move.product_id] = forced_qty                                						
						
            #for vals in self._prepare_pack_ops(cr, uid, picking, picking_quants, forced_qties, context=context):
            #    pack_operation_obj.create(cr, uid, vals, context=ctx)
                				
        #recompute the remaining quantities all at once
        self.do_recompute_remaining_quantities(cr, uid, picking_ids, context=context)
        self.write(cr, uid, picking_ids, {'recompute_pack_op': False}, context=context)	
		
    def _create_backorder(self, cr, uid, picking, backorder_moves=[], context=None):
        """ Move all non-done lines into a new backorder picking. If the key 'do_only_split' is given in the context, then move all lines not in context.get('split', []) instead of all non-done lines.
        """
        if not backorder_moves:
            backorder_moves = picking.move_lines
        backorder_move_ids = [x.id for x in backorder_moves if x.state not in ('done', 'cancel')]
        if 'do_only_split' in context and context['do_only_split']:
            backorder_move_ids = [x.id for x in backorder_moves if x.id not in context.get('split', [])]

        if backorder_move_ids:
            backorder_id = self.copy(cr, uid, picking.id, {
                'name': '/',
                'move_lines': [],
                'pack_operation_ids': [],
                'backorder_id': picking.id,
            })
            backorder = self.browse(cr, uid, backorder_id, context=context)
            #add by jimmy, to set picking_type as backorder			
            if backorder.picking_type_id.code == 'outgoing' : backorder.picking_type_id = self.pool.get("stock.picking.type").search(cr, uid, [('name', '=', 'Backorders')], context={'lang':'en_US'})[0]		
            self.message_post(cr, uid, picking.id, body=_("Back order <em>%s</em> <b>created</b>.") % (backorder.name), context=context)
            move_obj = self.pool.get("stock.move")
            move_obj.write(cr, uid, backorder_move_ids, {'picking_id': backorder_id}, context=context)

            self.write(cr, uid, [picking.id], {'date_done': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)
            self.action_confirm(cr, uid, [backorder_id], context=context)
            return backorder_id
        return False	

class stock_picking_type(osv.osv):
    _inherit = "stock.picking.type"			

    def _get_picking_count_done(self, cr, uid, ids, field_names, arg, context=None):
        obj = self.pool.get('stock.picking')
        domains = {
            'count_picking_draft_cancel': [('state', 'in', ['draft','cancel'])],
            'count_picking_done': [('state', '=', 'done')],			
            'count_picking_waiting_financial': [('state', '=', 'waiting_financial')],
        }
        result = {}
        for field in domains:
            data = obj.read_group(cr, uid, domains[field] + [('picking_type_id', 'in', ids)], ['picking_type_id'], ['picking_type_id'], context=context)
            count = dict(map(lambda x: (x['picking_type_id'] and x['picking_type_id'][0], x['picking_type_id_count']), data))
            for tid in ids:
                result.setdefault(tid, {})[field] = count.get(tid, 0)

        return result	
	
    _columns = {
        'count_picking_draft_cancel': fields.function(_get_picking_count_done,
            type='integer', multi='_get_picking_count_done'),	
        'count_picking_done': fields.function(_get_picking_count_done,
            type='integer', multi='_get_picking_count_done'),
        'count_picking_waiting_financial': fields.function(_get_picking_count_done,
            type='integer', multi='_get_picking_count_done'),			
    }			

	