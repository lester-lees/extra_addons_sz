# -*- coding: utf-8 -*-

from openerp import fields, models, api
import openerp

class affiliate_config_settings(models.Model):
    _name = 'to.affiliate.config.settings'
    _inherit = 'res.config.settings'
    
    company_id = fields.Many2one('res.company', string="Company",required=True, default=lambda self: self.env.user.company_id)
    comm_percent = fields.Float(string="Default Commission Percentage", related='company_id.to_affiliate_comm_percent')
    cookie_age = fields.Integer(string="Cookie Life", related='company_id.to_affiliate_cookie_age')
    payout = fields.Float(string="Minimum Payout", related='company_id.to_affiliate_payout')
    com_product_id = fields.Many2one('product.product', string="Commission Product", required=True,
        related='company_id.to_com_product_id', domain=[('type','=','service')])
    affcode_company = fields.Many2one('res.company', string="Default Affiliate Company", related='company_id.to_affcode_company', required=True, help="When a user joins the affiliate program without selecting a seller company (in multi-company environment), the company selected here will be chosen.")
    
    @api.model
    def create(self, values):
        new_id = super(affiliate_config_settings, self).create(values)
        # Hack: to avoid some nasty bug, related fields are not written upon record creation.
        # Hence we write on those fields here.
        vals = {}
        for fname, field in self._columns.iteritems():
            if isinstance(field, openerp.osv.fields.related) and fname in values:
                vals[fname] = values[fname]
        self.write(vals)
        return new_id