# -*- coding: utf-8 -*-
import time
import string
from openerp.report import report_sxw
from openerp.osv import osv
import logging
_logger = logging.getLogger(__name__)

class product_product_report_cls(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(product_product_report_cls, self).__init__(cr, uid, name, context=context)	
        self.localcontext.update({
            'time': time,
            'cr': cr,
            'uid': uid,			
        })	
		

class product_product_report_today_details(osv.AbstractModel):
    _name = 'report.warehouse_loewie_sz.product_product_report_today'
    _inherit = 'report.abstract_report'
    _template = 'warehouse_loewie_sz.product_product_report_today'
    _wrapped_report_class = product_product_report_cls	


class product_product_report_yesterday_details(osv.AbstractModel):
    _name = 'report.warehouse_loewie_sz.product_product_report_yesterday'
    _inherit = 'report.abstract_report'
    _template = 'warehouse_loewie_sz.product_product_report_yesterday'
    _wrapped_report_class = product_product_report_cls		
	