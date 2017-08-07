# -*- coding: utf-8 -*-
from openerp import http
from openerp.http import request
from openerp.addons.website.models.website import slug

class website_offlinestore(http.Controller):

    @http.route([
        '/offlinestore',
    ], type='http', auth="public", website=True)
    def offlinestore(self, **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        statement = "select n.id from nt_offlinestore n left join res_country r on n.country=r.id order by n.type desc,n.continent asc,r.name asc,n.name asc"	
        cr.execute(statement)	
        store_ids = [element[0] for element in cr.fetchall() ]		
        #store_ids = pool.get('nt.offlinestore').search(cr, uid, domain=[],order="order by ", context=context)			
        stores = pool.get('nt.offlinestore').browse(cr, uid, store_ids, context=context)		
	
        values = {
            'stores': stores,
        }
        return "Your Ip Address Is :%s" % request.httprequest.environ['REMOTE_ADDR'] 		
        #return "Your Ip Address Is :%s, and the real ip address is :%s." % (request.httprequest.environ['REMOTE_ADDR'], request.httprequest.environ['HTTP_X_REAL_IP'])
        #return request.website.render("nomitang_offlinestore.nt_offlinestore_website_view", values)	
		
	
    @http.route('/sendus-message', type='json', website=True, auth="public")
    def sendus_message(self, name, email, subject, message, **post):
        cr, uid, context = request.cr, request.uid, request.context
 		
        mail_obj = request.registry['mail.mail']
        vals = {    
                    'state':'outgoing',
                    'subject':'Message From Customer on NT Website ',						 
                    'body_html': '<pre>Name:<br/>%s<br/><br/> Email:<br/>%s<br/><br/>Subject:<br/>%s<br/><br/>Message:<br/>%s</pre>' % (name or '',email or '', subject or '', message or ''),
                    #'email_to': 'jimmy.lee@loewie.com',						 
                    'email_to':'jimmy.lee@loewie.com,arnd.krusche@loewie.com,anja.wang@loewie.com,bob.wang@loewie.com',
                    'email_from': 'info@nomitang.com',
                }
        mail_id = mail_obj.create(cr, uid, vals, context=context)
        if mail_id : mail_obj.send(cr, uid, [mail_id], context=context)		
        return True	