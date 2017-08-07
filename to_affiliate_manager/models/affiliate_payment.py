# -*- coding: utf-8 -*-

from openerp import fields, models, api, _
import openerp.addons.decimal_precision as dp

from openerp.exceptions import except_orm
        
class affiliate_payment(models.Model):
    _name = 'to.affiliate.payment'
    _description = 'TO Affiliate Payment'
    _inherit = ['mail.thread']      
    
    name = fields.Char(string="Name", required=True, readonly=True, default='/')
    user_id = fields.Many2one('res.users', string="Affiliate", required=True, 
        track_visibility='onchange', readonly=True, states={'draft': [('readonly', False)]},
        default=lambda self: self.env.user)
    date = fields.Date(string="Payment Date", required=True, readonly=True,
        states={'draft': [('readonly', False)]}, default=fields.Date.today)
    total = fields.Float(string="Commission Total", digits_compute=dp.get_precision('Account'),
        readonly=True, compute='_get_total', store=True)
    reference = fields.Char(string="Reference", readonly=True, states={'draft': [('readonly', False)]})
    notes = fields.Text(string="Notes")    
    currency_id = fields.Many2one('res.currency', string="Currency", required=True, readonly=True,
        states={'draft': [('readonly', False)]}, default=lambda self: self.env.user.company_id.currency_id)    
    com_ids = fields.Many2many('to.affiliate.commission', 'to_affiliate_commission_payment',
        string="Commission", domain="[('state','=','confirm')]", readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed by Affiliate'),
        ('approve', 'Approved'),
        ('paid', 'Paid'),
        ('cancel', 'Rejected'),
    ], string="Status", default='draft', track_visibility='onchange')
    invoice_ids = fields.One2many('account.invoice', 'to_aff_payment_id', string="Invoices")
    invoice_exists = fields.Boolean(string="Invoiced", compute='_invoice_exists')    
            
    @api.depends('com_ids.com_amount')
    def _get_total(self):
        for r in self:
            r.total = sum(com.com_amount for com in r.com_ids)
            
    @api.depends('invoice_ids')
    def _invoice_exists(self):
        for r in self:
            if r.invoice_ids:
                r.invoice_exists = True
            else:
                r.invoice_exists = False  
            
    @api.one
    def action_compute(self):
        if self.user_id and self.date:
            commission = self.env['to.affiliate.commission'].search([
                ('user_id','=', self.user_id.id),
                ('date', '<=', self.date),
                ('state', '=', 'confirm')
            ])        
            com_ids = [item.id for item in commission]
            
            self.write({'com_ids': [(6, 0, com_ids)]})
        return True        
    
    @api.one
    def action_confirm(self):
        self.action_compute()
        if not self.com_ids:
            raise except_orm(_('User Error!'), _("You can not submit a payment which has no commission."))
        if self.total < self.env.user.company_id.to_affiliate_payout:
            raise except_orm(_('User Error!'), _(" Your Unpaid Commission so far is %s while the minimum payout is %s. You need to make additional %s before you can request for commission payment") 
                    % (self.total, self.env.user.company_id.to_affiliate_payout, self.env.user.company_id.to_affiliate_payout - self.total))
        
        self.write({'state': 'confirm'})
        self.com_ids.write({'state':'submit'})
        
    @api.one
    def action_approve(self):
        if not self.env.user.company_id.to_com_product_id:
            raise except_orm(_('User Error!'), _("You  must config Commision Product before approve payment."))
            
        invoice_obj = self.env['account.invoice']
        invoice = {}
        invoice_lines = []
        invoice_lines.append((0, 0, {
            'product_id': self.env.user.company_id.to_com_product_id.id,
            'name': self.env.user.company_id.to_com_product_id.name,
            'price_unit': self.total,
        }))
        invoice = {
            'partner_id': self.user_id.partner_id.id,
            'to_aff_payment_id': self.id,
            'account_id': self.user_id.partner_id.property_account_payable.id,
            'date': self.date,
            'type': 'in_invoice',
            'invoice_line': invoice_lines        
        }
        invoice_obj.create(invoice)
        self.write({'state': 'approve'})
    
    def action_view_invoice(self, cr, uid, ids, context=None):
        '''
        This function returns an action that display existing invoices of given sales order ids. It can either be a in a list or in a form view, if there is only one invoice to show.
        '''
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        result = mod_obj.get_object_reference(cr, uid, 'account', 'action_invoice_tree1')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        #compute the number of invoices to display
        inv_ids = []
        for so in self.browse(cr, uid, ids, context=context):
            inv_ids += [invoice.id for invoice in so.invoice_ids]
        #choose the view_mode accordingly
        if len(inv_ids)>1:
            result['domain'] = "[('id','in',["+','.join(map(str, inv_ids))+"])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
            result['views'] = [(res and res[1] or False, 'form')]
            result['res_id'] = inv_ids and inv_ids[0] or False
        return result
        
    
    @api.one
    def action_cancel(self):
        self.write({'state': 'cancel'})
        self.com_ids.write({'state':'confirm'})
        
    @api.one
    def action_draft(self):
        self.write({'state': 'draft'})
    
    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].get('to.affiliate.payment') or '/'
        user_id = vals.get('user_id', False)
        date = vals.get('date', False)
        if user_id and date:
            commission = self.env['to.affiliate.commission'].search([
                ('user_id','=', user_id),
                ('date', '<=', date),
                ('state', '=', 'confirm')
            ])
            total = sum(item.com_amount for item in commission)
            if total < self.env.user.company_id.to_affiliate_payout:
                raise except_orm(_('User Error!'), _(" Your Unpaid Commission so far is %s while the minimum payout is %s. You need to make additional %s before you can request for commission payment") 
                    % (total, self.env.user.company_id.to_affiliate_payout, self.env.user.company_id.to_affiliate_payout - total))                
        new_id = super(affiliate_payment, self).create(vals)
        return new_id
        
    @api.multi
    def unlink(self):
        for item in self:
            if item.state not in ('draft'):
                raise except_orm(_('User Error!'), _("You can only delete records whose state is draft."))
        return super(affiliate_payment, self).unlink()
    
