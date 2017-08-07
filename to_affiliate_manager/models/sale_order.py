# -*- coding: utf-8 -*-

from ..constants import AFFCODE_PARAM_NAME
from openerp import fields,models, api
from openerp import SUPERUSER_ID
from openerp.http import request

class sale_order(models.Model):
    _inherit = 'sale.order'
    
    to_affcode_id = fields.Many2one('to.affiliate.code', string="AffCode", readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        copy=False, ondelete='restrict')
    to_referrer_analysis_id = fields.Many2one('to.affiliate.referrer.analysis', string="Referrer", readonly=True,
        copy=False, ondelete='restrict')
    
    @api.one
    def action_button_confirm(self):
        res = super(sale_order, self).action_button_confirm()
        #self.signal_workflow('order_confirm')
        if self.to_affcode_id:
            user = self.env['res.users'].search([('partner_id','=',self.to_affcode_id.partner_id.id)], limit=1)
            if user:
                line_ids = []
                commission_rule_line_obj = self.env['to.affiliate.commission.rule.line']
                super_user = self.env['res.users'].browse(SUPERUSER_ID)
                for item in self.order_line:
                    commission_rule_line = commission_rule_line_obj.search([
                        ('product_id','=',item.product_id.id),
                        ('company_id','=',item.order_id.company_id.id)
                    ], limit=1)
                    if commission_rule_line:
                        line_ids.append((0, 0, {
                            'product_id': item.product_id.id,
                            'total': item.price_subtotal,
                            'comm_percent': commission_rule_line.comm_percent,
                        }))
                    else:
                        line_ids.append((0, 0, {
                            'product_id': item.product_id.id,
                            'total': item.price_subtotal,
                            'comm_percent': super_user.company_id.to_affiliate_comm_percent,
                        }))
                if line_ids:
                    affiliate_com = self.env['to.affiliate.commission'].create({
                        'user_id': user.id,
                        'date': self.date_order,
                        'order_id': self.id,
                        'line_ids': line_ids                
                    })
                    affiliate_com.action_confirm()

            # if customer has no saleperson yet, assign a sale person
            customer = self.partner_id
            if not customer.user_id:
                customer.user_id = self.user_id
                customer.company_id = self.user_id.company_id

        return res
    
    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].get('sale.order') or '/'

        res = super(sale_order, self).create(vals)

        if not res.to_affcode_id:
            affcode_cookie = request.httprequest.cookies.get(AFFCODE_PARAM_NAME)
            if affcode_cookie:
                env = request.env(user=SUPERUSER_ID)
                affcode = env['to.affiliate.code'].search([('name', '=', affcode_cookie)], limit=1)
                if affcode:
                    res.to_affcode_id = affcode.id

        if res.to_affcode_id:

            salesperson = res.to_affcode_id.saleperson_id
            if salesperson:
                res.user_id = salesperson.id

            company = res.to_affcode_id.company_id
            if company:
                res.company_id = company.id

        return res

    @api.multi
    def action_cancel(self):
        res = super(sale_order, self).action_cancel()
        aff_commissions = self.env['to.affiliate.commission'].search([('order_id','=',self.id)])
        aff_commissions.action_cancel()
        return res
    
    @api.onchange('to_affcode_id', 'partner_id')
    def _onchage_to_affiliate_id(self):
        if not self.partner_id.user_id:
            aff_saleperson_id = self.to_affcode_id.saleperson_id
            if aff_saleperson_id:
                self.user_id = aff_saleperson_id
            else:
                self.user_id = self.env.user
