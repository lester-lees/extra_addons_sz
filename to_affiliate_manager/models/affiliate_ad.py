# -*- coding: utf-8 -*-

from openerp import fields, models, api
from openerp.tools.translate import html_translate

class to_affiliate_advertisement(models.Model):
    _description = "Store advertisement for affiliate partner to chose installing on their website."
    _name = "to.affiliate.advertisement"
    
    image = fields.Binary(string="Banner Image")
    url = fields.Char(string="Url to Nomi") 
    name = fields.Char(string="Advertisement Name")
    alternative_txt = fields.Char(string="Alternative")	
    active = fields.Boolean(string="Active")
    html = fields.Html('Html Code', sanitize=False, translate=html_translate)	
    #company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.user.company_id)	