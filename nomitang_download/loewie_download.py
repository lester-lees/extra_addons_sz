# -*- coding: utf-8 -*-
import logging
from openerp import tools, api, fields, models, _
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)

class download_category(models.Model):
    _name = "download.category"
    _inherit = ["website.seo.metadata"]

    name = fields.Char(string="Name")
    parent_id = fields.Many2one('download.category', string="Parent Category")
    child_id = fields.One2many('download.category', 'parent_id', string="Children")
    sequence = fields.Integer('Sequence')
    description = fields.Text(string="Description")	
    #child_ids = fields.One2many('download.category', 'parent_id', string="Children")	
	
class loewie_download(models.Model):	
    _name = "loewie.download"
    _order = "sequence asc, id asc, name asc"
	
    name = fields.Char(string="Name")
    sequence = fields.Integer('Sequence')	
    type = fields.Selection([('Video', 'Video'), ('Photo', 'Photo'), ('Factsheet', 'Factsheet'), ('Banner', 'Banner'), ('Lifestyle', 'Lifestyle')], string="Type")	
    category_parent_id = fields.Many2one('download.category', string='Category Parent')	
    category_id = fields.Many2one('download.category', string='Category')	
    link = fields.Char(string="Link")
    image = fields.Binary("Image", attachment=True,
        help="This field holds the image used as image for the category, limited to 1024x1024px.")
    image_medium = fields.Binary("Medium-sized image", attachment=True,
        help="Medium-sized image of the category. It is automatically "\
             "resized as a 128x128px image, with aspect ratio preserved. "\
             "Use this field in form views or some kanban views.")
    image_small = fields.Binary("Small-sized image", attachment=True,
        help="Small-sized image of the category. It is automatically "\
             "resized as a 64x64px image, with aspect ratio preserved. "\
             "Use this field anywhere a small image is required.")
			 
		
    @api.model
    def create(self, vals):
        tools.image_resize_images(vals)
        return super(loewie_download, self).create(vals)

    @api.multi
    def write(self, vals):
        tools.image_resize_images(vals)
        return super(loewie_download, self).write(vals)			 