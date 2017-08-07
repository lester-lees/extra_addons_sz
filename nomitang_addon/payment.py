# -*- coding: utf-8 -*-
import logging
from openerp import SUPERUSER_ID, models, fields
from openerp.osv import orm
from openerp.tools import float_compare
from datetime import datetime, timedelta
import xmlrpclib
import urllib
import random
_logger = logging.getLogger(__name__)

class product_template(models.Model):
    _inherit = "product.template"
    sugguest_product_ids = fields.Many2many('product.product','product_sugguest_rel','src_id','dest_id', string='Suggest Products', help='Appear on the shopping cart')	
	
class BlogPost(models.Model):
    _inherit = "blog.post"
	
    image = fields.Binary(string='Image')	
    content_copy = fields.Text(string='Content Source')	
	
    def copy_source_to_context(self, cr, uid, ids, context=None):
        cr.execute('update blog_post set content = content_copy where id=%d' % ids[0])
        return True	
		
class SaleOrder(models.Model):
    _inherit = "sale.order"

    #remote_hk_id = fields.Integer(string='Remote Sale Id', readonly=True)	
    is_created_order_in_hkerp = fields.Boolean(string='Is Created Order In HK-ERP?', readonly=True, copy=False)
    	
    def create_hkerp_salesorder(self, cr, uid, ids, context=None): 
        order_id = self.pool.get('payment.transaction').create_hkerp_salesorder(cr,uid,0,context) 	
        if 	order_id :
            self.pool.get('sale.order').write(cr, uid, ids, {'is_created_order_in_hkerp':True}, context=context)		
		
    def _cart_accessories(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids, context=context):
            s = set(j.id for l in (order.website_order_line or []) for j in (l.product_id.sugguest_product_ids or []) if j.website_published)
            s -= set(l.product_id.id for l in order.order_line)
            product_ids = random.sample(s, min(len(s), 3))
            return self.pool['product.product'].browse(cr, uid, product_ids, context=context)	
			
	
