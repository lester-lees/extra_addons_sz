# -*- encoding: utf-8 -*-
{
    'name': 'Loewie 电商接口 SZ',
    'version': '1.0',
    "category" : "Sales",
    'description': """ Loewie 电商接口 SZ""",
    'author': 'OSCG',
    'website': 'http://www.loewie.com',
    'depends': ['sale', 'product', 'stock','stock_picking_loewie','deliver_status_loewie'],
    'init_xml': [],
    'data': [
        'update_view.xml',
        'stock_picklist_tmijdi.xml',
        'stock_picklist_daifa.xml',
        'security.xml',		
     ],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'application': True,
}