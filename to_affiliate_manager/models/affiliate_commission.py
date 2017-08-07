# -*- coding: utf-8 -*-

from openerp import fields, models, api, _
from openerp.addons import decimal_precision as dp
from openerp.exceptions import except_orm
         

class affiliate_commission_rule_line(models.Model):
    _name = 'to.affiliate.commission.rule.line'
    _description = 'TO Affiliate Commission Rule Line'
    
    rule_id = fields.Many2one('to.affiliate.commission.rule', string="Commission Rule")
    company_id = fields.Many2one('res.company', string="Company", readonly=True, default=lambda self: self.env.user.company_id, required=True)
    product_id = fields.Many2one('product.product', string="Product", required=True)
    comm_percent = fields.Float(string="Commission Percentage (%)", default=lambda self: self.env.user.company_id.to_affiliate_comm_percent, required=True)
    
    _sql_constraints = [
        ('product_uniq', 'unique(product_id,company_id)', 'Product must be unique per company!'),
    ]

class affiliate_commission_rule(models.Model):
    _name = 'to.affiliate.commission.rule'
    _description = 'TO Affiliate Commission Rule'
    _inherit = ['mail.thread']
    
    name = fields.Char(string="Rule Name", required=True)
    company_id = fields.Many2one('res.company', string="Company", readonly=True, default=lambda self: self.env.user.company_id, required=True)
    type = fields.Selection([
        ('all', 'All Products'),
        ('category', 'Product Categories'),
        ('product_tmpl', 'Product Templates'),
        ('product', 'Products'),
    ], string="Apply for", required=True, default='all', track_visibility='onchange')
    comm_percent = fields.Float(string="Commission Percentage", default=lambda self: self.env.user.company_id.to_affiliate_comm_percent, track_visibility='onchange')
    product_category_ids = fields.Many2many('product.category', string="Product Categories")
    description = fields.Text(string="Description")
    line_ids = fields.One2many('to.affiliate.commission.rule.line','rule_id', string="Commission Details")    

class affiliate_commission_line(models.Model):
    _name = 'to.affiliate.commission.line'
    _description = 'TO Affiliate Commission Line'
    
    commission_id = fields.Many2one('to.affiliate.commission', string="Commission")
    product_id = fields.Many2one('product.product', string="Product", required=True)
    total = fields.Float(string="Total", required=True)
    comm_percent = fields.Float(string="Commission Percentage", required=True)
    comm_amount = fields.Float(string="Commission Amount", compute='_get_amount', store=True)
    
    @api.depends('total', 'comm_percent')
    def _get_amount(self):
        for r in self:
            r.comm_amount = r.total * r.comm_percent / 100

class affiliate_commission(models.Model):
    _name = 'to.affiliate.commission'
    _description = 'TO Affiliate Commission'
    _inherit = ['mail.thread']
    
    name = fields.Char(string="Name", required=True, readonly=True, default='/')
    user_id = fields.Many2one('res.users', string="Affiliate", required=True, 
        track_visibility='onchange', readonly=True, states={'draft': [('readonly', False)]})    
    date = fields.Date(string="Date", required=True, readonly=True, states={'draft': [('readonly', False)]})
    order_id = fields.Many2one('sale.order', string="Sales Order", required=True, readonly=True, states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', string="Currency", required=True, readonly=True,
        states={'draft': [('readonly', False)]}, default=lambda self: self.env.user.company_id.currency_id)    
    com_amount = fields.Float(string="Commission Amount", compute='_get_com_amount', digits_compute=dp.get_precision('Account'), store=True)
    line_ids = fields.One2many('to.affiliate.commission.line', 'commission_id', string="Commission Details", readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('com_paid', 'Commission Paid'),
        ('submit', 'Submitted Request'),
        ('cancel', 'Cancelled'),
    ], string="Status", default='draft', track_visibility='onchange')
    customer_invoice_ids = fields.Many2many('account.invoice', related='order_id.invoice_ids', string="Customer Invoices", readonly=True)
    
    @api.depends('line_ids.comm_amount')
    def _get_com_amount(self):
        for r in self:
            r.com_amount = sum(x.comm_amount for x in r.line_ids)
    
    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].get('to.affiliate.commission') or '/'
        new_id = super(affiliate_commission, self).create(vals)
        return new_id
    
    @api.one
    def action_confirm(self):        
        self.write({'state': 'confirm'})
        
    @api.multi
    def unlink(self):
        for item in self:
            if item.state not in ('draft'):
                raise except_orm(_('User Error!'), _("You can only delete records whose state is draft."))
        return super(affiliate_commission, self).unlink()
    
    @api.one
    def action_cancel(self):
        self.write({'state':'cancel'})
            
    @api.one
    def action_draft(self):
        self.write({'state':'draft'})

