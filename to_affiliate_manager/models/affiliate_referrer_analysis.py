# -*- coding: utf-8 -*-

from openerp import fields,models,api

class affiliate_referrer_analysis(models.Model):
    _name = 'to.affiliate.referrer.analysis'
    _description = 'TO Affiliate Referrer Analytic'
    
    affcode_id = fields.Many2one('to.affiliate.code', string="Affiliate Code", required=True)
    name = fields.Char(string="Name", required=True)
    referrer = fields.Char(string="Source")
    ip = fields.Char(string="IP Address")
    browser = fields.Char(string="Browser")
    datetime = fields.Datetime(string="Datetime", default=fields.Datetime.now)        
