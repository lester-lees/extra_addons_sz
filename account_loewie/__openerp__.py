# -*- coding: utf-8 -*-
{
    'name': 'Loewie Account',
    'version': '1.0',
    'author': 'Jimmy.Lee',
    'summary': 'Loewie Account',
    'description': """
      Loewie Account
    """,
    "depends": [
        "base", "account","stock","sale","report_webkit"
    ],	
    'website': 'http://www.loewie.com',
    'category': 'Loewie',
    "update_xml": ["account_view.xml","sale_contract_report.xml"],	
    'installable': True,
    'application': False,
    'auto_install': False,
}