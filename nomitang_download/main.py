# -*- coding: utf-8 -*-
import logging
import werkzeug
import openerp
from openerp import SUPERUSER_ID
from openerp import http
from openerp import tools
from openerp.http import request
from openerp.tools.translate import _
from openerp.addons.website.models.website import slug

PPG = 9 # Products Per Page
PPR = 3  # Products Per Row

_logger = logging.getLogger(__name__)

class table_compute(object):
    def __init__(self):
        self.table = {}

    def _check_place(self, posx, posy, sizex, sizey):
        res = True
        for y in range(sizey):
            for x in range(sizex):
                if posx+x>=PPR:
                    res = False
                    break
                row = self.table.setdefault(posy+y, {})
                if row.setdefault(posx+x) is not None:
                    res = False
                    break
            for x in range(PPR):
                self.table[posy+y].setdefault(x, None)
        return res

    def process(self, products, ppg=PPG):
        # Compute products positions on the grid
        minpos = 0
        index = 0
        maxy = 0
        for p in products:
            x = min(max(p.website_size_x, 1), PPR)
            y = min(max(p.website_size_y, 1), PPR)
            if index>=ppg:
                x = y = 1

            pos = minpos
            while not self._check_place(pos%PPR, pos/PPR, x, y):
                pos += 1
            # if 21st products (index 20) and the last line is full (PPR products in it), break
            # (pos + 1.0) / PPR is the line where the product would be inserted
            # maxy is the number of existing lines
            # + 1.0 is because pos begins at 0, thus pos 20 is actually the 21st block
            # and to force python to not round the division operation
            if index >= ppg and ((pos + 1.0) / PPR) > maxy:
                break

            if x==1 and y==1:   # simple heuristic for CPU optimization
                minpos = pos/PPR

            for y2 in range(y):
                for x2 in range(x):
                    self.table[(pos/PPR)+y2][(pos%PPR)+x2] = False
            self.table[pos/PPR][pos%PPR] = {
                'product': p, 'x':x, 'y': y,
                'class': " ".join(map(lambda x: x.html_class or '', p.website_style_ids))
            }
            if index<=ppg:
                maxy=max(maxy,y+(pos/PPR))
            index += 1

        # Format table according to HTML needs
        rows = self.table.items()
        rows.sort()
        rows = map(lambda x: x[1], rows)
        for col in range(len(rows)):
            cols = rows[col].items()
            cols.sort()
            x += len(cols)
            rows[col] = [c for c in map(lambda x: x[1], cols) if c != False]

        return rows

class QueryURL(object):
    def __init__(self, path='', **args):
        self.path = path
        self.args = args

    def __call__(self, path=None, **kw):
        if not path:
            path = self.path
        for k,v in self.args.items():
            kw.setdefault(k,v)
        l = []
        for k,v in kw.items():
            if v:
                if isinstance(v, list) or isinstance(v, set):
                    l.append(werkzeug.url_encode([(k,i) for i in v]))
                else:
                    l.append(werkzeug.url_encode([(k,v)]))
        if l:
            path += '?' + '&'.join(l)
        return path

