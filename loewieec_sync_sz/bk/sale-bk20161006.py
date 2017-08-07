# -*- encoding: utf-8 -*-
from openerp.osv import fields,osv
from openpyxl.reader.excel import load_workbook 
from openerp import tools
from openerp.tools.translate import _
import os
import re

class loewie_carrier(osv.osv):
    _name = "loewie.carrier"  
	
    _columns = {
        'name': fields.char(u'快递公司', required=True),
        'id_tm': fields.char(u'ID Tmall'),
        'id_jd': fields.char(u'ID JD'),	
        'reg_mail_no': fields.char(u'运单号Regex'),		
        'code_tm': fields.char(u'Code Tmall'),		
        'code_jd': fields.char(u'Code JD'),		# 京东平台，对物流公司的编码
        'base_kg':fields.float(u'基础重量',default=1),
        'base_price':fields.float(u'基础价格',default=1),
        'increment_kg':fields.float(u'增量重量',default=1),
        'increment_price': fields.float(u'增量价格',default=1),	
    }
	
class product_tmalljd(osv.osv):
    _name = "product.tmalljd"
    #_inherits = {'product.product': 'product_id'}

    def _get_ean13(self, cr, uid, ids, field_name, arg, context=None):	
        result = {}
        for line in self.pool.get('product.tmalljd').browse(cr, uid, ids, context=context):
            if line.erp_product_id : result[line.id] = line.erp_product_id.ean13 or line.erp_product_id.default_code
        return result		

    def _get_stock(self, cr, uid, ids, field_name, arg, context=None):	
        result = {}
        domain_products = [('location_id','=',38)]		
        quants = self.pool.get('stock.quant').read_group(cr, uid, domain_products, ['product_id', 'qty'], ['product_id'], context=context)	
        quants = dict(map(lambda x: (x['product_id'][0], x['qty']), quants))
		
        for line in self.pool.get('product.tmalljd').browse(cr, uid, ids, context=context):
            id = line.id
            if line.erp_product_id :
                pid = line.erp_product_id.id			
                result[id] = quants.get(pid, 0.0)
            else:
                result[id] = 0			
        return result		
		
    _columns = {
        'erp_product_id': fields.many2one('product.product','ERP Product Name'),
        'erp_ean13': fields.char('ERP_EAN13'), #fields.function(_get_ean13,type='char',string='ERP_EAN13'),
        'erp_stock': fields.float('ERPStock'),#fields.function(_get_stock,type='float',string='ERP库存'),		
        'ec_shop_id': fields.many2one('loewieec.shop', u'店铺'),		
        'ec_num_iid': fields.char(u'淘宝数字编码'),
        'ec_sku_id': fields.char(u'淘宝SKU_ID'),
        'ec_title':fields.char(u'商品标题'),
        'ec_price':fields.float(u'售价'),
        'ec_color':fields.char(u'颜色'),
        'ec_ean13': fields.char(u'条形码'),
        'ec_brand': fields.char(u'品牌'),
        'ec_qty': fields.integer(u'EC数量'),
        'ec_outer_code': fields.char(u'商家外部编码'),		
        'ec_product_name': fields.char(u'产品名称'),	
        'ec_product_id': fields.char(u'EC产品ID'),		
        'ec_num_custom':fields.char(u'海关代码'),	
    }
	
class loewieec_error(osv.osv):
    _name = "loewieec.error"

    _columns = {	
        'shop_id': fields.many2one('loewieec.shop', u'店铺'),
        'name': fields.char(u'错误信息'),
    }
	
class sale_coe(osv.osv):
    _name = "sale.coe"	
	
    _columns = {	
        'sale_id': fields.many2one('sale.order',string='销售单'),	
        'picking_id': fields.many2one('stock.picking',string=u'出货单'),		
        'customer': fields.many2one('res.partner',string=u'客户'),		
        'tmi_jdi_no': fields.char(string=u'电商单号'),		
        'express_no': fields.char(string=u'货运单号'),	
        'expresser': fields.many2one('loewie.carrier',string=u'货运公司'),	
        'pay_way': fields.selection([
            ('we_pay', u'包邮'),
            ('cash_pay', u'现付'),
            ('customer_pay', u'到付'),
            ], string=u'结算方式'),		
        'name': fields.char(string=u'收货人',required=True),	
        'receive_name': fields.char(string=u'收货人old'),		
        'tel': fields.char(string=u'电话'),
        'mobile': fields.char(string=u'手机',required=True),		
        'state': fields.char(string=u'省份'),	
        'city': fields.char(string=u'城市'),	
        'address': fields.char(string=u'地址',required=True),	
        'zip': fields.char(string=u'邮编'),	
        'weight': fields.float(string=u'重量',default=1),		
        'price': fields.float(string=u'快递费',default=6),		
    }
	
    def on_weight_express_change(self, cr, uid, ids, expresser=None, weight=1):
        return	
        if expresser is None: return		
        carrier = self.pool.get('loewie.carrier').browse(cr, uid, [expresser], context={})
        if weight <= carrier.base_kg:
            amount = carrier.base_price
        else:			
            round_weight = int(weight - carrier.base_kg)	
            increment_weight = 	round_weight < (weight - carrier.base_kg) and 1 or 0		
            amount = carrier.base_price + (round_weight + increment_weight) * carrier.increment_price					

        return {'value': {'price': amount}}
		
