# -*- coding: utf-8 -*-

from ..constants import AFFCODE_PARAM_NAME
from openerp import fields,models,api
import string
import random
from openerp.tools.translate import _
from openerp.exceptions import except_orm


class affiliate_code(models.Model):
    _name = 'to.affiliate.code'
    _description = 'TO Affiliate Code'
    
    @api.one
    @api.depends('name')
    def _gen_description(self):        
        if self.name and self.website_id and self.website_id.domain:
            self.description = _("""
                In order to get started with the code <code>%s</code>, 
                just copy the URL <code>%s/?%s=%s</code> and share it with your friends and partners. 
                You can put the URL on your social network like Facebook, LinkedIn 
                or put it on webpages where you can to get more and more customers.
            """) % (self.name, self.website_id.domain, AFFCODE_PARAM_NAME, self.name)
        else:
            self.description = ""
    
    name = fields.Char(string="Code", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Partner", required=True)
    saleperson_id = fields.Many2one('res.users', string="Saleperson", related='partner_id.user_id', store=True, readonly=True)
    url = fields.Char(string="URL", readonly=True)
    description = fields.Html(string="Description", compute='_gen_description')
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.user.company_id, required=True)
    website_id = fields.Many2one('website', string="Website")
    
    _sql_constraints = [
        ('partner_uniq', 'unique(partner_id)', 'The selected partner have already an affiliate code!'),
    ]
    
    @api.model
    def create(self, values):
        partner_id = values['partner_id']
        partner = self.browse(partner_id)
        user = self.env['res.users'].search([('partner_id','=',partner_id)], limit=1)
        if not user:
            raise except_orm(_('User Error!'), _("The partner you've selected does not link to any user. Please link the partner to a user before proceeding further"))            
        
        values['name'] = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(7))
        if values.get('website_id', False):            
            website = self.env['website'].browse(values['website_id'])
            values['url'] = website.domain + '?' + AFFCODE_PARAM_NAME + '=' + values['name']
        
        new_id = super(affiliate_code, self).create(values)
        new_id.partner_id.user_ids.write({
            'company_ids': [(6, 0, [new_id.company_id.id])],
            'company_id': new_id.company_id.id
        })        
        partner_values = {
            'to_is_affiliate': True,
            'supplier': True,
            'company_id': new_id.company_id.id
        }
        pricelist = self.env['product.pricelist'].search([('to_is_affiliate_pricelist','=',True), ('company_id','=',new_id.company_id.id)], limit=1)
        if pricelist:
            partner_values.update({'property_product_pricelist':pricelist.id})
        new_id.partner_id.write(partner_values)        
        
        md = self.env['ir.model.data']
        res_id = md.get_object_reference('to_affiliate_manager', 'group_to_affiliate_portal')[1]
        group = self.env['res.groups'].browse(res_id)
        user = self.env['res.users'].search([('partner_id','=',new_id.partner_id.id)], limit=1)        
        group.write({'users': [(4, user.id)]})
        
        return new_id
    
    @api.multi
    def unlink(self):
        for item in self:
            item.partner_id.write({'to_is_affiliate': False})
            user = self.env['res.users'].search([('partner_id','=',item.partner_id.id)], limit=1)
            md = self.env['ir.model.data']
            if user:
                res_id = md.get_object_reference('to_affiliate_manager', 'group_to_affiliate_portal')[1]
                group = self.env['res.groups'].browse(res_id)
                group.write({'users': [(3, user.id)]})
            
        return super(affiliate_code, self).unlink()
    
