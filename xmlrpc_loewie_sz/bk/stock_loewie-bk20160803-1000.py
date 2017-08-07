# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import datetime
import xmlrpclib
from openerp.tools.translate import _
		
class stock_picking(osv.osv):
    _inherit = "stock.picking"
	
    _columns = {
        'remote_picking_id': fields.integer( string='Remote Pick ID', readonly=True),
        'picking_no':fields.char(string='Remote Pick NO', readonly=True),		
    }
	
    _db = "LoewieHK"	
    _pwd = "Ufesbdr$%HG&hgf2432"
    _userid = 1	
    _peer_company = 'Loewie Trading Ltd.'
    _company = 	u"深圳市乐易保健用品有限公司"
    _peer_url = "http://192.168.1.250:8069/xmlrpc/object"	
    _peer_redirect = 'http://192.168.1.250:8069/web#id=%d&view_type=form&model=stock.picking&action=162&active_id=%d'	
	
    def query_id_byname(self, model, name):
        my_proxy = xmlrpclib.ServerProxy(self._peer_url)	
        ids = my_proxy.execute(self._db, 1, self._pwd, model, 'search', [('name','=',name)] )			
        if len(ids) == 0: return 0

        return ids[0]		
		
    def query_product_id_by_name_template(self, model, name):
        my_proxy = xmlrpclib.ServerProxy(self._peer_url)	
        ids = my_proxy.execute(self._db, 1, self._pwd, model, 'search', [('name_template','=',name)] )			
        if len(ids) == 0: return 0

        return ids[0]

    def query_product_id_by_ean13(self, model, ean13):
        my_proxy = xmlrpclib.ServerProxy(self._peer_url)	
        ids = my_proxy.execute(self._db, 1, self._pwd, model, 'search', ['|',('ean13','=',ean13),('default_code','=',ean13)] )			
        if len(ids) == 0: return 0

        return ids[0]		
	
    def generate_remote_erp_picking(self, cr, uid, ids, context=None):	
	
        vals_move = {	
            'product_id': 0, #, 
            'product_uom_qty':0, 
            'location_dest_id':1, #self.query_id_byname('stock.location', u'成品'), 
            'location_id': 1, #self.query_id_byname('stock.location', 'Suppliers'), 
            'company_id':self.query_id_byname('res.company', self._peer_company), 
            'date':datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'date_expected':(datetime.datetime.now() + datetime.timedelta(3)).strftime("%Y-%m-%d %H:%M:%S"), 
            'invoice_state':'none', 
            'name':'.', 
            'procure_method':'make_to_stock', 
            'state':'draft',			
            'product_uom':1, 
            'weight_uom_id':1,
            'picking_id': 0,			
        }		
		
        vals_pick = {
            'company_id': self.query_id_byname('res.company',self._peer_company),
            'partner_id': self.query_id_byname('res.partner',u'深圳市乐易保健用品有限公司'), 	
            'create_date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),			
            'origin': '.',			
            #'invoice_state': 'none',			
            'move_type': 'direct',
            'picking_type_id': 1, #self.query_id_byname('stock.picking.type', u'Receipts(收货)'),			
            #'priority': 1,		
            #'weight_uom_id': 3,            			
        }		
	
        model1 = "stock.picking"		
        model2 = "stock.move"		
        method = "create" 		
	
        for order in self.browse(cr, uid, ids):
            if order.picking_type_id.code == 'incoming' : 			
                picking_type = 2 #self.query_id_byname('stock.picking.type', u'Receipts()')
            elif order.picking_type_id.code == 'outgoing' :
                picking_type = 1 #self.query_id_byname('stock.picking.type', u'Receipts(收货)')
            else:
                return

            my_proxy = xmlrpclib.ServerProxy(self._peer_url)
            remote_id = 0			
            if order.remote_picking_id:			
                remote_id = my_proxy.execute(self._db, 1, self._pwd, model1, 'search', [('id','=',order.remote_picking_id)] )
			
            if remote_id :
                raise osv.except_osv(_(u'远端ERP仓库单据 已存在'),_(u'''请先删除远端ERP已生成的仓库单据：%s！''' % order.picking_no)) 			
				
            if True : #order.dest_address_id.name == self._company :			

                vals_pick.update({'origin': 'SZ-Pick:%s' % order.name, 'picking_type_id':picking_type})				
                value = my_proxy.execute(self._db, 1, self._pwd, model1,method, vals_pick )
                order.remote_picking_id = value		
                order.picking_no = my_proxy.execute(self._db, 1, self._pwd, model1, 'read', [value], ['name'] )[0]['name']
				
                if picking_type == 1 :    					
                    location_dest_id =  self.query_id_byname('stock.location', u'成品')                   					
                    location_id =  self.query_id_byname('stock.location', 'Suppliers')	
                if picking_type == 2 :    					
                    location_dest_id =  self.query_id_byname('stock.location', 'Suppliers')                   					
                    location_id =  self.query_id_byname('stock.location', u'成品')
					
                un_created_products = []					
                for line in order.move_lines:
                    pid = self.query_product_id_by_name_template('product.product', line.product_id.name_template)
                    if not pid: pid = self.query_product_id_by_ean13('product.product', line.product_id.ean13 or line.product_id.default_code)
                    if pid > 0 :	
                        vals_move.update({'product_id':pid, 'product_uom_qty':line.product_uom_qty, 'name': line.name, 'picking_id':value, 'location_dest_id':location_dest_id,  'location_id':location_id})	
                        my_proxy.execute(self._db, 1, self._pwd, model2, method, vals_move )
                    else:
                        un_created_products.append(line.product_id.name_template)
						
                if len(un_created_products) > 0:
                    names = ""				
                    for name in un_created_products:
                        names += name + " , " 					
                    order.note = ( order.note or "" ) + (u"   在远端ERP单据:%s 中无法找到与以下名字相同的产品：%s"  % (order.picking_no, names))
					
                    my_proxy.execute(self._db, 1, self._pwd, model1, 'write', value, {'note': u"远端ERP单据:%s 中的以下产品名 没有在本地ERP中创建: %s" % (order.name, names)} )	
            return True					
						

    def view_remote_erp_picking(self, cr, uid, ids, context=None):
        for po in self.browse(cr, uid, ids, context=context):
            if po.remote_picking_id > 0 :	 
                return {'type':'ir.actions.act_url', 'url':self._peer_redirect % (po.remote_picking_id, po.picking_type_id.code=='incoming' and 2 or 1 ), 'target':'new'}		
						