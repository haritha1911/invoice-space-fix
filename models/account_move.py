# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, Command, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError, MissingError
from odoo import http, _
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from collections import OrderedDict
from odoo.http import request
import num2words
import math
import ast


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'


    def _is_invoice_report(self, report_ref):
        return self._get_report(report_ref).report_name in ('isha_invoice_report_format.custom_account_invoices','account.report_invoice_with_payments', 'account.report_invoice')



class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    
    no_of_days = fields.Float("No. of Days")

    def get_analytic_distribution_account_move_line(self):
        analytic_distribution = []
        for record in self:
            if record.analytic_distribution:
                for key, value in record.analytic_distribution.items():
                    data = key.split(',')
                    for i in data:
                        analytic_distribution.append({
                            'keys': (int(i)),
                            'values': value,
                        })
        return analytic_distribution


class AccountJournal(models.Model):
    _inherit = "account.journal"


    enable_shipping_add = fields.Boolean('Enable Shipping Address')
    enable_dispatch_add = fields.Boolean('Enable Dispatch Address')

    
    # https://timesheet.odoo.com/web#id=897&cids=1&menu_id=112&action=184&active_id=4&model=project.task&view_type=form
    # Add Lognote while creating account journal
    @api.model_create_multi
    def create(self, vals_list):
        res = super(AccountJournal, self).create(vals_list)
        res.message_post(body=_("Account Journal Created"))
        return res
    
