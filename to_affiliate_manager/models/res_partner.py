# -*- coding: utf-8 -*-

from openerp import fields,models

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    to_is_affiliate = fields.Boolean(string="Affiliate", default=False)
    to_affcode_id = fields.Many2one('to.affiliate.code', string="Affiliate Code")
    website2 = fields.Char(string="Website2")	