class sale_order_line(osv.osv):
    _inherit = "sale.order.line"
	
    _columns = {
        'express_id': fields.many2one('sale.coe',string=u'快递信息'),	
        'tmi_jdi_no': fields.char(string=u'电商单号'),
        'pay_time': fields.datetime('PayTime'),	
        'create_time_tmjd': fields.datetime('TM_JD Create Time'),		
    }	

    def copy_sale_order_line(self, cr, uid, ids, context=None): 
        for line in self.pool.get('sale.order.line').browse(cr, uid, ids, context=context):
            line.copy()		
	
class stock_move(osv.osv):
    _inherit = "stock.move"
	
    def _get_express_id(self, cr, uid, ids, field_name, arg, context=None):	
        result = {}
        for move in self.pool.get('stock.move').browse(cr, uid, ids, context=context):
            result[move.id] = move.procurement_id.sale_line_id.express_id.id
        return result	
		
    _columns = {
        #'sale_order_line': fields.function(_get_sale_order_line, type='char',string='Sales Line'),	
        'express_id': fields.function(_get_express_id,type='many2one',relation='sale.coe',string=u'快递信息'),
        'express_id2': fields.many2one('sale.coe',string=u'快递信息'),		
    }	

class stock_picking(osv.osv):
    _inherit = "stock.picking"
			
    def import_orders_from_note(self, cr, uid, ids, context=None):	
        picking_obj = self.pool.get('stock.picking').browse(cr,uid,ids[0],context=context)	
        customer_id = picking_obj.partner_id.id	
        carrier_obj = self.pool.get('loewie.carrier')			
        coe_obj = self.pool.get('sale.coe')		
        lines = [ o.split(u'，') for o in picking_obj.note.split(chr(10))]	

        express_ids = []		
        pay_way = {'we_pay':u'包邮' , 'customer_pay': u'到付', 'cash_pay': u'现付'}		
        for line in lines:
            if len(line)<4: 
                lines.remove(line)		
                continue					
				
            vals = {		
                'picking_id': ids[0],
                'customer': customer_id,				
                'name':line[0].strip(),
                'mobile':line[1].strip(), 					
                'address':line[2].strip(),			
                'zip':line[3].strip(),
                'price':6,				
            }
			
            express_id = coe_obj.search(cr, uid, [('name','=',vals["name"]),('mobile','=',vals['mobile']),('picking_id','=',ids[0])], context=context)	
            express_id = express_id and express_id[0] or 0			
            if not express_id :	
								
                way = len(line)>5 and line[5] or ''	
                way = way.strip()				
                way_erp = ''			
                for key in pay_way.keys():
                    if pay_way[key] == way : way_erp = key
                if way_erp in pay_way.keys(): vals.update({'pay_way':way_erp})					
			
                expresser = line[4] or ''
                carrier_id = carrier_obj.search(cr,uid,[('name','=',expresser.strip())],context=context)
                carrier_id = carrier_id and carrier_id[0] or 0			
                if carrier_id : vals.update({'expresser':carrier_id})			
                express_id = coe_obj.create(cr, uid, vals, context=context)
            express_ids.append(express_id)            				
			
        if len(express_ids) != 1:
            return True

        for move in picking_obj.move_lines:
            move.express_id2 = express_ids[0]		
			
        return True
				
    def view_express_data(self, cr, uid, ids, context=None):	
        stock_picking_obj = self.pool.get('stock.picking').browse(cr,uid,ids[0],context=context)	

        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj.get_object_reference(cr, uid, 'loewieec_sync_sz', 'action_loewieec_salecoe')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]		
        partner_id = stock_picking_obj.partner_id.id
		
        if not stock_picking_obj.sale_id : 
            domain = [('picking_id','=',ids[0]),('express_id2','!=',False)]		# ,('express_id2','!=',False)
            express_ids = self.pool.get('stock.move').read_group(cr, uid, domain, ['express_id2'], ['express_id2'], context=context)
            express_ids = map(lambda x: (x['express_id2'] and x['express_id2'][0]), express_ids)			
            result['domain'] = [('id','in', express_ids)]
            result['res_id'] = express_ids
            result['context'] = {'default_customer':partner_id,'default_picking_id':ids[0]}				
            return result
			
        order_id = 	stock_picking_obj.sale_id.id 		
        sale_order_line_ids = self.pool.get('sale.order.line').search(cr,uid,[('order_id','=',order_id)],context=context)	
        if len(sale_order_line_ids)< 1: return False		
        eids = self.pool.get('sale.order.line').read(cr,uid,sale_order_line_ids,['express_id'],context=context)
        express_ids = [ eid['express_id'] and eid['express_id'][0] for eid in eids ]			
        if len(express_ids) < 1: 			
            raise osv.except_osv(u'stock.picking 错误',u'''没有快递信息''')		
            return False			
	
        sale_coe_obj = self.pool.get('sale.coe')
        for express_obj in sale_coe_obj.browse(cr,uid,express_ids,context=context):
            if not express_obj.picking_id: 
                express_obj.picking_id = ids[0]		

        result['domain'] = [('id','in', express_ids)]
        result['res_id'] = express_ids
        result['context'] = {'default_sale_id':order_id,'default_customer':partner_id,'default_picking_id':ids[0]}	
		
        return result		
	