class AccountMove(models.Model):
    _inherit = "account.move"

    dispatched_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Dispatched Address',
        check_company=True,
    )
    donner_info = fields.Text(string="Donor", readonly=True)
    is_debit_note = fields.Boolean("Debit Note")
    
    
    @api.model_create_multi
    def create(self, values):
        record = super(AccountMove, self).create(values)
        analytic_account_list = []
        for rec in record:
            for inv_line in rec.invoice_line_ids:
                if inv_line.analytic_distribution:
                    keys = list(inv_line.analytic_distribution.keys())
                    analytic_account_list.extend([int(val) for key in keys for val in key.split(',')])
        analytic_account_object = self.env['account.analytic.account'].search_read(
            [('id', 'in', analytic_account_list), ('plan_id', 'ilike', 'Donor')], fields=["name"])
        if analytic_account_object:
            donner_name = ", ".join([item['name'] for item in analytic_account_object])
            rec.update({'donner_info': donner_name})
        return record

    def write(self, values):
        analytic_account_list = []
        res = super(AccountMove, self).write(values)
        if "invoice_line_ids" in values and values["invoice_line_ids"]:
            for inv_lines in self.invoice_line_ids:
                if inv_lines.analytic_distribution:
                    keys = list(inv_lines.analytic_distribution.keys())
                    analytic_account_list.extend([int(val) for key in keys for val in key.split(',')])
        analytic_account_object = self.env['account.analytic.account'].search_read(
            [('id', 'in', analytic_account_list), ('plan_id', 'ilike', 'Donor')], fields=["name"])
        if analytic_account_object:
            donner_name = ", ".join([item['name'] for item in analytic_account_object])
            self.update({'donner_info': donner_name})
        return res

    # l10n_in_state_id = fields.Many2one('res.country.state', string="Place of supply", compute='none',store=True, readonly=False)

    """
        https://timesheet.odoo.com/web?debug=1#id=824&cids=1&menu_id=112&action=184&active_id=2&model=project.task&view_type=form
        -- place of supply should be editable and no need to set related with partner_shipping_id.state_id.id
    """
    # madhu anna confirmed we need to revert this changes in pilot and staging server.
    
    # @api.onchange('partner_id','partner_shipping_id','company_id')
    # def update_l10n_in_state_id(self):
    #     if self.partner_id.country_id.code == 'IN':
    #         if self.company_id and self.company_id.place_of_supply_config:
    #             if self.partner_id and self.partner_id.state_id and self.partner_id.state_id.id:
    #                 self.write({'l10n_in_state_id': self.partner_id.state_id.id})
    #         else:
    #             if self.partner_shipping_id and self.partner_shipping_id.state_id and self.partner_shipping_id.state_id.id:
    #                 self.write({'l10n_in_state_id': self.partner_shipping_id.state_id.id})

    #         if self.company_id and self.company_id.fiscal_position_config:
    #             if self.partner_id and self.partner_id.state_id and self.partner_id.state_id.id:
    #                 fiscal_id = self.env['account.fiscal.position'].with_company(
    #                         self.company_id
    #                     )._get_fiscal_position(self.partner_id, self.partner_id)
    #                 self.fiscal_position_id = fiscal_id.id
                    
    #         else:
    #             if self.partner_shipping_id and self.partner_shipping_id.state_id and self.partner_shipping_id.state_id.id:
    #                 fiscal_id = self.env['account.fiscal.position'].with_company(
    #                         self.company_id
    #                     )._get_fiscal_position(self.partner_id, self.partner_shipping_id).id
    #                 self.write({'fiscal_position_id':fiscal_id})

    # def action_post(self):
    #     for order in self:
    #         order.action_update_fpos_values()
    #     return super(AccountMove, self).action_post()


    # @api.depends('partner_id', 'company_id')
    # def _compute_l10n_in_state_id(self):
    #     super(AccountMove, self)._compute_l10n_in_state_id()
    #     for move in self:
    #         # Avoid NewIds issue by browsing for self.ids.
    #         moves = self.with_context(prefetch_fields=False).browse(self.ids)
    #         order_id = self.env['sale.order'].search([('invoice_ids','in',moves.ids)])
    #         module_obj = self.env['ir.module.module']
    #         l10n_in = module_obj.sudo().search([('name', '=', 'l10n_in'), ('state', '=', 'installed')])
    #         if l10n_in:
    #             for order in order_id:
    #                 if order and move.company_id and move.company_id.place_of_supply_config:
    #                     move.l10n_in_state_id = move.partner_id.state_id.id
    #                 else:
    #                     move.l10n_in_state_id = move.partner_shipping_id.state_id.id
    #                 move._compute_fiscal_position_id()
    

    def button_sign_invoice(self, custom_invoice_report_id=None):


        if custom_invoice_report_id:
            invoice_report_id = custom_invoice_report_id
        else:
            invoice_report_id = self.env.ref('account.account_invoices')

        return super(AccountMove, self).button_sign_invoice(invoice_report_id)

    def get_report_name_custom(self):
        """ Using this function we can set Header name of the report """

        with_tax = False
        without_tax = False

        if self.move_type == 'out_invoice':
            if self.invoice_line_ids:
                for line in self.invoice_line_ids.filtered(lambda line: line.display_type not in ['line_note','line_section']):
                    if not line.tax_ids:
                        without_tax = True
                    else:
                        total_tax = sum(line.tax_ids.mapped('amount'))
                        if total_tax > 0:
                            with_tax = True
                        else:
                            without_tax = True

                if with_tax and without_tax:
                    # return 'Invoice Cum Bill Of Supply'
                    if not self.debit_origin_id and self.is_debit_note == False:
                        return 'Invoice Cum Bill Of Supply'
                    else:
                        return 'Debit Note'

                elif with_tax and not without_tax:
                    if not self.debit_origin_id and self.is_debit_note == False:
                        return 'Tax Invoice'
                    else:
                        return 'Debit Note'
                    # return 'Tax Invoice'

                elif not with_tax and without_tax:
                    if not self.debit_origin_id and self.is_debit_note == False:
                        return 'Bill Of Supply'
                    else:
                        return 'Debit Note'


        if self.move_type == 'in_refund':
            return 'Debit Note'
        if self.move_type == 'in_invoice':
            if self.debit_origin_id:
                return 'Credit Note'

    def amount_total_words_india(self, move_id):
        """ amount based on the Indianized """
        #https://timesheet.odoo.com/web#id=1788&cids=1&menu_id=118&action=184&active_id=10&model=project.task&view_type=form
        if move_id.currency_id.name == 'INR':
            amt = round(move_id.amount_total, 2)
            wrd = "Rupees {0} and {1} paise".format(num2words.num2words(str(amt).split('.')[0], lang='en_IN'),
                                                    num2words.num2words(str(amt).split('.')[1], lang='en_IN'))
            return wrd.title()
        else:
            currency_in_word = move_id.currency_id.amount_to_text(move_id.amount_total).replace(',', '')

            return currency_in_word
        

    def tax_amount_in_words(self, total):
        """ Using this function we can fetch amount in word"""

        if self.currency_id.name == 'INR':
            if total == 0:
                return "Rupees Zero"
            else:
                amt = round(total, 2)

                wrd = "Rupees {0} and {1} paise".format(num2words.num2words(str(amt).split('.')[0], lang='en_IN'),
                                                        num2words.num2words(str(amt).split('.')[1], lang='en_IN'))
                return wrd.title()
        else:
            amt = round(total, 2)
            currency_in_word = self.currency_id.amount_to_text(amt).replace(',', '')

            return currency_in_word
            
        

    def _get_b2b_domestic_attachment_filename(self):
        """ Using this function we can set report file name"""
        filename = self._get_move_display_name()
        if self.move_type == 'out_invoice':
            filename = self.name.replace("/", "_") + "Invoice.pdf"
        if self.move_type == 'out_refund':
            filename = self.name.replace("/", "_") + "CreditNote.pdf"
        return filename

    # TODO add the purpose of the below code in comments
    def get_tax_line_main(self):
        """ used for the tax table in the report """

        line_ids = self.env['account.move.line'].search([('move_id', '=', self.id)])

        table_format = True
        for move_line_id in line_ids:
            tax_move_lines = self.env['account.move.line'].search(
                [('group_tax_id', 'in', move_line_id.tax_ids.ids), ('tax_line_id', '!=', False),
                 ('move_id', '=', move_line_id.move_id.id)])
            tax_move_line_sgst = tax_move_lines.filtered(lambda x: x.tax_line_id.tax_group_id.name.upper() == 'SGST')
            tax_move_line_cgst = tax_move_lines.filtered(lambda x: x.tax_line_id.tax_group_id.name.upper() == 'CGST')
            tax_line_ids = tax_move_lines.mapped('tax_line_id')
            sgst_rate = tax_line_ids.filtered(lambda x: x.tax_group_id.name.upper() == 'SGST')
            cgst_rate = tax_line_ids.filtered(lambda x: x.tax_group_id.name.upper() == 'CGST')
            total_tax = 0.0
            if tax_move_line_sgst:
                for line in tax_move_line_sgst:
                    sgst_rate_amount = line.credit if line.credit > 0.0 else line.debit
                    total_tax += sgst_rate_amount
                table_format = False

            if tax_move_line_cgst:
                for line in tax_move_line_cgst:
                    cgst_rate_amount = line.credit if line.credit > 0.0 else line.debit
                    total_tax += cgst_rate_amount
                table_format = False

        return table_format

    # TODO add the purpose of the below code in comments
    def get_tax_line_(self, move_line_id):
        """ used for the tax table in the report """

        if not move_line_id:
            move_line_id = self.env['account.move.line']

        tax_move_lines = self.env['account.move.line'].search(
            [('group_tax_id', 'in', move_line_id.tax_ids.ids), ('tax_line_id', '!=', False),
             ('move_id', '=', move_line_id.move_id.id)])

        tax_move_line_sgst = tax_move_lines.filtered(lambda
                                                         x: x.tax_line_id.tax_group_id.name.upper() == 'SGST')
        tax_move_line_cgst = tax_move_lines.filtered(lambda
                                                         x: x.tax_line_id.tax_group_id.name.upper() == 'CGST')
        tax_line_ids = tax_move_lines.mapped('tax_line_id')
        sgst_rate = tax_line_ids.filtered(lambda x: x.tax_group_id.name.upper() == 'SGST')
        cgst_rate = tax_line_ids.filtered(lambda x: x.tax_group_id.name.upper() == 'CGST')
        sgst_rate_amount = sum(line.credit if line.credit > 0.0 else line.debit for line in tax_move_line_sgst)
        cgst_rate_amount = sum(line.credit if line.credit > 0.0 else line.debit for line in tax_move_line_cgst)
        total_tax = sgst_rate_amount + cgst_rate_amount
        cgst_name = ''
        for line in tax_move_line_cgst:
            cgst_name = line.name.replace(' (Incl)', '')
        sgst_name = ''
        for line in tax_move_line_sgst:
            sgst_name = line.name.replace(' (Incl)', '')
            
        #https://timesheet.odoo.com/web#id=1767&cids=1&menu_id=118&action=184&active_id=10&model=project.task&view_type=form
        decimals = 2
        final_sgst_rate_amount = 0
        for sgst_rate_id in sgst_rate:
            sgst_rate_value = (move_line_id.price_subtotal * sgst_rate_id.amount) / 100
            third_decimal = (sgst_rate_value * 10 ** (decimals + 1)) % 10
            if third_decimal >= 5:
                sgst_rate_amount = math.ceil(sgst_rate_value * 10 ** decimals) / 10 ** decimals
                final_sgst_rate_amount = final_sgst_rate_amount + sgst_rate_amount
            else:
                sgst_rate_amount = math.floor(sgst_rate_value * 10 ** decimals) / 10 ** decimals
                final_sgst_rate_amount = final_sgst_rate_amount + sgst_rate_amount

        final_cgst_rate_value = 0
        for cgst_rate_id in cgst_rate:
            cgst_rate_value = (move_line_id.price_subtotal * cgst_rate_id.amount) / 100
            third_decimal = (cgst_rate_value * 10 ** (decimals + 1)) % 10
            if third_decimal >= 5:
                cgst_rate_amount = math.ceil(cgst_rate_value * 10 ** decimals) / 10 ** decimals
                final_cgst_rate_value = final_cgst_rate_value + cgst_rate_amount
            else:
                cgst_rate_amount = math.floor(cgst_rate_value * 10 ** decimals) / 10 ** decimals
                final_cgst_rate_value = final_cgst_rate_value + cgst_rate_amount

        cgst_rate_amount = final_cgst_rate_value
        sgst_rate_amount = final_sgst_rate_amount

        return_details = False
        if tax_move_line_cgst and tax_move_line_sgst:
            return_details = {
                'tax_move_line_cgst': tax_move_line_cgst,
                'tax_move_line_sgst': tax_move_line_sgst,
                'cgst_rate_amount': cgst_rate_amount,
                'sgst_rate_amount': sgst_rate_amount,
                'sgst_rate': sgst_rate,
                'cgst_rate': cgst_rate,
                'cgst_name': cgst_name,
                'sgst_name': sgst_name,
                'gst': True,
                'igst': False,
                'total_tax': cgst_rate_amount + sgst_rate_amount
            }
        else:
            tax_move_line_igst = tax_move_lines.filtered(
                lambda x: x.tax_line_id.name.upper() == 'IGST' and x.product_id.id == move_line_id.product_id.id)
            

            if tax_move_line_igst:
                return_details = {
                    'tax_move_line_igst': tax_move_line_igst,
                    'gst': False,
                    'igst': True,
                }
            else:
                return_details = {
                    'gst': False,
                    'igst': False,
                    'exempt': True
                }


        return return_details

    def get_org_company_name(self):
        org_company_name = "isha_fnd"
        ir_module_module_object = self.env["ir.module.module"].sudo()
        ishalife = ir_module_module_object.search([("name", "=", "isha_custom_india_ishalife"),
                                        ("state", "=", "installed")
                                        ])
        if ishalife:
            org_company_name = "isha_life"
        isha_usa = ir_module_module_object.search([("name", "=", "isha_usa_payment"),
                                        ("state", "=", "installed")
                                        ])
        if isha_usa:
            org_company_name = "isha_usa"
        return org_company_name

    def show_new_layout(self):
        """Show the new invoice layout if it's a stayflexi booking but not cancelled one."""
        if self.singer_source == "stayflexi":
            sale_ids = self.line_ids.sale_line_ids.order_id
            cancelled_tag = self.env.ref("isha_api_integration.tag_stayflexi_cancelled")
            return cancelled_tag not in sale_ids.tag_ids
        else:
            return False

    def hide_details_for_kshetragna(self):
        # only for the foundation
        
        hide_details = self.env["ir.config_parameter"].sudo().get_param("hide_debit_note_details")
        if hide_details:
            
            for move in self:
                if (self.debit_origin_id or self.is_debit_note) and move.move_type == 'out_invoice' and move.company_id.id in ast.literal_eval(hide_details):
                    return False
                else:
                    return True
        else:
            return True
        
    def hide_details_for_all_branch(self):
        # only for the foundation
        
        hide_details = self.env["ir.config_parameter"].sudo().get_param("hide_debit_note_details")
        if hide_details:
            for move in self:
                if move.move_type == 'out_invoice' and self.debit_origin_id or self.is_debit_note:
                    return False
                else:
                    return True
        else: 
            return True