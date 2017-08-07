# -*- coding: utf-8 -*-

from openerp import models, api

class IrRule(models.Model):
    _inherit = 'ir.rule'
    
    @api.model
    def update_rules(self):
        portal_sale_order_user_rule = self.env.ref('portal_sale.portal_sale_order_user_rule')
        portal_sale_order_user_rule.write({'domain_force':"['|',('message_partner_ids','child_of',[user.commercial_partner_id.id]),('to_affcode_id.partner_id.id','=',user.commercial_partner_id.id)]"})