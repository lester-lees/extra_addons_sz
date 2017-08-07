# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import datetime
import socket
import logging
from openerp import api
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

class loewie_shipping_label(osv.osv):
    _name = "loewie.shipping.label"
	
    _columns = {
        'name': fields.char( string='Express Name'),
        'field':fields.char(string='Field'),		
        'left': fields.integer(string='Left'),
        'top':fields.integer(string='Top'),	
        'right': fields.integer(string='Right'),		
        'bottom': fields.integer(string='Bottom'),	
    }

class loewie_recipients(osv.osv):
    _name = "loewie.recipients"
	
    _columns = {
        #'name': fields.integer( string='Name'),	
        'sale_id': fields.many2one('sale.order', string='Sales Order'),
        'picking_id':fields.many2one('stock.picking',string='Picking'),	
        'name': fields.char(string='Name'),		
        'cellphone': fields.char(string='Cell Phone'),
        'address': fields.char(string='Shipping Address'),		
    }	
	
class stock_picking(osv.osv):
    _inherit = "stock.picking"
	
    _columns = {
        'recipient_ids': fields.one2many('loewie.recipients', 'picking_id', string='Recipient'),	
    }				
	
    def print_shipping_label(self, cr, uid, ids, context=None):	
	
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)	
        server_ip = ("192.168.0.203", 8333)
        sock.connect(server_ip)
        msg = "Courrier:%s;Name:%s;Tel:%s;Address:%s;State:%s;City:%s"

        sock.sendal(msg)
        data = sock.recv(24)
        if data = 0:
            raise osv.except_osv(u'打印错误',u'xxxxxx')		
        sock.close()		
	
class stock_move(osv.osv):
    _inherit = "stock.move"
	
    _columns = {
        'recipient_id': fields.many2one('loewie.recipients', string='Recipient'),	
    }
	

	

class sale_order(osv.osv):
    _inherit = "sale.order"
	
    _columns = {
        'recipient_ids': fields.one2many('loewie.recipients', 'sale_id', string='Recipient'),		
    }		

    def action_view_delivery(self, cr, uid, ids, context=None):
        #_logger.info("Jimmy action_view_delivery") 
        for so in self.browse(cr, uid, ids, context=context):	
            #so.validated_by = 		
            if so.user_id is not None:				
                for pick in so.picking_ids:
                    pick_id = pick.id				
                    pick.add_followers({'ids':[pick.id], 'user_ids':[so.user_id.id]}, context=context)
                    pick.create_uid = so.user_id.id	
                    if pick.state == 'confirmed' or pick.state == 'partially_available':
                        statement = "update ir_attachment set res_id=%d, res_model='stock.picking', res_name='%s' where res_id=%d and datas_fname like '%s.xlsx'" % ( pick.id, pick.name, so.id, '%' )
                        cr.execute(statement)					
                        pick.action_assign()
						
                    for line in pick.move_lines:	
                        if pick.state == 'confirmed' or pick.state == 'partially_available' or pick.state == 'assigned':					
                            line.recipient_id = line.procurement_id.sale_line_id.recipient_id.id
                            line.recipient_id.picking_id = pick_id						
                            #line.procurement_id.sale_line_id.recipient_id.picking_id = pick.id	
					
                        if line.name and line.name.find('RMA')>=0 and line.state != 'done':			
                            line.location_id = 20 # Standby Location ID = 20      
        
        return super(sale_order, self).action_view_delivery(cr, uid, ids, context=None)
	
class sale_order_line(osv.osv):
    _inherit = "sale.order.line"
	
    _columns = {
        'recipient_id': fields.many2one('loewie.recipients', string='Recipient'),		
    }	

    def duplicate_sale_order_line(self, cr, uid, ids, context=None):
	
        sale_order_line_obj = self.pool.get('sale.order.line')		
		
        for line in self.browse(cr, uid, ids, context=context):
            sale_order_line_obj.copy(cr, uid, line.id, default={}, context=context)			

        return		