# -*- coding: utf-8 -*-
import openerp
from openerp.osv import orm, osv, fields
from openerp import models
from openerp.http import request

class res_lang(osv.osv):
    _inherit="res.lang"

    _columns={
        'flag_image': fields.binary('Flag img', oldname='content_image'),
        'img_src':fields.char(string='Image Path'),		
    }

	
class website(osv.osv):
    _inherit="website"

    @openerp.tools.ormcache(skiparg=3)
    def _get_languages(self, cr, uid, id, context=None):
        website = self.browse(cr, uid, id)
        return [(lg.code, lg.name, lg.iso_code,lg.img_src) for lg in website.language_ids]

    def get_languages(self, cr, uid, ids, context=None):
        return self._get_languages(cr, uid, ids[0], context=context)
		
    def get_alternate_languages(self, cr, uid, ids, req=None, context=None):
        langs = []
        if req is None:
            req = request.httprequest
        default = self.get_current_website(cr, uid, context=context).default_lang_code
        shorts = []

        def get_url_localized(router, lang):
            arguments = dict(request.endpoint_arguments)
            for k, v in arguments.items():
                if isinstance(v, orm.browse_record):
                    arguments[k] = v.with_context(lang=lang)
            return router.build(request.endpoint, arguments)
        router = request.httprequest.app.get_db_router(request.db).bind('')
        for code, name, l, src in self.get_languages(cr, uid, ids, context=context):
            lg_path = ('/' + code) if code != default else ''
            lg = code.split('_')
            shorts.append(lg[0])
            uri = request.endpoint and get_url_localized(router, code) or request.httprequest.path
            if req.query_string:
                uri += '?' + req.query_string
            lang = {
                'hreflang': ('-'.join(lg)).lower(),
                'short': lg[0],
                'href': req.url_root[0:-1] + lg_path + uri,
            }
            langs.append(lang)
        for lang in langs:
            if shorts.count(lang['short']) == 1:
                lang['hreflang'] = lang['short']
        return langs		
	

class ir_http(models.AbstractModel):
    _inherit = 'ir.http'

    def get_nearest_lang(self, lang):
        # Try to find a similar lang. Eg: fr_BE and fr_FR
        short = lang.partition('_')[0]
        short_match = False
        for code, name, l, src in request.website.get_languages():
            if code == lang:
                return lang
            if not short_match and code.startswith(short):
                short_match = code
        return short_match			