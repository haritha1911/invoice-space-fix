# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, Command, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError, MissingError
from odoo import http, _
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from collections import OrderedDict
from odoo.http import request
import num2words


class SaleOrders(models.Model):
    _name = 'sale.order'
    _inherit = ["sale.order", "approval.thread"]
    _description = 'Sale Order'

    country_id = fields.Many2one(related='partner_shipping_id.country_id', string='Country',)
    place_of_supply = fields.Many2one('res.country.state', string="Place of supply")

    
    """
        https://timesheet.odoo.com/web?debug=1#id=824&cids=1&menu_id=112&action=184&active_id=2&model=project.task&view_type=form
        -- place of supply should be editable and no need to set related with partner_shipping_id.state_id.id
    """
    # if self.partner_invoice_id.country_id.code == 'IN':
    # if self.company_id and self.company_id.place_of_supply_config:
    #     if self.partner_invoice_id and self.partner_invoice_id.state_id and self.partner_invoice_id.state_id.id:
    #         self.write({'place_of_supply': self.partner_invoice_id.state_id.id})
    # else:
    #     if self.partner_shipping_id and self.partner_shipping_id.state_id and self.partner_shipping_id.state_id.id:
    #         self.write({'place_of_supply': self.partner_shipping_id.state_id.id})
        
    # if self.company_id and self.company_id.fiscal_position_config:
    #     if self.partner_invoice_id and self.partner_invoice_id.state_id and self.partner_invoice_id.state_id.id:
    #         fiscal_id = self.env['account.fiscal.position'].with_company(
    #                 self.company_id
    #             )._get_fiscal_position(self.partner_id, self.partner_invoice_id).id
            
    #         self.write({'fiscal_position_id':fiscal_id})
    #         for line in self.order_line:
    #             line._compute_tax_id()
    #         self.action_update_shipping()
    # else:
    #     if self.partner_shipping_id and self.partner_shipping_id.state_id and self.partner_shipping_id.state_id.id:
    #         fiscal_id = self.env['account.fiscal.position'].with_company(
    #                 self.company_id
    #             )._get_fiscal_position(self.partner_id, self.partner_shipping_id).id
    #         self.write({'fiscal_position_id':fiscal_id})
    #         for line in self.order_line:
    #             line._compute_tax_id()
    #         self.action_update_shipping()


    # madhu anna confirmed we need to revert this changes in pilot and staging server.

    # @api.onchange('partner_shipping_id','partner_invoice_id','company_id')
    # def update_place_of_supply(self):

    #     if self.partner_invoice_id.country_id.code == 'IN':
    #         if self.company_id and self.company_id.place_of_supply_config:
    #             if self.partner_invoice_id and self.partner_invoice_id.state_id and self.partner_invoice_id.state_id.id:
    #                 self.write({'place_of_supply': self.partner_invoice_id.state_id.id})
    #         else:
    #             if self.partner_shipping_id and self.partner_shipping_id.state_id and self.partner_shipping_id.state_id.id:
    #                 self.write({'place_of_supply': self.partner_shipping_id.state_id.id})


    #         if self.company_id and self.company_id.fiscal_position_config:
    #             if self.partner_invoice_id and self.partner_invoice_id.state_id and self.partner_invoice_id.state_id.id:
    #                 fiscal_id = self.env['account.fiscal.position'].with_company(
    #                         self.company_id
    #                     )._get_fiscal_position(self.partner_id, self.partner_invoice_id).id
                    
    #                 self.write({'fiscal_position_id':fiscal_id})
    #                 for line in self.order_line:
    #                     line._compute_tax_id()
    #                 self.action_update_shipping()
    #         else:
    #             if self.partner_shipping_id and self.partner_shipping_id.state_id and self.partner_shipping_id.state_id.id:
    #                 fiscal_id = self.env['account.fiscal.position'].with_company(
    #                         self.company_id
    #                     )._get_fiscal_position(self.partner_id, self.partner_shipping_id).id
    #                 self.write({'fiscal_position_id':fiscal_id})
    #                 for line in self.order_line:
    #                     line._compute_tax_id()
    #                 self.action_update_shipping()

    # def _onchange_custom_partner_shipping_id(self):
    #     stock_picking_obj = self.env['stock.picking'].sudo()
    #     pickings = self.picking_ids.filtered(
    #         lambda p: p.state not in ['done', 'cancel'] and p.partner_id != self.partner_shipping_id
    #     )

    #     if self.company_id and self.company_id.fiscal_position_config:
    #         self.fiscal_position_id = self.env['account.fiscal.position']._get_fiscal_position \
    #             (self.partner_id, self.partner_invoice_id)
    #     else:
    #         self.fiscal_position_id = self.env['account.fiscal.position']._get_fiscal_position \
    #             (self.partner_id, self.partner_shipping_id)
                
    #     if pickings:
    #         stock_picking_obj.sudo().browse(pickings.ids).write({'partner_id': self.partner_shipping_id.id})


    def _get_proforma_invoice_filename(self):
        """ Using this function we can set report file name"""
        filename = self.name.replace("/", "_") + "ProformaInvoice.pdf"
        return filename

    def amount_total_words_india(self, sale_id):
        """ amount based on the Indianized """


        amt = round(sale_id.amount_total, 2)

        if sale_id.currency_id.name == 'INR':
            wrd = "Rupees {0} and {1} paise".format(num2words.num2words(str(amt).split('.')[0], lang='en_IN'),
                                                    num2words.num2words(str(amt).split('.')[1], lang='en_IN'))
        else:
            # https://timesheet.odoo.com/web#id=1358&cids=1&menu_id=170&action=198&model=project.task&view_type=form
            # For Export sale order proforma invoice amount in words should come based on currency.
            
            wrd = sale_id.currency_id.amount_to_text(amt)


        return wrd.title()

    def _prepare_invoice(self):
        """ using it we can set dispatched partner id """

        invoice_vals = super(SaleOrders, self)._prepare_invoice()

        dispatched_partner_id = False

        if self.warehouse_id and self.warehouse_id.partner_id:
            dispatched_partner_id = self.warehouse_id.partner_id.id
        invoice_vals.update({
            'dispatched_partner_id': dispatched_partner_id

        })

        return invoice_vals

    def button_sign_invoice(self, custom_invoice_report_id=None):
        invoice_report_id = self.env.ref('sale.action_report_pro_forma_invoice')
        return super(SaleOrders, self).button_sign_invoice(invoice_report_id)