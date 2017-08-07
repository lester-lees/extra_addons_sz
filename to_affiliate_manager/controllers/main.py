# -*- coding: utf-8 -*-

from ..constants import AFFCODE_PARAM_NAME
from openerp import http
from openerp.http import request
from openerp import SUPERUSER_ID
import openerp.addons.website_sale.controllers.main
import openerp.addons.website.controllers.main
from openerp.addons.website.models.website import slug
from openerp.addons.website_sale.controllers.main import website_sale
from openerp.addons.website_portal.controllers.main import website_account
import werkzeug

def to_get_pricelist():
    cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
    sale_order = context.get('sale_order')
    if sale_order:
        return sale_order.pricelist_id
    else:
        affcode_cookie = request.httprequest.cookies.get(AFFCODE_PARAM_NAME)
        if affcode_cookie:
            affcode_id = pool['to.affiliate.code'].search(cr, SUPERUSER_ID, [('name', '=', affcode_cookie)], limit=1)
            if affcode_id:
                affcode = pool['to.affiliate.code'].browse(cr, SUPERUSER_ID, affcode_id, context=context)
                return affcode.partner_id.property_product_pricelist
        else:
            partner = pool['res.users'].browse(cr, SUPERUSER_ID, uid, context=context).partner_id
            return partner.property_product_pricelist

openerp.addons.website_sale.controllers.main.get_pricelist = to_get_pricelist

class website_affiliate_register(http.Controller):

    @http.route(['/affiliate/advertisement'], type='http', auth="user", website=True)
    def show_advertisement(self, **kwargs):
        env = request.env(user=SUPERUSER_ID)
        res_company = env['res.company'].search([])
        values = {}
        aff_code = False
        if user and user.partner_id.to_is_affiliate:
            aff_code = env['to.affiliate.code'].search([('partner_id', '=', user.partner_id.id)], limit=1)
        values.update(kwargs={'to_res_company': res_company, 'user': user, 'aff_code': aff_code})
        return request.website.render("to_affiliate_manager.to_affiliate_ad", values)       	
	
    @http.route(['/affiliate', '/affiliate/<model("res.users"):user>'], type='http', auth="user", website=True)
    def affiliate_register(self, user=None, **kwargs):
        env = request.env(user=SUPERUSER_ID)
        res_company = env['res.company'].search([])
        values = {}
        aff_code = False
        if user and user.partner_id.to_is_affiliate:
            aff_code = env['to.affiliate.code'].search([('partner_id', '=', user.partner_id.id)], limit=1)
        values.update(kwargs={'to_res_company': res_company, 'user': user, 'aff_code': aff_code})
        return request.website.render("to_affiliate_manager.to_affiliate", values)

    @http.route(['/affiliate/join'], type='http', auth="user", website=True)
    def join_affiliate(self, **kwargs):
        env = request.env(user=SUPERUSER_ID)
        user_id = kwargs.get('user', False)
        company_id = kwargs.get('to_res_company', False)
        super_user = env['res.users'].browse(SUPERUSER_ID)
        if not company_id or int(company_id) == 0:
            company_id = super_user.company_id.to_affcode_company.id
        if user_id:
            user = env['res.users'].browse(int(user_id))
            if not user.partner_id.to_is_affiliate:
                aff_code = env['to.affiliate.code'].create({
                    'partner_id': user.partner_id.id,
                    'company_id': company_id,
                    'website_id': request.website and request.website.id or False
                })
            return request.redirect('/affiliate/%s' % user_id, code=301)
        return request.redirect('/affiliate', code=301)

class Website(openerp.addons.website.controllers.main.Website):

    @http.route('/', type='http', auth="public", website=True)
    def index(self, **kw):
        res = super(Website, self).index(**kw)
        environ = request.httprequest.headers.environ
        http_referer = environ.get("HTTP_REFERER")
        if not http_referer : return res

        shareasale_index = http_referer.find('www.shareasale.com')        		
        if shareasale_index < 0: return res

        u_id = http_referer.find('U=')
        if not u_id : return res
        affiliate_num = http_referer[ u_id+2 : u_id+8 ]
 		
        affcode = kw.get(AFFCODE_PARAM_NAME, False)
        env = request.env(user=SUPERUSER_ID)	
        affcode_cookie = request.httprequest.cookies.get(AFFCODE_PARAM_NAME)
		
        if affcode:    
            if not affcode_cookie:
                user = env['res.users'].browse(SUPERUSER_ID)
                affiliate_code = env['to.affiliate.code'].search([('name', '=', affcode)], limit=1)
                if affiliate_code:
                    UserAgent = werkzeug.useragents.UserAgent(environ.get("HTTP_USER_AGENT"))
                    referrer_analysis = env['to.affiliate.referrer.analysis'].create({
                        'affcode_id': affiliate_code.id,
                        'name': affiliate_code.name,
                        'referrer': http_referer,
                        'ip': environ.get("REMOTE_ADDR"),
                        'browser': UserAgent.browser + ' / ' + UserAgent.version
                    })
                    res.set_cookie('referrer_analysis_id', str(referrer_analysis.id), max_age=user.company_id.to_affiliate_cookie_age)
                res.set_cookie(AFFCODE_PARAM_NAME, affcode, max_age=user.company_id.to_affiliate_cookie_age)
        return res

    """
    @http.route('/', type='http', auth="public", website=True)
    def index(self, **kw):
        res = super(Website, self).index(**kw)
        affcode = kw.get(AFFCODE_PARAM_NAME, False)
        if affcode:
            affcode_cookie = request.httprequest.cookies.get(AFFCODE_PARAM_NAME)
            if not affcode_cookie:
                env = request.env(user=SUPERUSER_ID)
                environ = request.httprequest.headers.environ
                user = env['res.users'].browse(SUPERUSER_ID)
                affiliate_code = env['to.affiliate.code'].search([('name', '=', affcode)], limit=1)
                if affiliate_code:
                    UserAgent = werkzeug.useragents.UserAgent(environ.get("HTTP_USER_AGENT"))
                    referrer_analysis = env['to.affiliate.referrer.analysis'].create({
                        'affcode_id': affiliate_code.id,
                        'name': affiliate_code.name,
                        'referrer': environ.get("HTTP_REFERER"),
                        'ip': environ.get("REMOTE_ADDR"),
                        'browser': UserAgent.browser + ' / ' + UserAgent.version
                    })
                    res.set_cookie('referrer_analysis_id', str(referrer_analysis.id), max_age=user.company_id.to_affiliate_cookie_age)
                res.set_cookie(AFFCODE_PARAM_NAME, affcode, max_age=user.company_id.to_affiliate_cookie_age)
        return res    """

