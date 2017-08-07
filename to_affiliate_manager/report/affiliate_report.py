# -*- coding: utf-8 -*-

from openerp import tools
from openerp import fields, models
import openerp.addons.decimal_precision as dp

class report_affiliate_referrer_analysis(models.Model):
    _name = 'to.report.affiliate.referrer.analysis'
    _description = 'Report Affiliate Referrer Analysis'
    _auto = False
    
    affcode_id = fields.Many2one('to.affiliate.code', string="Affiliate Code", readonly=True)
    affiliate_id = fields.Many2one('res.partner', string="Affiliate", readonly=True)
    referrer = fields.Char(string="Referrer", readonly=True)
    ip = fields.Char(string="IP Address", readonly=True)
    browser = fields.Char(string="Browser", readonly=True)
    datetime = fields.Datetime(string="Datetime", readonly=True)
    number_so = fields.Integer(string="# Sales Orders", readonly=True)
    amount_so = fields.Float(string="Amount", readonly=True, digits_compute=dp.get_precision('Account'))
    
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'to_report_affiliate_referrer_analysis')
        cr.execute("""
            create or replace view to_report_affiliate_referrer_analysis as (
                 SELECT 
                    min(a.id) as id,
                    affcode_id,
                    ac.partner_id as affiliate_id,
                    referrer,
                    ip,
                    browser,
                    datetime,
                    (SELECT count(*) FROM sale_order so WHERE so.to_referrer_analysis_id = a.id AND so.state NOT IN ('draft', 'cancel', 'sent')) AS number_so,
                    (SELECT sum(amount_total) FROM sale_order so WHERE so.to_referrer_analysis_id = a.id AND so.state NOT IN ('draft', 'cancel', 'sent')) AS amount_so
                FROM to_affiliate_referrer_analysis a
                    LEFT JOIN to_affiliate_code ac ON (a.affcode_id=ac.id)
                GROUP BY
                    affcode_id,
                    ac.partner_id,
                    referrer,
                    ip,
                    browser,
                    datetime,
                    number_so,
                    amount_so
            )
        """)
