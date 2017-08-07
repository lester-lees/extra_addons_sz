# -*- coding: utf-8 -*-
import time
import string
from openerp.report import report_sxw
from openerp.osv import osv
import logging
_logger = logging.getLogger(__name__)

class stock_tmijdi_picking(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(stock_tmijdi_picking, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'cr': cr,
            'uid': uid,
            'group_lines_by_coe': self.group_lines_by_coe,				
        })		
		
    def group_lines_by_coe(self, o=None):	
        res = {}
        move_lines = o.move_lines.sorted(key=lambda r: r.express_id)		
			
        for line in move_lines:
            express_id = line.express_id
            if not express_id : 
                raise osv.except_osv(u'您选择了错误的拣货单',u'''没有快递信息''')			
                return False			
            coe_no_id = line.express_id.id		
			
            if coe_no_id not in res.keys():
                res[coe_no_id] = {}
				
                note = u"TMJD NO:%s , COE:%s , 姓名:%s , 电话:%s , 省份:%s , 城市:%s , 收货地址:%s , 邮编:%s ;"	% (express_id.tmi_jdi_no, express_id.name, express_id.receive_name, express_id.tel, express_id.province,express_id.city,express_id.address,express_id.zip )
				
                res[coe_no_id].update({
                'coe_info':note,
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
				
            line_value = {
                'id': len(res[coe_no_id]['lines'])+1,			
                'product_name': line.product_id.name,		
                'description': line.name,				
                'internal_reference':line.product_id.default_code,
                'express_id':line.express_id.name,		
                'tmi_jdi_no':line.express_id.tmi_jdi_no,				
                'loc_dest': loc_dest,				
                'loc_src': loc_src,				
                'ean13':line.product_id.ean13,				
                'qty': line.product_uom_qty,				
                'availability': availability,				
            }
			
            res[coe_no_id]['lines'].append(line_value)		
			
        return res			
		
class tmijdi_picklist_details(osv.AbstractModel):
    _name = 'report.loewieec_sync_sz.stock_picking_tmijdi'
    _inherit = 'report.abstract_report'
    _template = 'loewieec_sync_sz.stock_picking_tmijdi'
    _wrapped_report_class = stock_tmijdi_picking
	
	