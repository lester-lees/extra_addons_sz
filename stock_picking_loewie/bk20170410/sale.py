# -*- coding: utf-8 -*- manager_confirm_btn
from openerp.osv import fields, osv
import csv
import cStringIO
import base64
import psycopg2
import datetime
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round
import logging
_logger = logging.getLogger(__name__)

class product_product(osv.osv):
    _inherit = "product.product"
	
    def _qty_avail(self, cr, uid, ids, field_names=None, arg=False, context=None):
        context = context or {}
        field_names = field_names or []      		
		
        domain_products = [('product_id', 'in', ids)]
        domain_quant, domain_move_in, domain_move_out = self._get_domain_locations(cr, uid, ids, context=context)
		
        yesterday = datetime.datetime.today() - datetime.timedelta(days=1)		
        yesterday = "%d-%d-%d 00:00:01" % ( yesterday.year , yesterday.month, yesterday.day )
        before_dawn = "%d-%d-%d 00:00:01" % (datetime.datetime.today().year , datetime.datetime.today().month,  datetime.datetime.today().day )		
        to_date = "%s" % datetime.datetime.today()		
		
        domain_move_yesterday_in = domain_move_in + self._get_domain_dates(cr, uid, ids, context={'from_date':yesterday,'to_date':before_dawn}) + [('state', '=', 'done')] + domain_products
        domain_move_yesterday_out = domain_move_out + self._get_domain_dates(cr, uid, ids, context={'from_date':yesterday,'to_date':before_dawn}) + [('state', '=', 'done')] + domain_products
        domain_move_day_in = domain_move_in + self._get_domain_dates(cr, uid, ids, context={'from_date':before_dawn,'to_date':to_date}) + [('state', '=', 'done')] + domain_products
        domain_move_day_out = domain_move_out + self._get_domain_dates(cr, uid, ids, context={'from_date':before_dawn,'to_date':to_date}) + [('state', '=', 'done')] + domain_products
		
        domain_move_out += self._get_domain_dates(cr, uid, ids, context=context) + [('state', 'not in', ('done', 'cancel', 'draft'))] + domain_products
        domain_quant += domain_products
		
        if context.get('lot_id') or context.get('owner_id') or context.get('package_id'):
            if context.get('lot_id'):
                domain_quant.append(('lot_id', '=', context['lot_id']))
            if context.get('owner_id'):
                domain_quant.append(('owner_id', '=', context['owner_id']))
            if context.get('package_id'):
                domain_quant.append(('package_id', '=', context['package_id']))
            moves_out = []
        else:
            moves_out = self.pool.get('stock.move').read_group(cr, uid, domain_move_out, ['product_id', 'product_qty'], ['product_id'], context=context)
            moves_move_yesterday_in = self.pool.get('stock.move').read_group(cr, uid, domain_move_yesterday_in, ['product_id', 'product_qty'], ['product_id'], context=context)			
            moves_move_yesterday_out = self.pool.get('stock.move').read_group(cr, uid, domain_move_yesterday_out, ['product_id', 'product_qty'], ['product_id'], context=context)		
            moves_move_day_in = self.pool.get('stock.move').read_group(cr, uid, domain_move_day_in, ['product_id', 'product_qty'], ['product_id'], context=context)
            moves_move_day_out = self.pool.get('stock.move').read_group(cr, uid, domain_move_day_out, ['product_id', 'product_qty'], ['product_id'], context=context)		

        # 计算 电商 库位 的库存
        domain_qty_avail_ec = [('location_id', '=', 39),('reservation_id','=',False)] + domain_products	
        quants_qty_avail_ec = self.pool.get('stock.quant').read_group(cr, uid, domain_qty_avail_ec, ['product_id', 'qty'], ['product_id'], context=context)
        quants_qty_avail_ec = dict(map(lambda x: (x['product_id'][0], x['qty']), quants_qty_avail_ec))
		
        domain_qty_onhand_ec = [('location_id', '=', 39)] + domain_products		
        quants_qty_onhand_ec = self.pool.get('stock.quant').read_group(cr, uid, domain_qty_onhand_ec, ['product_id', 'qty'], ['product_id'], context=context)
        quants_qty_onhand_ec = dict(map(lambda x: (x['product_id'][0], x['qty']), quants_qty_onhand_ec))			
			
        # 计算 正常成品库位 的库存			
        quants_avail = self.pool.get('stock.quant').read_group(cr, uid, domain_quant + [('reservation_id','=',False)], ['product_id', 'qty'], ['product_id'], context=context)
        quants_avail = dict(map(lambda x: (x['product_id'][0], x['qty']), quants_avail))
        quants_normal_all = self.pool.get('stock.quant').read_group(cr, uid, domain_quant, ['product_id', 'qty'], ['product_id'], context=context)
        quants_normal_all = dict(map(lambda x: (x['product_id'][0], x['qty']), quants_normal_all))		
		
        domain_quants_deficient = [('location_id', '=', 18)] + domain_products		
        domain_quants_standby =  [('location_id', '=', 20)] + domain_products		

        quants_deficient = self.pool.get('stock.quant').read_group(cr, uid, domain_quants_deficient, ['product_id', 'qty'], ['product_id'], context=context)	
        quants_standby =  self.pool.get('stock.quant').read_group(cr, uid, domain_quants_standby, ['product_id', 'qty'], ['product_id'], context=context)	
        quants_deficient = dict(map(lambda x: (x['product_id'][0], x['qty']), quants_deficient))
        quants_standby = dict(map(lambda x: (x['product_id'][0], x['qty']), quants_standby))		

        moves_out = dict(map(lambda x: (x['product_id'][0], x['product_qty']), moves_out))
        moves_move_yesterday_in = dict(map(lambda x: (x['product_id'][0], x['product_qty']), moves_move_yesterday_in))
        moves_move_yesterday_out = dict(map(lambda x: (x['product_id'][0], x['product_qty']), moves_move_yesterday_out))
        moves_move_day_in = dict(map(lambda x: (x['product_id'][0], x['product_qty']), moves_move_day_in))
        moves_move_day_out = dict(map(lambda x: (x['product_id'][0], x['product_qty']), moves_move_day_out))
		
        res = {}
        for product in self.browse(cr, uid, ids, context=context):
            id = product.id
            # qty_avail_store	= product.qty_avail_store			
			
            quants_avail_qty = quants_avail.get(id, 0.0)	
            qty_quants_all = float_round( quants_normal_all.get(id, 0.0), precision_rounding=product.uom_id.rounding ) # quants_all
			
            virtual_available = quants_avail_qty #float_round( quants_all_qty - moves_out.get(id, 0.0), precision_rounding=product.uom_id.rounding)
            yesterday_in_qty = float_round(moves_move_yesterday_in.get(id, 0.0), precision_rounding=product.uom_id.rounding)			
            yesterday_out_qty = float_round(moves_move_yesterday_out.get(id, 0.0), precision_rounding=product.uom_id.rounding)
            day_in_qty = float_round(moves_move_day_in.get(id, 0.0), precision_rounding=product.uom_id.rounding)
            day_out_qty = float_round(moves_move_day_out.get(id, 0.0), precision_rounding=product.uom_id.rounding)						
            deficient_qty = quants_deficient.get(id, 0.0)
            standby_qty	= quants_standby.get(id, 0.0)	

            qty_avail_ec = float_round(quants_qty_avail_ec.get(id, 0.0), precision_rounding=product.uom_id.rounding)
            qty_onhand_ec = float_round(quants_qty_onhand_ec.get(id, 0.0), precision_rounding=product.uom_id.rounding)			
         				
            # if qty_avail_store != virtual_available : product.qty_avail_store = virtual_available 			
			
            res[id] = {
                'qty_avail': virtual_available,
                'qty_avail_ec': qty_avail_ec,
                'qty_onhand_ec': qty_onhand_ec,
                'qty_onhand_total': qty_onhand_ec + qty_quants_all,					
				
                'yesterday_in_qty': yesterday_in_qty,
                'yesterday_out_qty': yesterday_out_qty,
                'day_in_qty': day_in_qty,
                'day_out_qty': day_out_qty,	
                'deficient_qty': deficient_qty,				
                'standby_qty': standby_qty,					
            }
			
        return res
		
    def _search_product_qty(self, cr, uid, obj, name, domain, context):
        res = []
        for field, operator, value in domain:
            #to prevent sql injections
            assert field in ('qty_avail', 'qty_avail_ec', 'qty_onhand_ec', 'qty_onhand_total', 'yesterday_in_qty', 'yesterday_out_qty', 'day_in_qty','day_out_qty','deficient_qty','standby_qty'), 'Invalid domain left operand'
            assert operator in ('<', '>', '=', '!=', '<=', '>='), 'Invalid domain operator'
            assert isinstance(value, (float, int)), 'Invalid domain right operand'

            if operator == '=':
                operator = '=='

            product_ids = self.search(cr, uid, [], context=context)
            ids = []
            if product_ids:
                for element in self.browse(cr, uid, product_ids, context=context):
                    if eval(str(element[field]) + operator + str(value)):
                        ids.append(element.id)
            res.append(('id', 'in', ids))
        return res		
		
    def _is_liquid(self, cr, uid, ids, field_names=None, arg=False, context=None):
	
        res = {}	
        		
        for product in self.browse(cr, uid, ids, context=context):		
            is_create = context.get('create_product_product',False)           		
            id = product.id		
            name_template = is_create and product.display_name or product.name_template
			
            if not name_template or product.is_sample or product.is_market or product.is_materials or name_template.find('ml')<0 : 		
                res[id] = False
            else:		
                res[id] = True	
			
        return res
		
    _columns = {	
        'clean_inventory': fields.boolean(u'Clean Inventory', default=False, help="Clean the Inventory of this product."),
        #'is_liquid_product': fields.boolean(string=u"液体产品?"),		
        'is_liquid_product': fields.function(_is_liquid, type='boolean',string=u"Is液体产品", store=True), # boolean(u'液体产品?',default=False),	
        #'is_appliance_product': fields.function(_is_liquid, type='boolean',string=u"器具产品?", multi='is_liquid_product'), #boolean(u'器具产品?',default=True),			
        'is_clean_inventory': fields.boolean(u'Is清库存', default=False, help="清库存产品"),		
        'is_sample': fields.boolean(u'Is样品', default=False, help="Is Sample."),	
        'is_market': fields.boolean(u'Is市场物质', default=False, help="Is Market Materials."),
        'is_materials': fields.boolean(u'Is包材配件', default=False, help="Is Packaging Materials."),		
        'qty_avail_store': fields.integer(string=u'未预留库存2', default=0 ),	
		
        'qty_avail': fields.function(_qty_avail, type='integer',string=u"可用库存", multi='qty_avail',fnct_search=_search_product_qty),	
        'qty_avail_ec': fields.function(_qty_avail, type='integer',string=u"电商可用", multi='qty_avail',fnct_search=_search_product_qty),
        'qty_onhand_ec': fields.function(_qty_avail, type='integer',string=u"电商在手", multi='qty_avail',fnct_search=_search_product_qty),
        'qty_onhand_total': fields.function(_qty_avail, type='integer',string=u"总计在手", multi='qty_avail',fnct_search=_search_product_qty),		
		
        'yesterday_in_qty': fields.function(_qty_avail, type='integer',string=u"昨日入库", multi='qty_avail',fnct_search=_search_product_qty),
        'yesterday_out_qty': fields.function(_qty_avail, type='integer',string=u"昨日出库", multi='qty_avail',fnct_search=_search_product_qty),
        'day_in_qty': fields.function(_qty_avail, type='integer',string=u"今日入库", multi='qty_avail',fnct_search=_search_product_qty),   # 只包含 良品的出入库
        'day_out_qty': fields.function(_qty_avail, type='integer',string=u"今日出库", multi='qty_avail',fnct_search=_search_product_qty),
		
        #'last_month_qty': fields.function(_qty_avail, type='integer',string="上月结存", multi='qty_avail',fnct_search=_search_product_qty),
        'deficient_qty': fields.function(_qty_avail, type='integer',string="不良品数", multi='qty_avail',fnct_search=_search_product_qty),		
        'standby_qty': fields.function(_qty_avail, type='integer',string="待用仓数", multi='qty_avail',fnct_search=_search_product_qty),		
    }
		
	
