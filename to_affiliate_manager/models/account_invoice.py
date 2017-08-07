# -*- coding: utf-8 -*-

from openerp import fields, models, api

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    
    to_aff_payment_id = fields.Many2one('to.affiliate.payment', string="Commission Payment")
    
    @api.multi
    def confirm_paid(self):
        res = super(AccountInvoice, self).confirm_paid()
        for item in self:
            if item.to_aff_payment_id:
                item.to_aff_payment_id.write({'state': 'paid'})
                item.to_aff_payment_id.com_ids.write({'state': 'com_paid'})
        return res