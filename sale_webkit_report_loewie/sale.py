# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
import time
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
import logging
_logger = logging.getLogger(__name__)

# LY add checkbox " use price list "
class product_pricelist(osv.osv):
    _inherit = "product.pricelist"
    _columns = {
        'use_purchase_currency': fields.boolean(_('Use Purchase Currency?')),
    }

class res_partner(osv.osv):
    _inherit = 'res.partner'

    _columns = {	
        'one_currency': fields.boolean('One Currency', default=False),
        'half_price': fields.boolean('Half price in Custom Invoice',default=False),		
	
    }		
	
class sale_order_line(osv.osv):
    _inherit = "sale.order.line"

    def _pur_amount_line(self, cr, uid, ids, prop, arg, context=None):
        res = {}
        cur_obj = self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        line_obj = self.pool.get('sale.order.line')
        for line in line_obj.browse(cr, uid, ids, context=context):
            res[line.id] = {
                # 'price_subtotal': 0.0,
                # 'pur_price_unit': 0.0,
                'pur_price_subtotal': 0.0,
            }
            # taxes = tax_obj.compute_all(cr, uid, line.tax_id, line.price_unit,
            #     line.product_uom_qty, line.product_id, line.order_id.partner_id)
            # cur = line.order_id.pricelist_id.currency_id
            # subtotal = cur_obj.round(cr, uid, cur, taxes['total'])
            # pur_cur_id = line.pur_currency_id
            # pur_price_unit = cur_obj.compute(
            #     cr, uid, cur.id, pur_cur_id.id, line.price_unit, context=context)
            # res[line.id]['pur_price_unit'] = pur_price_unit

            # pur_price_subtotal = cur_obj.compute(
            #     cr, uid, cur.id, pur_cur_id.id, subtotal, context=context)
            obj_precision = self.pool.get('decimal.precision')
            prec = obj_precision.precision_get(cr, uid, 'Account')
            pur_price_subtotal = round(round(line.pur_price_unit, prec) * line.product_uom_qty,
                prec)
            
            res[line.id] = pur_price_subtotal
        return res

    _columns = {
        'name':fields.char('Product Description'),
        'platform_so':fields.char('Platform SO'),
        'pur_currency_id': fields.many2one('res.currency', 'Pur Currency'),
        'pur_price_unit': fields.float(string='Pur Price Unit',
            digits_compute=dp.get_precision('Account')),
        'pur_price_subtotal': fields.function(
            _pur_amount_line, string='Pur Subtotal',
            digits_compute=dp.get_precision('Account'),
            ),
        'sequence': fields.integer('Sequence', help="Gives the sequence order \
            when displaying a list of purchase order lines."),
    }
	
    def check_qty(self, cr, product_id, qty_ask):	
        if not product_id: return 0	
		
        cr.execute("select sum(product_uom_qty) from stock_move where product_id=%d and state='assigned' and location_dest_id in (select id from stock_location where usage='internal')" % product_id )	
        for val in cr.fetchall():
            qty_on_the_way = val[0]
        if not 	qty_on_the_way : qty_on_the_way = 0		
        qty_on_the_way = int(qty_on_the_way)		

        cr.execute("select sum(qty) from stock_quant where product_id=%d and location_id in (select id from stock_location where usage='internal')" % product_id)		
        for val in cr.fetchall():
            qty_on_hand = val[0]
        if not qty_on_hand : qty_on_hand = 0			
        qty_on_hand = int(qty_on_hand)		
		
        cr.execute("select sum(qty) from stock_quant where product_id=%d and reservation_id is not Null and location_id in (select id from stock_location where usage='internal')" % product_id)
        for val in cr.fetchall():
            qty_reserved = val[0]
        if not qty_reserved : qty_reserved = 0
        qty_reserved = int(qty_reserved)

        return {'qty_on_the_way':qty_on_the_way, 'qty_on_hand':qty_on_hand, 'qty_reserved':qty_reserved}
			
    def get_price(self, cr, pricelist_id=None, product_id=None):
	
        if (not pricelist_id) or (not product_id):
            return 0		
		
        cr.execute("select name,id from product_pricelist where name = 'Wholesale_USD' or name = 'Wholesale_HKD' or name = 'Wholesale_EUR'")		
        dict_pl = {}		
        for res in cr.fetchall():
            dict_pl[res[0]] = res[1]		

        if pricelist_id in dict_pl.values():
            pricelist_id = dict_pl['Wholesale_USD']			
			
        cr.execute("select price_surcharge from product_pricelist_item where product_id = %d and price_version_id = ( select id from product_pricelist_version where pricelist_id=%d and active=True limit 1)" % (product_id,pricelist_id) )
        price = 0		
        for res in cr.fetchall():
            price = res[0]

        return price		
	
    def pur_price_change(self, cr, uid, ids, pur_price_unit, pricelist_id,pur_currency_id, context=None):
        result = {}
        context = context or {}        
        currency_obj = self.pool.get('res.currency')
        pricelist_obj = self.pool.get('product.pricelist').browse(cr, uid, pricelist_id, context=context)		
        to_currency_id = pricelist_obj.currency_id.id
        use_purchase_currency = pricelist_obj.use_purchase_currency
		
        if use_purchase_currency :		
            result['price_unit'] = currency_obj.compute(cr, uid, pur_currency_id, to_currency_id, pur_price_unit, context=context)
        else:
            result['price_unit'] = 	pur_price_unit	
		
        return {'value': result, 'domain': {}, 'warning': {}}	

    def price_unit_change(self, cr, uid, ids, price_unit, parent_pricelist_id, pur_currency_id, context=None):
        result = {}
        context = context or {}        
        currency_obj = self.pool.get('res.currency')
        pricelist_obj = self.pool.get('product.pricelist').browse(cr, uid, parent_pricelist_id, context=context)		
        from_currency_id = pricelist_obj.currency_id.id
        use_purchase_currency = pricelist_obj.use_purchase_currency
		
        if use_purchase_currency :		
            result['pur_price_unit'] = currency_obj.compute(cr, uid, from_currency_id, pur_currency_id, price_unit, context=context)
        else:
            result['pur_price_unit'] = 	price_unit	
		
        return {'value': result, 'domain': {}, 'warning': {}}		

    def product_name_change(self, cr, uid, ids, product, name, context=None):
	
        name = name or context.get('name_str','') 		
        name_str = name and name.lower() or ''	
        		
        if not name : 
            return {'value': {'name':'-'}, 'domain':{},'warning':{} }
			
        if name_str.find('sample')>=0 or name_str.find('replacement')>=0 or name_str.find('shortship')>=0 or name.find('RMA')>=0 :		
            return {'value': {'name':name,'price_unit':0,'pur_price_unit':0}, 'domain':{},'warning':{} } 
	
        return {'value': {}, 'domain':{},'warning':{} } 		
		
    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False,
            fiscal_position=False, flag=False, context=None):
        obj_precision = self.pool.get('decimal.precision')
        prec = obj_precision.precision_get(cr, uid, 'Account')
        context = context or {}
        lang = lang or context.get('lang', False)
        if not partner_id:
            return {'value': {}, 'domain':{},'warning':{} } 		
            #raise osv.except_osv(_('No Customer Defined !'),_('''Before choosing a product,\n select a customer in the sales form.''')) 

        warning = {}
        product_uom_obj = self.pool.get('product.uom')
        partner_obj = self.pool.get('res.partner')
        product_obj = self.pool.get('product.product')
        context = {'lang': lang, 'partner_id': partner_id}
        if partner_id:
            lang = partner_obj.browse(cr, uid, partner_id).lang
        context_partner = {'lang': lang, 'partner_id': partner_id}

        if not product:
            return {'value': {'th_weight': 0,
                'product_uos_qty': qty}, 'domain': {'product_uom': [],
                   'product_uos': []}}
        if not date_order:
            date_order = time.strftime(DEFAULT_SERVER_DATE_FORMAT)

        result = {}
        warning_msgs = ''
        product_obj = product_obj.browse(cr, uid, product, context=context_partner)
		
        uom2 = False
        if uom:
            uom2 = product_uom_obj.browse(cr, uid, uom)
        if uos:
            if product_obj.uos_id:
                uos2 = product_uom_obj.browse(cr, uid, uos)
                if product_obj.uos_id.category_id.id != uos2.category_id.id:
                    uos = False
            else:
                uos = False
        fpos = fiscal_position and self.pool.get('account.fiscal.position').browse(
            cr, uid, fiscal_position) or False
        if update_tax:
            # The quantity only have changed
            result['tax_id'] = self.pool.get('account.fiscal.position').map_tax(
                cr, uid, fpos, product_obj.taxes_id)

        result['name'] = '-'
        if product_obj.description_sale:
            result['name'] += product_obj.description_sale	
			
        domain = {}
        if (not uom) and (not uos):
            result['product_uom'] = product_obj.uom_id.id
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
                uos_category_id = product_obj.uos_id.category_id.id
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
                uos_category_id = False
            result['th_weight'] = qty * product_obj.weight
            domain = {
                'product_uom':
                [('category_id', '=', product_obj.uom_id.category_id.id)],
                'product_uos': [('category_id', '=', uos_category_id)]}
        elif uos and not uom:
            # only happens if uom is False
            result['product_uom'] = product_obj.uom_id and product_obj.uom_id.id
            result['product_uom_qty'] = qty_uos / product_obj.uos_coeff
            result['th_weight'] = result['product_uom_qty'] * product_obj.weight
        elif uom:
            # whether uos is set or not
            default_uom = product_obj.uom_id and product_obj.uom_id.id
            q = product_uom_obj._compute_qty(cr, uid, uom, qty, default_uom)
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty

            # Round the quantity up
            result['th_weight'] = q * product_obj.weight

        if not uom2:
            uom2 = product_obj.uom_id

        if not pricelist:
            warn_msg = _('''You have to select a pricelist or a customer in the sales form !\n
                    Please set one before choosing a product.''')
            warning_msgs += _("No Pricelist ! : ") + warn_msg + "\n\n"
        else:
            pricelist_data_obj = self.pool.get('product.pricelist').browse(
                cr, uid, [pricelist], context=context)[0]
            currency_id_list = pricelist_data_obj.currency_id.id
            currency_obj = self.pool.get('res.currency')
            purchase_curr = product_obj.purchase_currency_id.id
            company_curr = product_obj.company_id.currency_id.id

            original_price = self.get_price(cr,pricelist,product_obj.id)	
				
            result.update({'pur_price_unit': original_price})
			
            # xie set purchase currency
            result.update({'pur_currency_id': purchase_curr or company_curr})

            # LY apply loewie price rule
            if not pricelist_data_obj.use_purchase_currency:
                # 1 LY normal price list, fixed price
                amount = original_price
            else:
                # 2 LY price calculated from price of purchase currency
                if purchase_curr:
                    amount = currency_obj.compute(
                        cr, uid, purchase_curr, currency_id_list,
                        original_price, context=context)
                else:
                    amount = currency_obj.compute(
                        cr, uid, company_curr, currency_id_list,
                        original_price, context=context)

            if amount is False:
                warn_msg = _('''Cannot find a pricelist line matching this
                    product and quantity.\nYou have to change either the
                    product, the quantity or the pricelist.''')
                warning_msgs += _("No valid pricelist line found ! :") + warn_msg +"\n\n"
            else:
                result.update({'price_unit': amount})

        if partner_id:
            discount_obj = self.pool.get('product.discount')
            product_type = product_obj.product_type or None
            filer = [
                ('type', '=', product_type),
                ('partner_id', '=', partner_id)
            ]
            dis_id = discount_obj.search(cr, uid, filer, context=context)
            if dis_id:
                dis_id = dis_id[0]
                dis = discount_obj.browse(cr, uid, dis_id, context=context)
                result.update({'discount': dis.discount})			

        warning = {
            'title': _('Configuration Error!'),
            'message': warning_msgs 
        }
        return {'value': result, 'domain': domain, 'warning': warning}

sale_order_line()