class payment_transaction(orm.Model):
    _inherit = 'payment.transaction'
	
    _db = "LoewieHK"	
    _pwd = "LoewieNomitang321"
    _userid = 28	#user: NT_Sync
    _peer_company = u'深圳市乐易保健用品有限公司'
    _company = 	u"深圳市乐易保健用品有限公司"
    _peer_url = "http://leyi.fortiddns.com:8070/xmlrpc/object"	
    #_peer_url = "http://61.244.238.57:8069/xmlrpc/object"	
    #_peer_url = "http://192.168.0.250:8069/xmlrpc/object"	
	
    def query_product_id_by_ean13(self, ean13=None, default_code=None):
        my_proxy = xmlrpclib.ServerProxy(self._peer_url)	
		
        if ean13 : 
            obj_ids = my_proxy.execute(self._db, 28, self._pwd, 'product.product', 'search', [('ean13','=',ean13)] )			
        elif default_code : 
            obj_ids = my_proxy.execute(self._db, 28, self._pwd, 'product.product', 'search', [('default_code','=',default_code)] )	
		
        obj_id = obj_ids and obj_ids[0] or 0  
        return obj_id

    def query_pricelist_by_currency(self, currency):
        my_proxy = xmlrpclib.ServerProxy(self._peer_url)	
		
        obj_ids = my_proxy.execute(self._db, self._userid, self._pwd, 'res.currency', 'search', [('name','=',currency)] )			
        obj_id = obj_ids and obj_ids[0] or 0 
        if not obj_id : return 0
		
        obj_ids = my_proxy.execute(self._db, self._userid, self._pwd, 'product.pricelist', 'search', [('active','=',True),('currency_id','=',obj_id),('type','=','sale')] )			
        obj_id = obj_ids and obj_ids[0] or 0  
        return obj_id
	
    def query_partner(self, partner):
        my_proxy = xmlrpclib.ServerProxy(self._peer_url)	
        obj_ids = my_proxy.execute(self._db, 28, self._pwd, 'res.partner', 'search', [('phone','=',partner.phone),('name','=',partner.name),('email','=',partner.email)] )			
        return obj_ids and obj_ids[0] or 0  
		
    def create_hkerp_customer(self,cr,uid,ids,partner):
        my_proxy = xmlrpclib.ServerProxy(self._peer_url)			
        partner_vals = {	
            'parent_id': 643,		
            'name': partner.name,
            'phone': partner.phone or '',
            'street': partner.street or '',
            'street2': partner.street2 or '',			
            'mobile': partner.mobile or '',	
            'city': partner.city or '',			
            'zip': partner.zip or '',
            'email': partner.email or '',			
            'type': 'delivery',			
            'is_company': False,
            'customer': True,
            'supplier': False,		
            'section_id':9,	  # 9 NT Website,   3		
            'ref':'Nomi Tang Direct',			
        }  
        if partner.country_id and partner.country_id.id :			
            partner_vals.update({'country_id':partner.country_id.id})			
        if partner.state_id and partner.state_id.id: 
            partner_vals.update({'state':partner.state_id.id})
			
        return my_proxy.execute(self._db, self._userid, self._pwd, 'res.partner', 'create', partner_vals )
		
    def create_hkerp_salesorder(self, cr, uid, ids, context=None):  
        #_logger.info('Jimmy(nomitang_addon) - enter create_hkerp_salesorder') 	
		
        model1 = "sale.order"			
        method = "create"		
        my_proxy = xmlrpclib.ServerProxy(self._peer_url)
        sale_id = context.get('sale_id',False)

        if not sale_id :		
            nt_order = self.browse(cr,uid,ids[0],context=context).sale_order_id
        else:
            nt_order = self.pool.get('sale.order').browse(cr,uid,[sale_id],context=context)	

        #from_currency = nt_order.pricelist_id.currency_id
        #to_currency = nt_order.company_id.currency_id			
        #amount = self.pool.get('res.currency')._compute(cr, uid, from_currency, to_currency, nt_order.amount_total, context=context)
        #params = urllib.urlencode({'amount': amount, 'tracking': nt_order.name, 'transtype': 'sale', 'merchantID':'69694'})	
        #url = "https://shareasale.com/sale.cfm?%s" % params		
        #f = urllib.urlopen(url)
        #f.read()		
        #_logger.info(url)	
		
        #partner_objs = self.pool.get('res.partner')	
        partner = nt_order.partner_id
        partner_id = self.query_partner(partner)		
        if not partner_id : partner_id = self.create_hkerp_customer(cr,uid,ids,partner)

        if not partner_id: return False		
		
        partner_shipping_id = partner_id
        if nt_order.partner_id.id != nt_order.partner_shipping_id.id :		
            partner_shipping_id = self.query_partner(nt_order.partner_shipping_id) 		
            if not partner_shipping_id : partner_shipping_id = self.create_hkerp_customer(cr,uid,ids,nt_order.partner_shipping_id)	
			
        pricelist_id = self.query_pricelist_by_currency(nt_order.pricelist_id.currency_id.name)	
        if not pricelist_id : return False
		
        order_val = {
            'date_order':  datetime.now().strftime('%Y-%m-%d %H:%M:%S')	,      
            'create_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')	,  
            'partner_id': partner_id,
            'partner_invoice_id': partner_id, 			
            'partner_shipping_id': partner_shipping_id,
            'warehouse_id': 1,
            'pricelist_id': pricelist_id,  
            'company_id': 1,			
            'all_discounts': 0,
            'picking_policy': 'direct',
            'state':'draft',		
            'user_id': self._userid,		
            'order_policy': 'picking',
            'client_order_ref': u'From NT Website:%s' % nt_order.name,	
            'origin': nt_order.name,			
            'order_line': [],
        }							
					
        for line in nt_order.order_line: 	
            qty = line.product_uom_qty	
            price = line.price_unit					
            product_id = 0 
            if line.product_id.name_template == 'Delivery charge' or line.product_id.type == 'service' : 
                product_id = 19497			
            else:                			
                if not line.product_id.barcode : product_id = self.query_product_id_by_ean13(default_code=line.product_id.default_code)
                else: product_id = self.query_product_id_by_ean13(ean13=line.product_id.default_code)
				
            if not product_id: continue
			
            line_vals = {			
                'product_uos_qty': qty,
                'product_id': product_id,			
                'product_uom': 1,
                'price_unit': price,
                'pur_price_unit':price,				
                'product_uom_qty': qty,
                'name':line.name or '-',
                'delay': 7,
                'discount': 0,
            }							
            order_val['order_line'].append( (0, 0, line_vals) ) 
			
        if len(order_val['order_line']) < 1: 			
            return False

        order_id = my_proxy.execute(self._db, self._userid, self._pwd, model1, method, order_val )				
        my_proxy.execute(self._db, self._userid, self._pwd, 'sale.order', 'action_button_confirm', order_id ) 
        my_proxy.exec_workflow(self._db, self._userid, self._pwd, 'sale.order', 'manager_confirm_btn', order_id )    # manager_confirm_btn
        my_proxy.execute(self._db, self._userid, self._pwd, 'sale.order', 'inform_warehouse_shipping', order_id ) 		
        return True				
			
    def sent_mail_to_loewie_staff(self, cr, uid, context=None, message=''):
        mail_obj = self.pool.get('mail.mail')	
        #_logger.info('Jimmy(nomitang_addon) - enter sent_mail_to_loewie_staff')		
        vals = {    
                    'state':'outgoing',
                    'subject':'Salesorder from NT Website',						 
                    'body_html': '<pre>Hi, guys, We got new salesorder from NT Website --- %s</pre>' % message,
                    #'email_to': 'jimmy.lee@loewie.com,arnd.krusche@loewie.com',						 
                    'email_to':'jimmy.lee@loewie.com,arnd.krusche@loewie.com,anthony.chau@loewie.com,ray.kwok@loewie.com,anja.wang@loewie.com,emma.wang@loewie.com,chifai.yuen@loewie.com',
                    'email_from': 'info@nomitang.com',
                }
        mail_id = mail_obj.create(cr, uid, vals, context=context)
        if mail_id : 
            mail_obj.send(cr, uid, [mail_id], context=context)		
            #_logger.info('Jimmy(nomitang_addon) - sent_mail_to_loewie_staff mail_obj.send')
        return True		

    def form_feedback(self, cr, uid, data, acquirer_name, context=None):
        """ Override to confirm the sale order, if defined, and if the transaction
        is done. """
        tx = None
        #_logger.info('Jimmy(nomitang_addon form_feedback before super(payment_transaction, self).form_feedback')
		
        res = super(payment_transaction, self).form_feedback(cr, uid, data, acquirer_name, context=context)
		
        #_logger.info('Jimmy(nomitang_addon form_feedback after super(payment_transaction, self).form_feedback')
        # fetch the tx, check its state, confirm the potential SOPaymentTransaction  payment_transaction
        try:
            tx_find_method_name = '_%s_form_get_tx_from_data' % acquirer_name
            if hasattr(self, tx_find_method_name):
                tx = getattr(self, tx_find_method_name)(cr, uid, data, context=context)
            _logger.info('<%s> Jimmy(nomitang_addon form_feedback) - transaction processed: tx ref:%s, tx amount: %s', acquirer_name, tx.reference if tx else 'n/a', tx.amount if tx else 'n/a')

            if tx and tx.sale_order_id and tx.sale_order_id.state in ['draft', 'sent']:
                # verify SO/TX match, excluding tx.fees which are currently not included in SO
                amount_matches = float_compare(tx.amount, tx.sale_order_id.amount_total, 2) == 0
                #_logger.info('Jimmy(nomitang_addon form_feedback) : if amount_matches ')				
                if amount_matches:
                    if tx.state == 'done' and tx.acquirer_id.auto_confirm == 'at_pay_confirm':
                        #_logger.info('<%s> Jimmy(nomitang_addon form_feedback) - transaction completed, auto-confirming order %s (ID %s)', acquirer_name, tx.sale_order_id.name, tx.sale_order_id.id)
                        self.pool['sale.order'].action_confirm(cr, SUPERUSER_ID, [tx.sale_order_id.id], context=dict(context, send_email=True))
                        message = 'Customer:%s, Order No:%s.' % (tx.sale_order_id.partner_id.name, tx.sale_order_id.name)
                        self.sent_mail_to_loewie_staff(cr, uid, context=context, message=message)
                        self.create_hkerp_salesorder(cr, uid, [tx.id], context=context)						
                    elif tx.state not in ['cancel', 'error'] and tx.sale_order_id.state == 'draft':
                        _logger.info('<%s> Jimmy(nomitang_addon form_feedback) - transaction pending/to confirm manually, sending quote email for order %s (ID %s)', acquirer_name, tx.sale_order_id.name, tx.sale_order_id.id)
                        self.pool['sale.order'].force_quotation_send(cr, SUPERUSER_ID, [tx.sale_order_id.id], context=context)
                else:
                    _logger.warning('<%s> Jimmy(nomitang_addon form_feedback) - transaction MISMATCH for order %s (ID %s)', acquirer_name, tx.sale_order_id.name, tx.sale_order_id.id)
					
            #_logger.info('Jimmy(nomitang_addon form_feedback) : if tx and tx.sale_order_id and tx.sale_order_id.state in ')
			
        except Exception:
            _logger.exception('Jimmy(nomitang_addon form_feedback Exception) - Fail to confirm the order or send the confirmation email%s', tx and ' for the transaction %s' % tx.reference or '')

        return res
