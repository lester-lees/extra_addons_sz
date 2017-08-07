# -*- coding: utf-8 -*-
import time
from openerp.report import report_sxw
from openerp.osv import osv
import logging
import datetime
import string
_logger = logging.getLogger(__name__)

class sale_contract_report(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(sale_contract_report
		, self).__init__(cr, uid, name, context=context)	
        self.localcontext.update({
            'time': time,
            'cr': cr,
            'uid': uid,		
            'group_salelines_by_brand': self.group_salelines_by_brand,			
        })	
		
    def group_salelines_by_brand(self, sale_orders=None):	    		
        lines = []
        line_list = {}		
        if not sale_orders: return 
		
        partner_id = 0		
        for order in sale_orders:
            if not partner_id : partner_id = order.partner_id.id
            elif partner_id != order.partner_id.id :
                raise osv.except_osv((u'错误!'), (u'只能对同一个客户的销售单 出具 购销合同.'))                			
            			
            lines += order.order_line

        for line in lines :  #.sorted( key=lambda x: x.product_id.name_template):
            if line.product_id.type == 'service': continue		
            line_key = str(line.product_id.name_template) + str(line.product_id.id) + str(line.price_unit) + str(line.discount) + str(line.tax_id)
            if line_key in line_list.keys():
                line_list[line_key]['qty'] += line.product_uom_qty
            else:
                name_template = line.product_id.name_template
                unit = name_template.find('ml')>=0 and u'瓶' or u'个'				
                line_list[line_key] = {'id':line.product_id.id, 'product_name':line.product_id.name_template, 'name_cn':line.product_id.description_sale, 'unit':unit, 'qty':line.product_uom_qty, 'price':line.price_unit*(100-line.discount)/100}	

        return line_list				

class sale_contract_report_details(osv.AbstractModel):
    _name = 'report.account_loewie.view_sale_contract_report'
    _inherit = 'report.abstract_report'
    _template = 'account_loewie.view_sale_contract_report'
    _wrapped_report_class = sale_contract_report		
	