from odoo import api, fields, models, Command, _


class StockLocationInherit(models.Model):
    _name = "stock.location"
    _inherit = ['stock.location',
                'mail.thread',
                'mail.activity.mixin',
               ]
    
    # https://timesheet.odoo.com/web#id=897&cids=1&menu_id=112&action=184&active_id=4&model=project.task&view_type=form
    # Add Lognote while creating location master
    

class StockPickingOverride(models.Model):
    _inherit = "stock.picking"

    def get_epos_thermal_print_data(self, print_for="picklist"):
        self.ensure_one()
        if print_for == 'invoice':
            report_action = self.env.ref('isha_invoice_report_format.action_invoice_thermal_print')
            move_ids = self.env['account.move'].sudo().search([('picking_id', '=', self.id)]).ids
            datas = report_action.sudo()._render(report_action.report_name, move_ids)
            data_bytes = datas[0]
            return {
                "ip": self.env.user.thermal_printer_ip,
                "mode": self.env.user.thermal_printer_mode,
                "data": data_bytes.decode('utf-8')
            }
        return super(StockPickingOverride, self).get_epos_thermal_print_data(print_for)