class website_sale(website_sale):

    @http.route(['/shop/confirm_order'], type='http', auth="public", website=True)
    def confirm_order(self, **post):
        value = super(website_sale, self).confirm_order(**post)
        sale_order_id = request.session.get('sale_last_order_id')
        affcode_cookie = request.httprequest.cookies.get(AFFCODE_PARAM_NAME)
        referrer_analysis_id = request.httprequest.cookies.get('referrer_analysis_id')
        if sale_order_id:
            env = request.env(user=SUPERUSER_ID)
            sale_order = env['sale.order'].browse(sale_order_id)
            if affcode_cookie:
                affcode = env['to.affiliate.code'].search([('name', '=', affcode_cookie)], limit=1)
                if affcode:
                    affcodes = env['to.affiliate.code'].search([])
                    sale_orders = env['sale.order'].search([
                                                            ('to_affcode_id', 'in', [x.id for x in affcodes]),
                                                            ('partner_id', '=', sale_order.partner_id.id),
                                                            ('state', 'not in', ['draft', 'sent', 'cancel'])
                                                            ]
                                                           )
                    if not sale_orders:
                        sale_order.write({
                            'to_affcode_id': affcode.id,
                            'company_id': affcode.company_id.id,
                            'user_id': affcode.saleperson_id.id,
                            'to_referrer_analysis_id': referrer_analysis_id and int(referrer_analysis_id) or False
                        })
                        sale_order.partner_id.user_ids.write({'company_ids': [(6, 0, [affcode.company_id.id])], 'company_id': affcode.company_id.id})
                        sale_order.partner_id.write({'company_id': affcode.company_id.id})
            else:
                sale_order.write({'company_id': sale_order.partner_id.company_id and sale_order.partner_id.company_id.id or False})

        return value

#     @http.route(['/shop/confirmation'], type='http', auth="public", website=True)
#     def payment_confirmation(self, **post):
#         value = super(website_sale, self).payment_confirmation(**post)
#         sale_order_id = request.session.get('sale_last_order_id')
#         affcode_cookie = request.httprequest.cookies.get(AFFCODE_PARAM_NAME)
#         referrer_analysis_id = request.httprequest.cookies.get('referrer_analysis_id')
#         if sale_order_id:
#             env = request.env(user=SUPERUSER_ID)
#             sale_order = env['sale.order'].browse(sale_order_id)
#             if affcode_cookie:
#                 affcode = env['to.affiliate.code'].search([('name', '=', affcode_cookie)], limit=1)
#                 if affcode:
#                     affcodes = env['to.affiliate.code'].search([])
#                     sale_orders = env['sale.order'].search([('to_affcode_id', 'in', [x.id for x in affcodes]), ('partner_id', '=', sale_order.partner_id.id)])
#                     if not sale_orders:
#                         sale_order.write({
#                             'to_affcode_id': affcode.id,
#                             'company_id': affcode.company_id.id,
#                             'user_id': affcode.saleperson_id.id,
#                             'to_referrer_analysis_id': referrer_analysis_id and int(referrer_analysis_id) or False
#                         })
#                         sale_order.partner_id.user_ids.write({'company_ids': [(6, 0, [affcode.company_id.id])], 'company_id': affcode.company_id.id})
#                         sale_order.partner_id.write({'company_id': affcode.company_id.id})
#             else:
#                 sale_order.write({'company_id': sale_order.partner_id.company_id and sale_order.partner_id.company_id.id or False})
#
#         return value

    def checkout_parse(self, address_type, data, remove_prefix=False):
        values = super(website_sale, self).checkout_parse(address_type, data, remove_prefix=remove_prefix)
        affcode_cookie = request.httprequest.cookies.get(AFFCODE_PARAM_NAME)
        if affcode_cookie:
            env = request.env(user=SUPERUSER_ID)
            affcode = env['to.affiliate.code'].search([('name', '=', affcode_cookie)], limit=1)
            if affcode:
                values.update({'to_affcode_id': affcode.id})
        return values
