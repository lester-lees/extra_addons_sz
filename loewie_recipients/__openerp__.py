# -*- coding: utf-8 -*-
{
    'name': 'Loewie recipients Management',
    'version': '1.0',
    'author': 'Jimmy.Lee',
    'summary': 'Loewie recipients Management',
    'description': """
       Loewie recipients Management	
    """,
    'website': 'http://www.loewie.com',
    'depends': ['sale','stock','sale_stock'],
    'category': 'Loewie',
    "update_xml": ["loewie_recipients.xml","security/ir.model.access.csv"],	
    'installable': True,
    'application': False,
    'auto_install': False,
}