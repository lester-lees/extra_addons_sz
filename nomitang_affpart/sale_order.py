# -*- coding: utf-8 -*-
# request.csrf_token()
from openerp.osv import osv, orm, fields
from openerp import SUPERUSER_ID
from openerp.addons.web.http import request

class sale_order(osv.Model):
    _inherit = "sale.order"
	
    _columns = {
        'session_id': fields.char(string='Session ID', readonly=True),
        'is_sent_tracking_code': fields.boolean(string="Sent Shareasale Code?", readonly=True),		
    }		
	
class website(orm.Model):
    _inherit = 'website'	
    def sale_get_order(self, cr, uid, ids, force_create=False, code=None, update_pricelist=False, force_pricelist=False, context=None):
        """ Return the current sale order after mofications specified by params.

        :param bool force_create: Create sale order if not already existing
        :param str code: Code to force a pricelist (promo code)
                         If empty, it's a special case to reset the pricelist with the first available else the default.
        :param bool update_pricelist: Force to recompute all the lines from sale order to adapt the price with the current pricelist.
        :param int force_pricelist: pricelist_id - if set,  we change the pricelist with this one

        :returns: browse record for the current sale order
        """
        partner = self.get_partner(cr, uid)
        sale_order_obj = self.pool['sale.order']
        sale_order_id = request.session.get('sale_order_id')
        if not sale_order_id:
            last_order = partner.last_website_so_id
            available_pricelists = self.get_pricelist_available(cr, uid, context=context)
            # Do not reload the cart of this user last visit if the cart is no longer draft or uses a pricelist no longer available.
            sale_order_id = last_order and last_order.state == 'draft' and last_order.pricelist_id in available_pricelists and last_order.id

        sale_order = None
        # Test validity of the sale_order_id
        if sale_order_id and sale_order_obj.exists(cr, SUPERUSER_ID, sale_order_id, context=context):
            sale_order = sale_order_obj.browse(cr, SUPERUSER_ID, sale_order_id, context=context)
        else:
            sale_order_id = None
        pricelist_id = request.session.get('website_sale_current_pl') or self.get_current_pricelist(cr, uid, context=context).id

        if force_pricelist and self.pool['product.pricelist'].search_count(cr, uid, [('id', '=', force_pricelist)], context=context):
            pricelist_id = force_pricelist
            request.session['website_sale_current_pl'] = pricelist_id
            update_pricelist = True

        # create so if needed
        if not sale_order_id and (force_create or code):
            # TODO cache partner_id session
            user_obj = self.pool['res.users']
            affiliate_id = request.session.get('affiliate_id')
            salesperson_id = affiliate_id if user_obj.exists(cr, SUPERUSER_ID, affiliate_id, context=context) else request.website.salesperson_id.id
            for w in self.browse(cr, uid, ids):
                addr = partner.address_get(['delivery', 'invoice'])
                values = {
                    'partner_id': partner.id,
                    'pricelist_id': pricelist_id,
                    'payment_term_id': partner.property_payment_term_id.id if partner.property_payment_term_id else False,
                    'team_id': w.salesteam_id.id,
                    'partner_invoice_id': addr['invoice'],
                    'partner_shipping_id': addr['delivery'],
                    'user_id': salesperson_id or w.salesperson_id.id,
                    'session_id': request.session.sid,					
                }
                sale_order_id = sale_order_obj.create(cr, SUPERUSER_ID, values, context=context)
                request.session['sale_order_id'] = sale_order_id
                sale_order = sale_order_obj.browse(cr, SUPERUSER_ID, sale_order_id, context=context)

                if request.website.partner_id.id != partner.id:
                    self.pool['res.partner'].write(cr, SUPERUSER_ID, partner.id, {'last_website_so_id': sale_order_id})

        if sale_order_id:

            # check for change of pricelist with a coupon
            pricelist_id = pricelist_id or partner.property_product_pricelist.id

            # check for change of partner_id ie after signup
            if sale_order.partner_id.id != partner.id and request.website.partner_id.id != partner.id:
                flag_pricelist = False
                if pricelist_id != sale_order.pricelist_id.id:
                    flag_pricelist = True
                fiscal_position = sale_order.fiscal_position_id and sale_order.fiscal_position_id.id or False

                # change the partner, and trigger the onchange
                sale_order_obj.write(cr, SUPERUSER_ID, [sale_order_id], {'partner_id': partner.id}, context=context)
                sale_order_obj.onchange_partner_id(cr, SUPERUSER_ID, [sale_order_id], context=context)

                # check the pricelist : update it if the pricelist is not the 'forced' one
                values = {}
                if sale_order.pricelist_id:
                    if sale_order.pricelist_id.id != pricelist_id:
                        values['pricelist_id'] = pricelist_id
                        update_pricelist = True

                # if fiscal position, update the order lines taxes
                if sale_order.fiscal_position_id:
                    sale_order._compute_tax_id()

                # if values, then make the SO update
                if values:
                    sale_order_obj.write(cr, SUPERUSER_ID, [sale_order_id], values, context=context)

                # check if the fiscal position has changed with the partner_id update
                recent_fiscal_position = sale_order.fiscal_position_id and sale_order.fiscal_position_id.id or False
                if flag_pricelist or recent_fiscal_position != fiscal_position:
                    update_pricelist = True

            if code and code != sale_order.pricelist_id.code:
                pricelist_ids = self.pool['product.pricelist'].search(cr, uid, [('code', '=', code)], limit=1, context=context)
                if pricelist_ids:
                    pricelist_id = pricelist_ids[0]
                    update_pricelist = True
            elif code is not None and sale_order.pricelist_id.code:
                # code is not None when user removes code and click on "Apply"
                pricelist_id = partner.property_product_pricelist.id
                update_pricelist = True

            # update the pricelist
            if update_pricelist:
                request.session['website_sale_current_pl'] = pricelist_id
                values = {'pricelist_id': pricelist_id}
                sale_order.write(values)
                for line in sale_order.order_line:
                    if line.exists():
                        sale_order._cart_update(product_id=line.product_id.id, line_id=line.id, add_qty=0)

            # update browse record
            if (code and code != sale_order.pricelist_id.code) or sale_order.partner_id.id != partner.id or force_pricelist:
                sale_order = sale_order_obj.browse(cr, SUPERUSER_ID, sale_order.id, context=context)

        else:
            request.session['sale_order_id'] = None
            return None

        return sale_order		