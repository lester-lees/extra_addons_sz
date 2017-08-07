# -*- coding: utf-8 -*-
{
    'name': 'Loewie Optimize Warehouse Operations',
    'version': '1.0',
    'author': 'Jimmy.Lee',
    'summary': 'Loewie Optimize Warehouse Operations',
    'description': """
       Loewie Optimize Warehouse Operations	
    """,
    'website': 'http://www.loewie.com',
    'depends': ['stock','product','stock_picking_loewie'],
    'category': 'Loewie',
    "update_xml": ["product_product_report_yesterday.xml",'warehouse_loewie.xml','product_product_report_today.xml'],	
    'installable': True,
    'application': False,
    'auto_install': False,
}