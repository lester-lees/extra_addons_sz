# -*- coding: utf-8 -*-

from openerp import fields, models

class sale_report(models.Model):
    _inherit = 'sale.report'
    
    to_affiliate_id = fields.Many2one('res.partner', string="Affiliate")
    
    def _select(self):
        select_str = """
            , ac.partner_id as to_affiliate_id
        """
        return super(sale_report,self)._select() + select_str
    
    def _from(self):
        from_str = """
                left join to_affiliate_code ac on (s.to_affcode_id=ac.id)
        """
        return super(sale_report,self)._from() + from_str
    
    def _group_by(self):
        group_by_str = """
            , ac.partner_id
        """
        return super(sale_report,self)._group_by() + group_by_str
    