class sale_order(osv.osv):
    _name = "sale.order"
    _inherit = "sale.order"
        
    _columns = {
        'selected': fields.boolean('Selected'),	
        'shop_id': fields.many2one('loewieec.shop', string=u"EC店铺名", readonly=True),
        'sale_code': fields.char(u'EC单号', readonly=True),				
        'order_state': fields.selection([
            ('WAIT_SELLER_SEND_GOODS', u'等待卖家发货'),
            ('WAIT_BUYER_CONFIRM_GOODS', u'等待买家确认收货'),
            ('TRADE_FINISHED', u'交易成功'),
            ('TRADE_CLOSED', u'交易关闭'),
            ], u'订单状态'),
    }   
	
    def update_waybill_no(self, cr, uid, ids, context=None):
        sale_order_obj = self.pool.get('sale.order').browse(cr,uid,ids[0],context=context)	
        shop = sale_order_obj.shop_id		
        if not shop : return False  

        return shop.set_losgistic_confirm(context=context, salesorder=sale_order_obj)			
		
    def string_refactor(self, name):   
        if not name: return False		
        name = name.replace("/","%")
        name = name.replace("|","%")			
        ll = name.split("-")
        ll = [l.strip() for l in ll]
        ll = "%".join(ll)				
        return ll.replace(" ","%")
		
    def get_express_data(self, cr, uid, ids, context=None):			
		
        sale_coe_obj = self.pool.get('sale.coe')
        express_ids = sale_coe_obj.search(cr,uid,[('sale_id','=',ids[0])],context=context)
        if len(express_ids)<1: return False
		
        note = ""		
        for express in sale_coe_obj.browse(cr,uid,express_ids,context=context):
            if not express.name : continue		
            name = express.name
            express_no = express.express_no or 'none'
            expresser = express.expresser and express.expresser.name or 'none'			
            tmp_str =  name + "," + expresser + "," + express_no + chr(10)		
            note += tmp_str
			
        sale_order_obj = self.pool.get('sale.order').browse(cr,uid,ids[0],context=context)
        note_tmp = sale_order_obj.note	or  '.'	
        sale_order_obj.note = note + note_tmp 
        return True		
		
    def view_express_data(self, cr, uid, ids, context=None):	
        sale_order_obj = self.pool.get('sale.order').browse(cr,uid,ids[0],context=context)		
        if not sale_order_obj : 
            raise osv.except_osv(u'Sale order 错误',u'''请先保存销售单草稿''')	
            return False

        #express_ids = sale_coe_obj.search(cr,uid,[('sale_id','=',ids[0])],context=context)
        sale_order_line_ids = self.pool.get('sale.order.line').search(cr,uid,[('order_id','=',ids[0])],context=context)	
        if len(sale_order_line_ids)< 1: return False		
        eids = self.pool.get('sale.order.line').read(cr,uid,sale_order_line_ids,['express_id'],context=context)
        #if len(eids) < 1: return False		
        express_ids = [ eid['express_id'] and eid['express_id'][0] for eid in eids ]			
		
        customer_id = sale_order_obj.partner_id.id
        sale_coe_obj = self.pool.get('sale.coe')
        if len(express_ids)>0:		
            for express_obj in sale_coe_obj.browse(cr,uid,express_ids,context=context):
                express_obj.sale_id = ids[0]		
                express_obj.customer = customer_id	                		
		
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        result = mod_obj.get_object_reference(cr, uid, 'loewieec_sync_sz', 'action_loewieec_salecoe')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        result['domain'] = [('id','in',express_ids)]
        result['res_id'] = express_ids
        result['context'] = {'default_sale_id':ids[0],'default_customer':customer_id}		
		
        return result		
		
    def import_orders_from_note(self, cr, uid, ids, context=None):	
        sale_order_obj = self.pool.get('sale.order').browse(cr,uid,ids[0],context=context)	
        if sale_order_obj.shop_id or sale_order_obj.partner_id.name in [u'TMI天猫国际', u'天猫乐易成人用品专营店'] :
            return self.import_tmall_consignee_from_note(cr, uid, ids, context=context, order=sale_order_obj)				
			
        if not sale_order_obj : 
            raise osv.except_osv(u'Sale order 错误',u'''请先保存销售单草稿''')	
            return False
        customer_id = sale_order_obj.partner_id.id	
        carrier_obj = self.pool.get('loewie.carrier')			
        coe_obj = self.pool.get('sale.coe')		
        lines = [ o.split(u'，') for o in sale_order_obj.note.split(chr(10))]	

        express_ids = []		
        pay_way = {'we_pay':u'包邮' , 'customer_pay': u'到付', 'cash_pay': u'现付'}		
        for line in lines:
            if len(line)<4: 
                lines.remove(line)		
                continue					
				
            vals = {		
                'sale_id': ids[0],
                'customer': customer_id,				
                'name':line[0].strip(),
                'mobile':line[1].strip(), 					
                'address':line[2].strip(),			
                'zip':line[3].strip(),
                'price':6,				
            }		
            express_id = coe_obj.search(cr, uid, [('name','=',vals["name"]),('mobile','=',vals['mobile']),('sale_id','=',ids[0])], context=context)	
            express_id = express_id and express_id[0] or 0			
            if not express_id :	
								
                way = len(line)>5 and line[5] or ''	
                way = way.strip()				
                way_erp = ''			
                for key in pay_way.keys():
                    if pay_way[key] == way : way_erp = key
                if way_erp in pay_way.keys(): vals.update({'pay_way':way_erp})					
			
                expresser = line[4] or ''
                carrier_id = carrier_obj.search(cr,uid,[('name','=',expresser.strip())],context=context)
                carrier_id = carrier_id and carrier_id[0] or 0			
                if carrier_id : vals.update({'expresser':carrier_id})			
                express_id = coe_obj.create(cr, uid, vals, context=context)
            express_ids.append(express_id)            				
			
        if len(express_ids) != 1:
            return True

        for product in sale_order_obj.order_line:
            product.express_id = express_ids[0]		
			
        return True
		
    def import_tmall_consignee_from_note(self, cr, uid, ids, context=None,order=None):			
        sale_order_obj = order		
        if not sale_order_obj : 
            raise osv.except_osv(u'Sale order 错误',u'''请先保存销售单草稿''')	

        customer_id = sale_order_obj.partner_id.id	
        carrier_obj = self.pool.get('loewie.carrier')			
        coe_obj = self.pool.get('sale.coe')		
        lines = [ o.split(chr(9)) for o in sale_order_obj.note.split(chr(10))]	

        express_ids = {}		
        pay_way = {'we_pay':u'包邮' , 'customer_pay': u'到付', 'cash_pay': u'现付'}		
        for line in lines:
            if len(line)<4: 
                lines.remove(line)		
                continue					
				
            vals = {		
                'sale_id': ids[0],
                'customer': customer_id,
                'tmi_jdi_no': line[0].strip(),			
                'name':line[1].strip(),	
                'mobile':line[3].strip(),				
                'address':line[2].strip(), 	
                #'zip':line[4].strip(),
                'expresser':3,
                'pay_way':'cash_pay',				
                'price':6,				
            }		
            express_id = coe_obj.search(cr, uid, [('name','=',vals["name"]),('mobile','=',vals['mobile']),('sale_id','=',ids[0])], context=context)	
            express_id = express_id and express_id[0] or 0			
            if not express_id :			
                express_id = coe_obj.create(cr, uid, vals, context=context)
            express_ids[vals['tmi_jdi_no']] = express_id            			

        for product in sale_order_obj.order_line:
            tmi_no = product.tmi_jdi_no.strip()		
            if tmi_no in express_ids.keys():		
                product.express_id = express_ids[tmi_no]		
			
        return True
				
    def set_line_express_id(self, cr, uid, ids, context=None):		
        sale_order_obj = self.pool.get('sale.order').browse(cr,uid,ids[0],context=context)	
        express_ids = self.pool.get('sale.coe').search(cr,uid,[('sale_id','=',ids[0])],context=context)
        express_id = len(express_ids)==1 and express_ids[0]	or 0
        if not express_id : return False		
		
        for product in sale_order_obj.order_line:
            product.express_id = express_id		
			
        return True