class Loewie_Download_Ctl(http.Controller):
    """    
    @http.route('/web/login', type='http', auth="none")
    def web_login(self, redirect=None, **kw):
        #ensure_db()
        request.params['login_success'] = False
        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return http.redirect_with_hash(redirect)

        if not request.uid:
            request.uid = openerp.SUPERUSER_ID

        values = request.params.copy()
        try:
            values['databases'] = http.db_list()
        except openerp.exceptions.AccessDenied:
            values['databases'] = None
 
        values['error'] = _("Please Login to See our download resources.")
        return request.render('web.login', values) """

    @http.route([
        '/downloads',
        '/downloads/<model("res.users"):user>', 		
        '/downloads/page/<int:page>',
        '/downloads/category/<model("download.category"):category>',
        '/downloads/category/<model("download.category"):category>/page/<int:page>'
    ], type='http', auth="user", website=True)
    def downloads(self, page=0, category=None, search='', ppg=False, **post):
	
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry		
        user_obj = pool['res.users'].browse(cr,uid,[uid],context=context)
        #if not user_obj.active :
        #    request.params['error'] = _("Please Login to See our download resources.")		
        #    return request.redirect('/web/login')		
		
		
        category_obj = pool['download.category']
        category_ids = category_obj.search(cr, uid, [('parent_id', '=', False)], context=context)
        categories = category_obj.browse(cr, uid, category_ids, context=context).sorted(key=lambda x:x.sequence)	
        download_obj = pool.get('loewie.download')
        if category and category.name == 'All Downloads' :
            category=None
			
        keep = QueryURL('/downloads', category=category and int(category), search=search)		
		
        url = "/downloads"		
        category_ids = []
        if category:
            category_ids.append(category.id)
            url = "/downloads/category/%s" % slug(category)			
            for categ in category.child_id:
                category_ids.append(categ.id)
				
        domain = []
        if category_ids : domain = [('category_id','in',category_ids or [1])]	
		
        if search :            
            for srch in search.split(" "):
                domain += [('name', 'ilike', srch)]
					
        download_count = download_obj.search_count(cr, uid, domain, context=context)
        pager = request.website.pager(url=url, total=download_count, page=page, step=9, scope=7, url_args=post)
        download_ids = download_obj.search(cr, uid, domain, limit=9, offset=pager['offset'], context=context) # order=self._get_search_order(post),
        #download_ids = download_obj.search(cr, uid, domain, context=context)		
        downloads = download_obj.browse(cr, uid, download_ids, context=context)

		
        parent_category_ids = []		
        if category:	
            parent_category_ids = [category.id]
            current_category = category
            while current_category.parent_id:
                parent_category_ids.append(current_category.parent_id.id)
                current_category = current_category.parent_id		
		
        values = {
            'search': search, 
            'categories': categories,
            'category': category,			
            'parent_category_ids':parent_category_ids, 				
            'keep': keep,			
            'pager': pager,
            'downloads': downloads,
            #'bins': table_compute().process(downloads, ppg), 
            'rows': 3,
        }

		
        return request.website.render("nomitang_download.downloads_tmpl", values)
	
		
    @http.route(['/downloads/download/<model("loewie.download"):download>', '/downloads/download/<model("res.users"):user>', ], type='http', auth="user", website=True)
    def download(self, download, category='', search='', **kwargs):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        user_obj = pool['res.users'].browse(cr,uid,[uid],context=context)
        #if not user_obj.active :
        #    return request.redirect('/website/login')		
			
        #domain = []		
        if search : request.redirect(request.httprequest.referrer or '/downloads')           
            #for srch in search.split(" "):
            #    domain += [('name', 'ilike', srch)]		
		
		
        category_obj = pool['download.category']
        download_obj = pool['loewie.download']

        context.update(active_id=download.id)

        if category:
            category = category_obj.browse(cr, uid, int(category), context=context)
            category = category if category.exists() else False

				
        category_ids = category_obj.search(cr, uid, [('parent_id', '=', False)], context=context)
        categories = category_obj.browse(cr, uid, category_ids, context=context).sorted(key=lambda x:x.sequence)
        keep = QueryURL('/downloads', category=category and category.id, search=search)
		
        parent_category_ids = []		
        if category:	
            parent_category_ids = [category.id]
            current_category = category
            while current_category.parent_id:
                parent_category_ids.append(current_category.parent_id.id)
                current_category = current_category.parent_id	
	
        values = {
            'search': search,
            'categories': categories,
            'category': category,		
            'parent_category_ids':parent_category_ids,			
            'main_object': download,
            'keep': keep,			
        }
        return request.website.render("nomitang_download.download_tmpl", values)
		