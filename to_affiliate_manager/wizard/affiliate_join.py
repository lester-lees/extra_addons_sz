# -*- coding: utf-8 -*-

from openerp import fields, _
from openerp.osv import osv
from openerp import SUPERUSER_ID

class wizard_affiliate_join(osv.osv_memory):
    _name = 'to.wizard.affiliate.join'

    user_id = fields.Many2one('res.users', string="Affiliate User", default=lambda self: self.env.user)
    is_affiliate = fields.Boolean(string="Affiliate", related='user_id.partner_id.to_is_affiliate', readonly=True)
    company_id = fields.Many2one('res.company', string="Company", domain="[('aff_allowed', '=', True)]")


    def open_table(self, cr, uid, ids, context=None):
        item = self.browse(cr, SUPERUSER_ID, ids[0], context)
        super_user = self.pool.get('res.users').browse(cr, SUPERUSER_ID, SUPERUSER_ID, context=context)
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if not item.user_id.partner_id.to_is_affiliate:
            self.pool.get('to.affiliate.code').create(cr, SUPERUSER_ID, {
                'partner_id': item.user_id.partner_id.id,
                'company_id': item.company_id and item.company_id.id or super_user.company_id.to_affcode_company.id,
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        return {
                'domain': "[('partner_id', '=', " + str(user.partner_id.id) + ")]",
                'name': _('Affiliate Code'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'to.affiliate.code',
                'type': 'ir.actions.act_window',
            }
