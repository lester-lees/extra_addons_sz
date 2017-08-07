# -*- coding: utf-8 -*-
from openerp import http
from openerp.http import request
from openerp.addons.website.models.website import slug

class website_offlinestore(http.Controller):

    @http.route(['/thanks',], type='http', auth="public", website=True)
    def thanks(self, **post):
		
        return request.website.render("nomitang_affpart.nt_thanks_website_view", {'url':''}) 
