# -*- coding: utf-8 -*-
import time
import string
from openerp.report import report_sxw
from openerp.osv import osv
import logging
_logger = logging.getLogger(__name__)

class stock_daifa_picking(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(stock_daifa_picking, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'cr': cr,
            'uid': uid,
            'group_lines_by_express': self.group_lines_by_express,	
            'group_lines_by_brand':self.group_lines_by_brand,			
        })		
    def group_lines_by_brand(self, o=None):	
        res = {}
        move_lines = o.move_lines
        for line in move_lines:
            product_id = line.product_id.id		
            product_type = line.product_id.product_type	
            product_name = line.product_id.name_template
            default_code = line.product_id.default_code			
            desc = line.product_id.description_sale			
            if product_type not in res.keys():
                res[product_type] = {}

            if product_id not in res[product_type].keys():
                res[product_type][product_id] = {'id':1,'product':product_name, 'desc':desc, 'ean13': default_code,'qty':line.product_uom_qty}
            else:
                res[product_type][product_id]['qty'] += line.product_uom_qty    

        for brand in res.values():
            id = 1		
            for product in brand.values():
                product['id'] = id 	
                id = id + 1						
            			
        return res
			
    def group_lines_by_express(self, o=None):	
        res = {}
        move_lines = o.move_lines.sorted(key=lambda r: r.express_id)		
		
        pay_way = {'we_pay':u'包邮','cash_pay':u'现付','customer_pay':u'到付'}		
			
        for line in move_lines:
            express = line.express_id
            if not express : return {}			
            express_id = line.express_id.id				
			
            if express_id not in res.keys():
                res[express_id] = {}
                zip = express.zip or u'无邮编'		
                expresser = express.expresser and express.expresser.name or 'None'
                pay = express.pay_way and pay_way[express.pay_way] or 'None'				
                note = u"姓名:%s, 电话:%s, 地址:%s, %s, 货运:%s, %s;" % (express.name, express.mobile, express.address,zip,expresser,pay )
                res[express_id].update({
                'consignee_info':note,
                'lines':[],
                })
				
            availability = 0				
            if line.picking_type_id.code == 'incoming' and line.state != 'done':
                availability = line.product_uom_qty
            else:
                availability = line.reserved_availability
				
            loc_src = line.location_id.name
            loc_dest = line.location_dest_id.name			
			
            if line.picking_type_id.code == 'outgoing':			 
                if line.product_id.is_sample: loc_src = 'Sample Loc'
                if line.product_id.clean_inventory: loc_src = 'Clean Loc'
                if line.product_id.is_market: loc_src = 'Market Loc'				
			
            if line.picking_type_id.code == 'incoming':			 
                if line.product_id.is_sample: loc_dest = 'Sample Loc'
                if line.product_id.clean_inventory: loc_dest = 'Clean Loc'
                if line.product_id.is_market: loc_dest = 'Market Loc'
				
            desc = line.name or '-'				
            if line.product_id.description_sale and len(desc.strip())<3:	
                desc = line.product_id.description_sale		
            line_value = {
                'id': len(res[express_id]['lines'])+1,			
                'product_name': line.product_id.name,		
                'description': desc,				
                'internal_reference':line.product_id.default_code,
                'express_id':line.express_id.name,						
                'loc_dest': loc_dest,				
                'loc_src': loc_src,				
                'ean13':line.product_id.ean13,				
                'qty': line.product_uom_qty,				
                'availability': availability,				
            }
			
            res[express_id]['lines'].append(line_value)		
			
        return res			
		
class daifa_picklist_details(osv.AbstractModel):
    _name = 'report.loewieec_sync_sz.stock_picking_daifa'
    _inherit = 'report.abstract_report'
    _template = 'loewieec_sync_sz.stock_picking_daifa'
    _wrapped_report_class = stock_daifa_picking
	
	