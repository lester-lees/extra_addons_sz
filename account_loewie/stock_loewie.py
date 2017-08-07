# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import logging

_logger = logging.getLogger(__name__)


class stock_move(osv.osv):
    _inherit = "stock.move"
    _order = 'id , date_expected desc'
	
    def _get_sale_order_line(self, cr, uid, ids, field_name, arg, context=None):	
        result = {}
        for move in self.pool.get('stock.move').browse(cr, uid, ids, context=context):
            result[move.id] = move.procurement_id.sale_line_id.id
        return result	
	
    _columns = {
        'sale_order_line': fields.function(_get_sale_order_line, type='many2one', relation='sale.order.line',string='Sales Line'),		
    }

class stock_picking(osv.osv):
    _inherit = 'stock.picking'
    _order = "id desc, priority desc, date asc"	

    def _search_saleorder_id(self, cr, uid, obj, name, domain, context):
        res = []
        for field, operator, value in domain:
            #to prevent sql injections
            assert field in ('salesorder_id','sale_id'), 'Invalid domain left operand'
            assert operator in ('<', '>', '=', '!=', '<=', '>='), 'Invalid domain operator'
            assert isinstance(value, (float, int)), 'Invalid domain right operand'

            if operator == '=':
                operator = '=='

            pick_ids = self.search(cr, uid, [], context=context)
            ids = []
            if pick_ids:
                #TODO: use a query instead of this browse record which is probably making the too much requests, but don't forget
                #the context that can be set with a location, an owner...
                for element in self.browse(cr, uid, pick_ids, context=context):
                    str_eval = 	str(element[field].id) + operator + str(value)			
                    if eval(str_eval):
                        ids.append(element.id)
            res.append(('id', 'in', ids))
        return res
	
    def _get_saleorder_id(self, cr, uid, ids, name, args, context=None):
        sale_obj = self.pool.get("sale.order")
        res = {}
        for picking in self.browse(cr, uid, ids, context=context):
            res[picking.id] = False
            if picking.group_id:
                sale_ids = sale_obj.search(cr, uid, [('procurement_group_id', '=', picking.group_id.id)], context=context)
                if sale_ids:
                    res[picking.id] = sale_ids[0]
        return res	

    def _default_sales_person(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context)
        res = self.pool.get('stock.warehouse').search(cr, uid, [('company_id', '=', user.company_id.id)], limit=1, context=context)
        return res and res[0] or False
		
    _columns = {
        'sale_id': fields.function(_get_saleorder_id, type="many2one", relation="sale.order", string="Sale Order", fnct_search=_search_saleorder_id, store=True),	
        'ref_invoice':fields.many2one('account.invoice',string=u'关联发票', copy=False),		
        'sales_person': fields.many2one('res.users',string=u'销售人员',store=True),			
    }
    _defaults = {
        'sales_person': _default_sales_person,	
    }	

    def show_so_delivery(self, cr, uid, ids, context=None):	
	
        group1 = [16,26,28,44]	 # china sales 16,26,28,44 ->Mirror, Manager_Temporarily, Angela, Michelle
        group2 = [41,35,27,46]		# e-commerce 41,35,27,46 -> Vivien, Andy, Lois, aileen,   
        		
        if uid in group1 :
            group = group1
        elif uid in group2:
            group = group2
        elif uid== 1:
            group = group1 + group2
        else:			
            return 		
			
        act_obj = self.pool.get('ir.actions.act_window')
        statement0 = """select id from stock_picking where picking_type_id in (2,19) and state not in ('done','draft','cancel') and sales_person in (%s)"""  % ','.join( map(str,group) )
        statement1 = """select id from stock_picking where picking_type_id in (2,19) and state='done' and sales_person in (%s)"""  % ','.join( map(str,group) )
        statement = ids and statement1 or statement0 		
        cr.execute(statement)
        picks = [ item[0] for item in cr.fetchall()]	
			
        result = act_obj.read(cr, uid, [483], context=context)[0]	
        result['domain'] = "[('id','in',[" + ','.join(map(str, picks)) + "])]"	        		
        result['context'] = result['context'].replace( '{', "{'default_picking_type_id':19," )
        #_logger.info(result['domain'])			
        return result			
		
    def show_return_delivery(self, cr, uid, ids, context=None):	

        picks = []	
 		
        group1 = [16,26,28,44]	 # china sales 16,26,28,44 ->Mirror, Manager_Temporarily, Angela, Michelle
        group2 = [41,35,27,46]		# e-commerce 41,35,27,46 -> Vivien, Andy, Lois, aileen,   in (2,19)
        		
        if uid in group1 :
            group = group1
        elif uid in group2:
            group = group2
        elif uid== 1:
            group = group1 + group2
        else:			
            return 		
			
        act_obj = self.pool.get('ir.actions.act_window')
        statement = """select id from stock_picking where picking_type_id=20 and sales_person in (%s)"""  % ','.join( map(str,group) )		
        cr.execute(statement)
		
        for i in cr.fetchall():
            picks.append(i[0])	
			
        result = act_obj.read(cr, uid, [1042], context=context)[0]	
        result['domain'] = "[('id','in',[" + ','.join(map(str, picks)) + "])]"	        		
        result['context'] = result['context'].replace( '{', "{'default_picking_type_id':20," )
        #_logger.info(result['domain'])			
        return result			
	
    def show_account_delivery(self, cr, uid, ids, context=None):

        act_obj = self.pool.get('ir.actions.act_window')	
        #if ids == 0 or ids == 1 :		
        result = act_obj.read(cr, uid, [483], context=context)[0]
			
        #if ids == 2 or ids == 3 :		
        #    result = act_obj.read(cr, uid, [1], context=context)[0]			
			
        if ids == 0:		
            result['domain'] = "[('state','=','done'), ('ref_invoice','=',False),('picking_type_id','in',[2,19])]"		
        elif  ids == 1:
            result['domain'] = "[('state','=','done'), ('ref_invoice','!=',False),('picking_type_id','in',[2,19])]"	
        elif ids == 2:		
            result['domain'] = "[('state','=','done'), ('ref_invoice','=',False),('picking_type_id','in',[1,20])]"		
        elif  ids == 3:
            result['domain'] = "[('state','=','done'), ('ref_invoice','!=',False),('picking_type_id','in',[1,20])]"		
			
        return result	
	
    def _invoice_create_line(self, cr, uid, moves, journal_id, inv_type='out_invoice', context=None):
        invoice_obj = self.pool.get('account.invoice')
        move_obj = self.pool.get('stock.move')
        invoices = {}
        _logger.info("Jimmy --- _invoice_create_line in sotck_loewie")		
		
        for move in moves:
            company = move.company_id
            origin = move.picking_id.name
            partner, user_id, currency_id = move_obj._get_master_data(cr, uid, move, company, context=context)

            key = (partner, currency_id, company.id, user_id)
            invoice_vals = self._get_invoice_vals(cr, uid, key, inv_type, journal_id, move, context=context)

            if key not in invoices:
                # Get account and payment terms
                invoice_id = self._create_invoice_from_picking(cr, uid, move.picking_id, invoice_vals, context=context)
                invoices[key] = invoice_id				
                invoice = invoice_obj.browse(cr, uid, [invoice_id], context=context)[0]	
                invoice.write({'picking_id': move.picking_id.id})				
                move.picking_id.ref_invoice = invoice_id				
                _logger.info("Jimmy picking_id:%d" % move.picking_id.id)				
                if move.picking_id.sale_id : 
                    invoice.write({'sale_id': move.picking_id.sale_id.id})				
                    _logger.info("Jimmy sale_id:%d" % move.picking_id.sale_id.id)					
            else:
                invoice = invoice_obj.browse(cr, uid, invoices[key], context=context)
                if not invoice.origin or invoice_vals['origin'] not in invoice.origin.split(', '):
                    invoice_origin = filter(None, [invoice.origin, invoice_vals['origin']])
                    invoice.write({'origin': ', '.join(invoice_origin)})
                invoice.write({'picking_id': move.picking_id.id})					
                _logger.info("Jimmy nokey picking_id:%d" % move.picking_id.id)	
                move.picking_id.ref_invoice = invoice_id				
                if move.picking_id.sale_id : 
                    _logger.info("Jimmy nokey sale_id:%d" % move.picking_id.sale_id.id)                    				
                    invoice.write({'sale_id': move.picking_id.sale_id.id})					

            invoice_line_vals = move_obj._get_invoice_line_vals(cr, uid, move, partner, inv_type, context=context)
            invoice_line_vals['invoice_id'] = invoices[key]
            invoice_line_vals['origin'] = origin

            move_obj._create_invoice_line_from_vals(cr, uid, move, invoice_line_vals, context=context)
            move_obj.write(cr, uid, move.id, {'invoice_state': 'invoiced'}, context=context)

        invoice_obj.button_compute(cr, uid, invoices.values(), context=context, set_total=(inv_type in ('in_invoice', 'in_refund')))
        return invoices.values()	