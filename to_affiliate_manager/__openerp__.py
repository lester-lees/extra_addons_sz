# -*- coding: utf-8 -*-

{
    'name' : 'TO Affiliate Manager',
    'version': '2.0.8',
    'author' : 'T.V.T Marine Automation (aka TVTMA)',
    'website': 'http://ma.tvtmarine.com',
    'summary': 'Manage Affiliate code and commission',
    'sequence': 24,
    'category': 'Sales',
    'description':"""
Manage Affiliate code and commission
====================================

    """,
    'depends': ['website_sale', 'portal'],
    'data': [        
        'data/affiliate_data_view.xml',
        'data/update_record_rule.xml',
        'security/affiliate_security.xml',
        'security/ir.model.access.csv',
        'views/affiliate_views.xml',
        'views/website_template.xml',
        'views/sale_views.xml',
        'views/res_config_view.xml',
        'views/account_invoice_view.xml',
        'views/res_partner_view.xml',
        'views/product_view.xml',
        'views/res_company_form_view.xml',
        'wizard/affiliate_join_view.xml',
        'report/affiliate_report.xml',
        'report/sale_report.xml',
    ],
    'installable': True,
    'application': True,
}