class sale_order_line(osv.osv):
    _inherit = "sale.order.line"	
	
    def _qty_transfered(self, cr, uid, ids, field_names=None, arg=False, context=None):	
        res = {}		
 
        for line in self.browse(cr, uid, ids, context=context):
            qty_transfered = qty_return = 0
			
            if line.product_id.type == 'service' or line.product_uom_qty < 0 : 	
                res[line.id] = {'qty_transfered': qty_transfered,'qty_return': qty_return}
                continue			
				
            for move in line.procurement_ids.move_ids : 
                if move.state != 'done': continue
                if move.location_dest_id.usage == 'internal' and move.location_id.usage != 'internal':				
                    qty_return += move.product_uom_qty
                else:					
                    qty_transfered += move.product_uom_qty				
						
            res[line.id] = {'qty_transfered': qty_transfered,'qty_return': qty_return}	
			
        return res
		
    _columns = {
        'default_code':fields.char('Product Description'),
        'qty_transfered':fields.function(_qty_transfered, type='float',multi='_qty_transfered',string=u"已发货数"),	
        'qty_return':fields.function(_qty_transfered, type='float',multi='_qty_transfered',string=u"已退货数"),			
    }		
	
class sale_order(osv.osv):
    _inherit = 'sale.order'	

    def set_order_line_status(self, cr, uid, ids, status, context=None):
        line = self.pool.get('sale.order.line')
        order_line_ids = []
        proc_obj = self.pool.get('procurement.order')
        for order in self.browse(cr, uid, ids, context=context):
            order_line_ids += [po_line.id for po_line in order.order_line]
        if order_line_ids:
            line.write(cr, uid, order_line_ids, {'state': status}, context=context)
        if order_line_ids and status == 'cancel':
            procs = proc_obj.search(cr, uid, [('sale_line_id', 'in', order_line_ids)], context=context)
            if procs:
                proc_obj.write(cr, uid, procs, {'state': 'exception'}, context=context)
                proc_obj.unlink()				
        return True	

    def action_cancel_draft(self, cr, uid, ids, context=None):
        if not len(ids):
            return False
        self.write(cr, uid, ids, {'state':'draft','shipped':0})
        self.set_order_line_status(cr, uid, ids, 'draft', context=context)
        for p_id in ids:
            # Deleting the existing instance of workflow for PO
            self.delete_workflow(cr, uid, [p_id]) # TODO is it necessary to interleave the calls?
            self.create_workflow(cr, uid, [p_id])
			
        this = self.browse(cr, uid, ids[0], context=context)			
		
        if this.procurement_group_id:			
            for line in this.procurement_group_id.procurement_ids:		
                line.unlink()
            this.procurement_group_id.unlink()				
			
        return True	
	
    #@api.one	
    def calc_total_weight(self, cr, uid, ids, context=None): #self, cr, uid, ids, name, attr, context=None): 
	
        weight = 0
        this = self.browse(cr, uid, ids, context=context)[0]	
		
        for line in this.order_line :
            weight = weight + line.product_id.weight * line.product_uom_qty		
			
        this.write({'total_weight':weight})	
		
        return
		
			
    _columns = {
        'note_delivery': fields.text( string=u'备注信息', readonly=False, states={'done': [('readonly', True)]} ),
        'note_financial': fields.char( string=u'付款信息', readonly=False, states={'done': [('readonly', True)]} ),		
        'upload_file':fields.binary('Up&Download Order Lines'),	
        'return_pick':fields.many2one('stock.picking',string=u'客户退货单'),
        'ref_invoice':fields.related('return_pick', 'ref_invoice', type='many2one', relation='account.invoice', string='退货发票'),		 # 'account.invoice',string=u'关联发票'
        'total_weight' : fields.float('Total Weight') ,	
        'validated_by':fields.many2one('res.users',string='Validated By'),		
        'state': fields.selection([
            ('draft', 'Draft Quotation'),
            ('sent', 'Quotation Sent'),
            ('manager_confirm','Manager Confirm'),			
            ('cancel', 'Cancelled'),
            ('waiting_date', 'Waiting Schedule'),
            ('progress', 'Sales Order'),
            ('manual', 'Sale to Invoice'),
            ('shipping_except', 'Shipping Exception'),
            ('invoice_except', 'Invoice Exception'),
            ('done', 'Done'),
            ], 'Status', readonly=True, copy=False, help="Gives the status of the quotation or sales order.\
              \nThe exception status is automatically set when a cancel operation occurs \
              in the invoice validation (Invoice Exception) or in the picking list process (Shipping Exception).\nThe 'Waiting Schedule' status is set when the invoice is confirmed\
               but waiting for the scheduler to run on the order date.", select=True),
        'country_id': fields.related('partner_id', 'country_id', type='many2one', relation='res.country', string='Country')			   
    }
		
    def manager_confirm_btn(self, cr, uid, ids, context=None): #self, cr, uid, ids, name, attr, context=None): 
		
        for so in self.browse(cr, uid, ids, context=context) :
            so.validated_by = uid				

        return	
	
    #@api.one	
    def export_csv(self, cr, uid, ids, context=None):

        this = self.browse(cr, uid, ids, context=context)[0]	
        buf = cStringIO.StringIO()
        writer = csv.writer(buf)		
		
        for line in this.order_line:
            writer.writerow([line.product_id.id,line.name,line.product_uom_qty,line.price_unit,line.product_uom.id])		
			
        out = base64.encodestring(buf.getvalue())
        this.write({'upload_file':out})	
		
        return		

    #@api.one		
    def import_csv(self, cr, uid, ids, context=None):
	
        this = self.browse(cr, uid, ids, context=context)[0]
        sol_obj = self.pool.get('sale.order.line')		#sol_obj: sale.order.line
        buf = cStringIO.StringIO(base64.decodestring(this.upload_file))
        reader = csv.reader(buf)		
		
        for line in reader:            		
            statement = "insert into sale_order_line(order_id,product_id,name,product_uom_qty,price_unit,product_uom,delay,state) values(%d,%s,'%s',%s,%s,%s,7,'draft')" % ( this.id, line[0], line[1], line[2], line[3], line[4])			
            cr.execute(statement)			
		
        for line in this.order_line:
            vals = sol_obj.product_id_change(
                cr, uid, line.id, this.pricelist_id.id,
                product=line.product_id.id, qty=line.product_uom_qty,
                uom=line.product_uom.id, qty_uos=line.product_uos_qty,
                uos=line.product_uos.id, name=line.name,
                partner_id=this.partner_id.id,
                lang=False, update_tax=True, date_order=this.date_order,
                packaging=False, fiscal_position=False, flag=False, context=context)
            sol_obj.write(cr, uid, line.id, vals['value'], context=context)            		
			
        return			

    def onchange_pricelist_id(self, cr, uid, ids, pricelist_id, order_lines, context=None):
	
        context = context or {}
        if not pricelist_id:
            return {}
        pricelist_obj = self.pool.get('product.pricelist')
        pricelist_this_obj = pricelist_obj.browse(cr, uid, pricelist_id, context=context)		
        value = {
            'currency_id': pricelist_this_obj.currency_id.id
        }
        if not order_lines or order_lines == [(6, 0, [])]:
            return {'value': value}

        obj_precision = self.pool.get('decimal.precision')
        prec = obj_precision.precision_get(cr, uid, 'Account')
        currency_obj = self.pool.get('res.currency')		
        this = self.browse(cr, uid, ids, context=context)[0]		
		
        for line in this.order_line:
            line.pur_currency_id = line.product_id.purchase_currency_id.id		
			
            #line.pur_price_unit = round(pricelist_obj.price_get(cr, uid, [pricelist_id], line.product_id.id, 1.0, this.partner_id.id,{'uom': line.product_uom.id, 'date': this.date_order})[pricelist_id], prec)		
            
            #if line.pur_price_unit == 0 and pricelist_this_obj.use_purchase_currency :
            line.pur_price_unit = line.get_price( pricelist_id, line.product_id.id)	
				
            if pricelist_this_obj.use_purchase_currency :
                line.price_unit = 	currency_obj.compute(cr, uid, line.pur_currency_id.id, value['currency_id'],line.pur_price_unit, context=context)	
            else:
                line.price_unit = line.pur_price_unit
				
            line.subtotal = round(line.price_unit * line.product_uom_qty / (100 - line.discount)*100 ,prec)
		
			
        warning = {
            'title': _('Pricelist Warning!'),
            'message' : _('If you change the pricelist of this order (and eventually the currency), prices of existing order lines will not be updated.')
        }
        return {'warning': warning, 'value': value}	
		
		
			
    def action_view_delivery(self, cr, uid, ids, context=None):
 
        for so in self.browse(cr, uid, ids, context=context):	
            is_tmall_jd = so.partner_id.name
            is_tmall_jd = ( is_tmall_jd.find('TM')>=0 or is_tmall_jd.find('JDI')>=0 )
            user = so.user_id and so.user_id.id or so.create_uid.id	
			
            for pick in so.picking_ids:
                if is_tmall_jd and pick.state != 'done' : pick.move_lines.filtered(lambda r: r.location_id.id != 39).write({'location_id':39})			
                pick.add_followers({'ids':[pick.id], 'user_ids':[user]}, context=context)
                pick.create_uid = user
                if pick.state in ['confirmed'] :
                    statement = "update ir_attachment set res_id=%d, res_model='stock.picking', res_name='%s' where res_id=%d and datas_fname like '%s.xlsx'" % ( pick.id, pick.name, so.id, '%' )
                    cr.execute(statement)					
                    pick.action_assign()
						
                for line in pick.move_lines:					
                    if line.name and line.name.find('RMA')>=0 and line.state != 'done':			
                        line.location_id = 20 # Standby Location ID = 20      
        
        return super(sale_order, self).action_view_delivery(cr, uid, ids, context=None)  
			