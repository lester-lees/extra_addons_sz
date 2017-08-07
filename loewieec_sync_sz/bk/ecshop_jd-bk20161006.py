# -*- encoding: utf-8 -*-
from openerp.osv import fields,osv
from openerp.tools.translate import _
import json
from jdapi.WaresListGetRequest import WaresListGetRequest
from jdapi.WaresListingGetRequest import WaresListingGetRequest
from jdapi.OrderSearchRequest import OrderSearchRequest
from datetime import datetime, timedelta
import xmlrpclib
import logging
_logger = logging.getLogger(__name__)

							
class loewieec_jdshop(osv.osv):
    _inherit = 'loewieec.shop'

    _columns = {
        'sz_sale_id': fields.integer( string='SZ Sales ID',readonly=True,default=0),
        'sz_sale_order':fields.char(string=u'深圳ERP订单',readonly=True),		
    }	

    def get_datetime_now(self):
        return (datetime.now() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')	
    	
    def clean_jdi_hk_orders(self, cr, uid, ids, orders, shop, context=None):
        statement = "select tmi_jdi_no from sale_order_line where tmi_jdi_no is not Null and state not in ('cancel','draft') group by tmi_jdi_no"
        cr.execute(statement)
        exist_tmijdi_no = []
        jaycee_list = []
        sz_list = []		
        last_log = []
        last_log_sz = []
        last_log_jaycee = []		
		
        for item in cr.fetchall():
        	exist_tmijdi_no.append(item[0])

        for order in orders:  
            if str(order["order_id"]) in exist_tmijdi_no :		
                last_log.append( str(order["order_id"]) )				
                continue				
				
            remark = order.get('vender_remark')		
            if remark.find(u'jaycee订单') >= 0:
                order['is_jaycee'] = True			
                jaycee_list.append(order)
                last_log_jaycee.append( str(order["order_id"]) )				
                continue				

            if remark.find(u'深圳发货') >= 0:
                sz_list.append(order)
                last_log_sz.append( str(order["order_id"]) )				
                continue						
				
        note = shop.last_log or ""		
        if len(last_log) > 0:
            note += 	u"重复订单：" + chr(10) + ",".join(last_log) + chr(10)
        if len(last_log_sz) > 0:			
            note += u"深圳订单：" + chr(10) + ",".join(last_log_sz) + chr(10)
        if len(last_log_jaycee) > 0:			
            note += u"Jaycee订单：" + chr(10) + ",".join(last_log_jaycee) + chr(10)			
        if last_log or last_log_sz or last_log_jaycee : shop.last_log =  self.get_datetime_now() + chr(9) + note
			
        return jaycee_list, sz_list	
		
    def import_orders_from_jd(self, cr, uid, ids, context=None):	
        shop_id = self.browse(cr, uid, ids[0], context= context)
		
        req = OrderSearchRequest(shop_id.apiurl, 443, shop_id.appkey, shop_id.appsecret)
        		
        req.optional_fields = 'order_id,order_payment,order_state,vender_remark,consignee_info,item_info_list,payment_confirm_time,waybill,logistics_id'
		
        req.page_size = 20	
        req.page = 1  	
        req.dateType = 1		
        req.sortType = 1		
        req.order_state = 'WAIT_SELLER_STOCK_OUT,WAIT_SELLER_DELIVERY'	

        ctx_start_time = context.get('start_time',False)		
        ctx_start_time = ctx_start_time and ( datetime.strptime(ctx_start_time, '%Y-%m-%d %H:%M:%S') + timedelta(hours=8) ) 		
		
        ctx_end_time = context.get('end_time',False)	# datetime.strptime(string, "%Y-%m-%d-%H")
        ctx_end_time = ctx_end_time and datetime.strptime(ctx_end_time, '%Y-%m-%d %H:%M:%S') + timedelta(hours=8) 
        req.end_date = ctx_end_time and ctx_end_time.strftime('%Y-%m-%d %H:%M:%S') or self.get_datetime_now()	
		
        hours_interval = shop_id.sync_interval
        if not hours_interval : hours_interval = 24
		
        req.start_date = ctx_start_time or (ctx_end_time and (ctx_end_time - timedelta(hours=hours_interval)).strftime('%Y-%m-%d %H:%M:%S') ) or (datetime.now() - timedelta(hours=hours_interval-8)).strftime('%Y-%m-%d %H:%M:%S')			
		
        order_total = 100
        total_get = 0		
        order_info_list = []		
        while total_get < order_total :		
            resp= req.getResponse(shop_id.sessionkey or shop_id.access_token)
            order_total = resp.get('order_search_response').get('order_search').get('order_total')            			
			
            if order_total > 0:
                order_info_list += resp.get('order_search_response').get('order_search').get('order_info_list')	
				
            total_get += req.page_size			
            req.page = req.page + 1				
		
        jaycee_list, sz_list = self.clean_jdi_hk_orders(cr, uid, ids, order_info_list, shop_id, context=context)
        self.create_order_for_jd(cr, uid, ids, jaycee_list + sz_list, context=context)				
	
    def create_order_for_jd(self, cr, uid, ids, orders, context=None):
        shop = self.browse(cr, uid, ids[0], context = context)
        order_obj = self.pool.get('sale.order')
        partner_id = shop.partner_id.id		
        gift_product_id = shop.gift_product_id.id		
        if not gift_product_id : raise osv.except_osv(u"请先设置赠品",u'''没有赠品！！！''')		
        order_val = {
            'name': "%s_%s" % ( shop.code, self.pool.get('ir.sequence').get(cr, uid, 'sale.order') or '/' ),
            'shop_id': shop.id,
            'date_order':  datetime.now().strftime('%Y-%m-%d %H:%M:%S')	,      #订单支付时间 trade.get('pay_time') or 
            'create_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')	,  #trade.get('created'),       #订单创建时间
            'partner_id': partner_id,
            'partner_invoice_id': partner_id, 			
            'partner_shipping_id': partner_id,
            'warehouse_id': shop.warehouse_id.id,
            'pricelist_id': shop.pricelist_id.id,
            'company_id': 1,			
            'all_discounts': 0,
            'picking_policy': 'direct',
            'state':'draft',		
            'user_id': uid, 			
            'order_policy': 'picking',
            'client_order_ref': u'Loewieec_sync Generated',			
            'order_line': [],
        }	
		
        order_lines = []					
        product_obj = self.pool.get('product.product')
        coe_obj = self.pool.get('sale.coe')	
        express = {}		
        null_product_id = product_obj.search(cr,uid,[('name_template','=',u'刷单空包')],context=context)
        null_product_id = null_product_id and null_product_id[0] or 0		
        if not null_product_id : raise osv.except_osv(u"无法找到产品-刷单空包",u'''ERP中 无法找到产品-刷单空包''')		
        for order in orders:	
            order_jd_no = order.get('order_id')		
            consignee = order.get('consignee_info')		
            #address = "%s %s %s" % (consignee.get('province'),consignee.get('city'),consignee.get('full_address'))
            vals = {	# 为每个收件人创建COE 条目 					
                'name':consignee.get('fullname'),
                'mobile':consignee.get('mobile'),
                'tmi_jdi_no':order_jd_no,			
                'address':consignee.get('full_address'), 
                'tel':consignee.get('telephone'),
                'pay_way':'cash_pay',	
                'expresser': 1,				 
            }
            express_id = coe_obj.search(cr,uid, [('name','=',vals['name']),('mobile','=',vals['mobile']),('tmi_jdi_no','=',order_jd_no)],context=context )   #先查找是否已经创建
            express_id = express_id and express_id[0] or 0			
            if not express_id :			
                express_id = coe_obj.create(cr,uid,vals,context=context)	
            vals["id"] = express_id	           	
            express[vals["mobile"]]	= vals
			
            gift_vals = {	  # 添加 赠品行		
                'product_uos_qty': 1,
                'product_id': order['is_jaycee'] and null_product_id or gift_product_id,
                'tmi_jdi_no': order_jd_no,
                'express_id': express_id,				
                'product_uom': 1,
                'price_unit': 0,
                'product_uom_qty': 1,
                'name': '-',
                'delay': 7,
                'discount': 0,
            }		
		
            order_val['order_line'].append( (0, 0, gift_vals) )	
            if order['is_jaycee'] : continue	
			
            for order_line in order['item_info_list']:		
                line_vals = {			
                    'product_uos_qty': order_line.get('item_total'),
                    'product_id': 1,
                    'tmi_jdi_no': order_jd_no,	
                    'express_id': express_id,					
                    'product_uom': 1,
                    'price_unit': 1,
                    'product_uom_qty': order_line.get('item_total'),
                    'name':'-',
                    'delay': 7,
                    'discount': 0,
                    'price_unit': float(order_line.get('jd_price'))/int(order_line.get('item_total')),					
                }			
                product_tmalljd_ids = self.pool.get('product.tmalljd').search(cr, uid, [('ec_sku_id','=',order_line.get('sku_id') or order_line.get('ware_id'))], context = context )
            
                #如果没有匹配到产品，报同步异常  coe_lines
                if not product_tmalljd_ids:
                    syncerr = u"ERP中不存在以下产品: order_id=%s, ware_id=%s, sku_id=%s " % ( order_jd_no, order_line.get('ware_id', ''),  order_line.get('sku_id', '') )
                    self.pool.get('loewieec.error').create(cr, uid, {'name':syncerr, 'shop_id':shop.id }, context = context )
                    raise osv.except_osv(u"ERP中不存在以下产品",u'''%s''' % order_line.get('sku_name'))

                product_tmalljd_obj = self.pool.get('product.tmalljd').browse(cr, uid, product_tmalljd_ids[0], context = context)
                product_id = product_tmalljd_obj.erp_product_id.id			
	
                line_vals.update({'product_id': product_id  } )
                order_val['order_line'].append( (0, 0, line_vals) ) 
				
        note = shop.last_log or ""			
        if len(order_val['order_line']) < 1: 	
            shop.last_log = u'''时间:%s,JDI 后台无有效深圳代发订单及Jaycee订单.''' % self.get_datetime_now() + chr(10) + note		
            return True				
						
        order_id = order_obj.create(cr, uid, order_val, context = context)			
        shop.import_salesorder = order_id
        return order_id
	
    def get_jd_access_token(self, cr, uid, ids, context=None):
        shop_id = self.browse(cr, uid, ids[0], context= context)	
        url = 'https://oauth.jd.com/oauth/authorize?response_type=code&client_id=%s&redirect_uri=%s' % (shop_id.appkey, shop_id.authurl)	
        return {'type':'ir.actions.act_url', 'url':url, 'target':'new'}	
		
    def search_jd_wares(self, cr, uid, ids, context=None):		
        shop_id = self.browse(cr, uid, ids[0], context= context)
        product_tmalljd_objs = self.pool.get('product.tmalljd')
			
        req = WaresListGetRequest(shop_id.apiurl, 443, shop_id.appkey, shop_id.appsecret)	
        req.fields = 'ware_id,skus,cid,brand_id,vender_id,shop_id,ware_status,title,item_num,upc_code,market_price,stock_num,status,weight,shop_categorys,property_alias'
		
        ware_list = self.get_all_ware_ids(cr, uid, ids, context=context)
        if len(ware_list) < 1: return 
        ware_id_list = [str(o['ware_id']) for o in ware_list]  
        ware_info_list = []		
	
        interval = 10
        start = end = 0
        final_end = len(ware_id_list)
		
        while start < final_end:
            if start + interval > final_end	: end = final_end
            else: end = start + interval	
            sub_list = ware_id_list[start:end]			
            sub_num_iids = ",".join(sub_list)			           			
            start = end	
        		
            req.ware_ids = sub_num_iids		
            resp= req.getResponse(shop_id.sessionkey or shop_id.access_token)
            wares = resp.get('ware_list_response').get('wares')			
            if len(wares)>0 :ware_info_list +=  wares    

        for ware in ware_info_list :
	
            product_vals = {'ec_shop_id':shop_id.id,'ec_num_iid':str(ware['ware_id']), 'ec_title':ware["title"], 'ec_outer_code':ware.get('item_num') }		
            
            for sku_item in ware['skus'] :			
                pids = product_tmalljd_objs.search( cr, uid, [('ec_sku_id', '=', str(sku_item.get('sku_id'))),('ec_shop_id','=',shop_id.id)], context=context)		
                if len(pids) > 0: continue
                product_vals.update({'ec_sku_id': str(sku_item.get('sku_id')),'ec_price':float(sku_item.get('market_price')),'ec_qty':sku_item.get('stock_num'), 'ec_color':sku_item.get('color_value')})				
                product_tmalljd_objs.create(cr, uid, product_vals)		
	
    def get_all_ware_ids(self, cr, uid, ids, context=None):	
        shop_id = self.browse(cr, uid, ids[0], context= context)
        req = WaresListingGetRequest(shop_id.apiurl, 443, shop_id.appkey, shop_id.appsecret)
        req.page_size = 100	
        req.page = 1		
        cids = ['1502','1504','1505','12610','12609']		
        req.fields = 'ware_id,cid'
        ware_list = []		
        for cid in cids :		
            req.cid = cid		
            resp= req.getResponse(shop_id.sessionkey or shop_id.access_token)
            ware_infos = resp.get('ware_listing_get_response')
            ware_infos = ware_infos.get('ware_infos')			
            if len(ware_infos)>0 :  ware_list += ware_infos
			
        return ware_list			