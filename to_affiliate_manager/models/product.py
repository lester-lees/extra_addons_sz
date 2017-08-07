# -*- coding: utf-8 -*-

from openerp import fields, models, api

class product_pricelist(models.Model):
    _inherit = 'product.pricelist'
    
    to_is_affiliate_pricelist = fields.Boolean(string="Is Affiliate Pricelist?")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.user.company_id)
    
    @api.model
    def create(self, values):
        new_id = super(product_pricelist, self).create(values)
        if new_id.to_is_affiliate_pricelist:
            pricelists = self.search([
                ('to_is_affiliate_pricelist','=',True),
                ('id','!=',new_id.id),
                ('company_id','=',new_id.company_id.id)
            ])
            if pricelists:
                pricelists.write({'to_is_affiliate_pricelist': False})
        return new_id
    
    @api.multi
    def write(self, vals):
        to_is_affiliate_pricelist = vals.get('to_is_affiliate_pricelist', False)
        if to_is_affiliate_pricelist:
            company_id = vals.get('company_id', False)
            if not company_id:
                company_id = self.company_id.id
            pricelists = self.search([('to_is_affiliate_pricelist','=',True),('company_id','=',company_id)])
            if pricelists:
                pricelists.write({'to_is_affiliate_pricelist': False})                        
        return super(product_pricelist, self).write(vals)