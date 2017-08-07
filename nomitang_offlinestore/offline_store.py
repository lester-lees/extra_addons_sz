# -*- coding: utf-8 -*-
from openerp import fields,models

class nt_offlinestore(models.Model):
    _name = 'nt.offlinestore'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    name = fields.Char(string='Offline Store', required=True, translate=True)
    image = fields.Binary(string='Image')
    img_src = fields.Char(string='Image Source')	
    type = 	fields.Selection([('normal', 'Normal'), ('distributors', 'Distributors')], string='Type',default='normal',required=True)
    continent = fields.Selection([('asia', 'Asia'), ('europe', 'Europe'), ('america', 'America'), ('australia', 'Australia')], default='asia', string='Area',required=True)	
    country = fields.Many2one('res.country', string='Country',required=True)
    website1 = fields.Char(string='Website', required=True)
    website2 = fields.Char(string='Website2')
    email1 = fields.Char(string='Email')
    email2 = fields.Char(string='Email2')	
    tel1 = fields.Char(string='Tel')
    tel2 = fields.Char(string='Tel2')	
    address = fields.Char(string='Address', translate=True)	