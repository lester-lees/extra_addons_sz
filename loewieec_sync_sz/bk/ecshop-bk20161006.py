# -*- encoding: utf-8 -*-
import time
from openerp import tools
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from openerp.tools.translate import _
from openerp.osv import fields,osv

from top import setDefaultAppInfo
from top.api.rest import ItemsOnsaleGetRequest
from top.api.rest import TradesSoldIncrementGetRequest
from top.api.rest import TimeGetRequest
from top.api.rest import TradesSoldGetRequest
from top.api.rest import TradeFullinfoGetRequest
from top.api.rest import ItemSkusGetRequest
from top.api.rest import TradeGetRequest  
from top.api.rest import LogisticsOnlineConfirmRequest
from top.api.rest import LogisticsOfflineSendRequest
from top.api.rest import LogisticsCompaniesGetRequest 
import logging
_logger = logging.getLogger(__name__)

class loewieec_shop(osv.osv):
    _name = 'loewieec.shop'
    _description = u"电商店铺"
   
    _columns = {
        'active':fields.boolean(string='Active',default=False),	
        'tmall_time': fields.datetime(string='TMall Time'),	
        'name': fields.char(u'店铺名称', size=16, required=True),
        'code': fields.char(u'店铺前缀', size=8, required=True, help=u"系统会自动给该店铺的订单编号.客户昵称加上此前缀.通常同一个平台的店铺前缀设置成一样"),
        'platform': fields.selection([('tb', u'淘宝天猫'), ('sb', u'淘宝沙箱'),], string=u'电商平台', required=True, help = u"淘宝、京东等电商平台" ),
        #'categ_id': fields.many2one('product.category', string=u"商品默认分类", required=True),
        'location_id': fields.many2one('stock.location', string=u"店铺库位", required=True),
        'journal_id': fields.many2one('account.journal', string=u"默认销售账簿", required=True),
        'post_product_id': fields.many2one('product.product', string=u"邮费"),
        #'coupon_product_id': fields.many2one('product.product', string=u"优惠减款", required=True),
        'gift_product_id': fields.many2one('product.product', string=u"赠品", ),
        'partner_id': fields.many2one('res.partner',string='Partner', required=True),
        'pricelist_id':fields.many2one('product.pricelist',string='Price List', required=True),		
        'warehouse_id':fields.many2one('stock.warehouse',string='Warehouse', required=True),		
        'appkey': fields.char(u'App Key', ),
        'appsecret': fields.char(u'App Secret', ),
        'sessionkey': fields.char(u'Session Key', ),
        'apiurl': fields.char(u'API URL', ),
        'authurl': fields.char(u'Auth URL', ),
        'tokenurl': fields.char(u'Token URL', ),
      	'products': fields.one2many('product.tmalljd','ec_shop_id',string="Products"),  
        'orders': fields.one2many('sale.order','shop_id',string="Orders"),  		
        'start_modified': fields.datetime(string='Start Modified'),	
        'end_modified': fields.datetime(string='End Modified'),	
        'sync_interval': fields.integer(u'同步最近多少小时的订单',default=24),
        'import_salesorder': fields.many2one('sale.order',u'天猫COE信息的目标订单'),	
        'last_log':fields.text(u'同步信息'),	
        'tmi_state': fields.selection([
            ('WAIT_BUYER_PAY', u'等待买家付款'),
            ('WAIT_SELLER_SEND_GOODS', u'等待卖家发货'),
            ('WAIT_BUYER_CONFIRM_GOODS', u'等待买家确认收货'),
            ('TRADE_FINISHED', u'交易成功'),
            ('TRADE_CLOSED', u'交易关闭'),
            ('TRADE_CLOSED_BY_TAOBAO', '交易被淘宝关闭'),
            ('ALL_WAIT_PAY', u'所有买家未付款的交易'),
            ('ALL_CLOSED', u'所有关闭的交易'),
            ], '订单的天猫订单状态', default='WAIT_SELLER_SEND_GOODS' ),		
    }
	
    def update_waybill_no_tmall(self, cr, uid, ids, context=None): # 	 
        port = 80
        shop = self.browse(cr, uid, ids[0], context = context)
        setDefaultAppInfo(shop.appkey, shop.appsecret)
        req = LogisticsOfflineSendRequest(shop.apiurl,port)
        req.company_code="EMS"
	
        sale_id = shop.import_salesorder.id
        domain = [('order_id','=',sale_id)]		
        coe_tmino = self.pool.get('sale.order.line').read_group(cr, uid, domain, ['tmi_jdi_no','coe_no'], ['product_id'], context=context)
        resp= req.getResponse(shop.sessionkey)
        companies = resp.get('logistics_companies_get_response').get('logistics_companies', False)
        comp_list = companies.get('logistics_company',False)
		
        return True		
		
    def get_losgistic_company_code(self, cr, uid, ids, context=None):	# 		
 
        port = 80
        shop = self.browse(cr, uid, ids[0], context = context)
        setDefaultAppInfo(shop.appkey, shop.appsecret)
        req = LogisticsCompaniesGetRequest(shop.apiurl,port)
        req.fields="id,code,name,reg_mail_no"
        req.order_mode="all"		
			
        resp= req.getResponse(shop.sessionkey)
        companies = resp.get('logistics_companies_get_response').get('logistics_companies', False)
        comp_list = companies.get('logistics_company',False)

        carrier_obj = self.pool.get('loewie.carrier')		
        for comp in comp_list:
            comp_ids = carrier_obj.search(cr,uid,[('name','=',comp.get('name'))],context=context)
            comp_ids	= comp_ids and comp_ids[0] or 0
            if not comp_ids :
                vals = 	{'name':comp.get('name'),'id_tm':str(comp.get('id')),'code_tm':comp.get('code'),'reg_mail_no':comp.get('reg_mail_no')}		
                carrier_obj.create(cr,uid,vals,context=context)			

        return True   	

    def set_losgistic_confirm(self, cr, uid, ids, context=None, salesorder=None):	# 		
 
        port = 80
        shop = self.browse(cr, uid, ids[0], context = context)
        setDefaultAppInfo(shop.appkey, shop.appsecret)
        req = LogisticsOnlineConfirmRequest(shop.apiurl,port)
		
        tmi_jdi_list = {}		
        for line in salesorder.order_line:	
		
            tmi_jdi_no,coe_no,is_sent = line.tmi_jdi_no,line.coe_no, line.logistic_sent
            tmi_jdi_no = tmi_jdi_no.strip()	
            coe_no = coe_no and coe_no.name.strip() or False			
            if not tmi_jdi_no or not coe_no or is_sent: continue	
            tmi_jdi_list[tmi_jdi_no] = coe_no
        
        is_sent_list = []		
        for tmi_jdi_num in tmi_jdi_list.keys():		
            req.tid = tmi_jdi_num
            req.out_sid = tmi_jdi_list[tmi_jdi_num]			
            resp= req.getResponse(shop.sessionkey)
            is_ok = resp.get('logistics_online_confirm_response').get('shipping', False).get('is_success')
			
            if is_ok :	 
                is_sent_list.append(tmi_jdi_num)
				
        for line3 in salesorder.order_line:				
            tmi_jdi = line3.tmi_jdi_no
            if tmi_jdi.strip() in is_sent_list:
                line3.logistic_sent = True	
				
        return True		
			       
    def search_product_sku(self, cr, uid, ids, num_iids=None, context=None):

        port = 80
        shop = self.browse(cr, uid, ids[0], context = context)
        setDefaultAppInfo(shop.appkey, shop.appsecret)
        req = ItemSkusGetRequest(shop.apiurl,port)
        req.fields="sku_id, num_iid, properties, price, status, memo, properties_name, outer_id,quantity,barcode,change_prop,sku_spec_id,extra_id"
        
        if not num_iids : 
            req.num_iids = shop.tokenurl			
        else: 
            req.num_iids = num_iids
			
        resp= req.getResponse(shop.sessionkey)
        skus = resp.get('item_skus_get_response').get('skus', False).get('sku',False)

        return skus

    def create_product_tmalljd_nosku(self, cr, uid, ids, item, context=None):
        product_tmalljd_objs = self.pool.get('product.tmalljd') 	
        product_vals = {'ec_shop_id':ids[0],'ec_price':float(item.get('price')),'ec_qty':item.get('num'),'ec_outer_code':item.get('outer_id'), 'ec_num_iid':str(item.get('num_iid')),'ec_title':item.get('title') } 	
		
        pids = product_tmalljd_objs.search( cr, uid, [('ec_num_iid', '=', str(item.get('num_iid'))),('ec_shop_id','=',ids[0])], context=context)		
        if len(pids) < 1: 			
                product_tmalljd_objs.create(cr, uid, product_vals)  
        return True				
		
    def search_product(self, cr, uid, ids, context=None ):	
        this = self.browse(cr, uid, ids, context=context)[0]	
        res = self._search_product(cr, uid, ids, product_name = None, start_modified=this.start_modified, end_modified=this.end_modified, context=context)

        if len(res) < 1: return 
        product_tmalljd_objs = self.pool.get('product.tmalljd') 
        num_iids = [str(o['num_iid']) for o in res]
        titles = {}
        for item in res:
            titles[str(item.get('num_iid'))] = item.get('title') 
			
        skus_list = []	
        skus_list2 = []		
        interval = 40
        start = end = 0
        final_end = len(num_iids)
		
        while start < final_end:
            if start + interval > final_end	: end = final_end
            else: end = start + interval	
            sub_list = num_iids[start:end]			
            sub_num_iids = ",".join(sub_list)			
            skus_list +=  self.search_product_sku(cr, uid, ids, num_iids=sub_num_iids, context=context)            			
            start = end	
			
        for sku_item in skus_list:
            str_num_iid = str(sku_item.get('num_iid'))		
            if str_num_iid not in skus_list2:
                skus_list2.append( str_num_iid )		
				
        no_sku_num_iids = []		
        for item in res:
            if str(item["num_iid"]) not in skus_list2: 
                self.create_product_tmalljd_nosku(cr,uid,ids,item,context=context)			
			
        for sku in skus_list:
		
            product_vals = {'ec_shop_id':this.id,'ec_price':float(sku.get('price')),'ec_qty':sku.get('quantity'),'ec_outer_code':sku.get('outer_id'),'ec_sku_id':str(sku.get('sku_id')) } #, 'ec_ean13':sku.get('barcode','')}	
            num_iid = str(sku['num_iid'])			
            product_vals['ec_num_iid'] = num_iid	
            product_vals['ec_title'] = titles[num_iid]			
            pids = product_tmalljd_objs.search( cr, uid, [('ec_sku_id', '=', str(sku['sku_id'])),('ec_shop_id','=',this.id)], context=context)		
            #if len(pids)>0: 
            #    product_tmalljd_objs.write(cr,uid,pids[0],product_vals)	            				
            #else:
            if len(pids) < 1: 			
                product_tmalljd_objs.create(cr, uid, product_vals)	
			
        return True	

    def _search_product(self, cr, uid, ids, product_name = None, start_modified = None, end_modified = None, context=None):
        """
        1) 按商品名称，商品修改时间搜索店铺商品
        2) start_modified、end_modified 都是UTC时间，需要加上8小时传给电商平台
        """
        shop_id = self.browse(cr, uid, ids[0], context= context)
        setDefaultAppInfo(shop_id.appkey, shop_id.appsecret)
        req = ItemsOnsaleGetRequest(shop_id.apiurl, 80)
        req.fields="approve_status,num_iid,title,nick,type,num,list_time,price,modified,delist_time,outer_id"		
        if product_name:
            req.q = product_name
        
        req.page_no = 1
        req.page_size = 100
        total_get = 0
        total_results = 100
        res = []
        while total_get < total_results:
            resp= req.getResponse(shop_id.sessionkey)
            total_results = resp.get('items_onsale_get_response').get('total_results')
		
            if total_results > 0:
                res += resp.get('items_onsale_get_response').get('items').get('item')
            total_get += req.page_size			
            req.page_no = req.page_no + 1
        #
        # 时间需要减去8小时
        for r in res:
            r['modified'] = (datetime.strptime(r['modified'],'%Y-%m-%d %H:%M:%S',) - timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
        return res
      				
    def create_order(self, cr, uid, ids, trade, context=None):	
        order_obj = self.pool.get('sale.order')
        shop = self.browse(cr, uid, ids[0], context = context)	
        partner_id = shop.partner_id.id		
        gift_product_id = shop.gift_product_id.id		
        shop_code = shop.code		
        order_val = {
            'name': "%s_%s" % ( shop.code, self.pool.get('ir.sequence').get(cr, uid, 'sale.order') or '/' ),
            'shop_id': shop.id,
            'date_order':  datetime.now(),      #订单支付时间 trade.get('pay_time') or 
            'create_date': datetime.now(),  #trade.get('created'),       #订单创建时间
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
				   
        product_null_id = self.pool.get('product.product').search(cr, uid, [('name_template','=',u'刷单空包')], context=context )
        product_null_id = product_null_id and product_null_id[0] or 0
        if not product_null_id: 
            raise osv.except_osv(u'ERP错误',u'''ERP中不存在 '刷单空包' 产品!''') 		

        order_lines = []	
        product_tmalljd_obj = self.pool.get('product.tmalljd')		
        for order in trade:  
            tid = str(order['tid'])	
            is_shuadan = order['is_jaycee'] or order['is_kevin'] or False			
            if shop_code  == 'TMI' and not is_shuadan and not order['is_sz']: continue  # TMI天猫国际的 非代发、非深圳发货 单 略过
            jaycee_vals = {	
                'product_id': is_shuadan and product_null_id or gift_product_id,			
                'product_uos_qty': 1,
                'tmi_jdi_no': tid,			
                'product_uom': 1,
                'price_unit': 0,
                'product_uom_qty': 1,
                'name':'-',
                'delay': 7,
                'discount': 0,
            }	
            order_val['order_line'].append((0, 0, jaycee_vals))				
            if is_shuadan : continue	
			
            lines = order["orders"]["order"]			
            for line in lines:				
                order_lines.append(line)									
				
        for order_line in order_lines:  
            tid = str ( order_line.get('tid') or order_line.get('oid') )
            qty = order_line.get('num')			
            line_vals = {			
                'product_uos_qty': qty,
                'product_id': 1,
                'tmi_jdi_no': tid,			
                'product_uom': 1,
                'price_unit': float(order_line.get('payment',0))/qty or float(order_line.get('total_fee',0))/qty,
                'product_uom_qty': qty,
                'name':'-',
                'delay': 7,
                'discount': 0,
            }			
            product_tmalljd_ids = product_tmalljd_obj.search(cr, uid, [('ec_sku_id','=',order_line.get('sku_id') or order_line.get('num_iid'))], context = context )
            if not product_tmalljd_ids:
                syncerr = u"订单导入错误: 匹配不到商品。tid=%s, 商品num_iid=%s, outer_sku_id=%s, sku_id=%s " % ( tid, order_line.get('num_iid', ''),  order_line.get('outer_sku_id', ''), order_line.get('sku_id', '') )
                raise osv.except_osv(u"ERP中不存在以下产品", syncerr)

            product_tmalljd_obj = self.pool.get('product.tmalljd').browse(cr, uid, product_tmalljd_ids[0], context = context)
            product_id = product_tmalljd_obj.erp_product_id.id
            #uom_id = product_tmalljd_obj.erp_product_id.uom_id.id			
            #添加订单明细行			
            line_vals.update({'product_id': product_id } )
            order_val['order_line'].append( (0, 0, line_vals) ) 
			
        note = shop.last_log or ""			
        if len(order_val['order_line']) < 1: 	
            shop.last_log = u'''时间:%s, 天猫后台无有效订单.''' % self.get_datetime_now() + chr(10) + note		
            return False					
			
        order_id = order_obj.create(cr, uid, order_val, context = context)	
        return order_id

    def search_orders_sent_on_tmall(self, cr, uid, ids, context=None):
        return self.search_orders_by_created_time(cr, uid, ids, context=context, status = ['WAIT_BUYER_CONFIRM_GOODS','WAIT_SELLER_SEND_GOODS'])	

    def search_orders_seller_memo(self, cr, uid, ids, context=None, orders = {}):
        port = 80
        shop = self.browse(cr, uid, ids[0], context = context)
        partner_id = shop.partner_id.id		
        setDefaultAppInfo(shop.appkey, shop.appsecret)
        req = TradeGetRequest(shop.apiurl,port) 		
        req.fields="seller_memo"
		
        for order in orders:            	
            req.tid = order["tid"]
            resp= req.getResponse(shop.sessionkey)
            seller_memo = resp.get('trade_get_response','').get('trade','').get('seller_memo','')
            order['is_jaycee'] = seller_memo.find(u'jaycee订单') >= 0		
            order['is_kevin'] = seller_memo.find(u'kevin订单') >= 0	
            order['is_sz'] = seller_memo.find(u'深圳发货') >= 0
			
        return orders		
		
    def search_orders_by_created_time(self, cr, uid, ids, context=None, status = []):
        port = 80
        shop = self.browse(cr, uid, ids[0], context = context)
        partner_id = shop.partner_id.id		
        setDefaultAppInfo(shop.appkey, shop.appsecret)
        req = TradesSoldGetRequest(shop.apiurl,port) 
		
        req.fields="sid,tid,receiver_name,receiver_state,receiver_city,receiver_district,receiver_address, receiver_zip,receiver_mobile,receiver_phone,orders.num,orders.store_code,orders.num_iid,orders.sku_id,orders.oid, orders.total_fee,orders.payment,orders.outer_sku_id"
        req.type = "instant_trade,auto_delivery,guarantee_trade,tmall_i18n"		
        hours_interval = shop.sync_interval
        if hours_interval : hours_interval -= 8
        else: hours_interval = 16		
        req.start_created = (datetime.now() - timedelta(hours=hours_interval)).strftime('%Y-%m-%d %H:%M:%S')					
        req.end_created = (datetime.now()+ timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')   
		
        res = []
        if len(status) < 1: status.append( shop.tmi_state or 'WAIT_SELLER_SEND_GOODS')
		
        for order_status in status :
            req.status = order_status		
            req.page_no = 1
            req.page_size = 100
            total_get = 0
            total_results = 100
            while total_get < total_results:
                resp= req.getResponse(shop.sessionkey)
                trades = resp.get('trades_sold_get_response').get('trades', False)
                total_results = resp.get('trades_sold_get_response').get('total_results')
                _logger.info("Jimmy total_results :%d" % total_results)				
                if total_results > 0:
                    res += trades.get('trade')
                total_get += req.page_size
                req.page_no = req.page_no + 1
	
        if total_results < 1:
            shop.last_log = u"在%d小时内没有状态：%s 的订单可下载" % (shop.sync_interval, shop.tmi_state)
            return True			
	
        orders = self.remove_duplicate_tmi_jdi_no(cr, uid, ids, res, shop, context=context)	
        marked_orders = self.search_orders_seller_memo(cr, uid, ids, context,orders)		
        order_id = self.create_order(cr, uid, ids, marked_orders, context = context )
        if order_id : shop.import_salesorder = order_id
        return order_id

    def remove_duplicate_tmi_jdi_no(self, cr, uid, ids, orders, shop, context=None):
        statement = "select tmi_jdi_no from sale_order_line where state not in ('cancel','draft') group by tmi_jdi_no"
        cr.execute(statement)
        exist_tmi_jdi_no = []
        res = []	
        last_log = []
		
        for item in cr.fetchall():
        	exist_tmi_jdi_no.append(item[0])
      			
        for order in orders:            
            if str(order["tid"]) not in exist_tmi_jdi_no:
                res.append(order)
            else:
                last_log.append( str(order["tid"]) )
        if len(last_log) > 0:
            shop.last_log = u"以下电商单号ERP中已存在,所以此次未导入(%s): " % self.get_datetime_now() + chr(10) + ",".join(last_log) + chr(10)
        return res			
		