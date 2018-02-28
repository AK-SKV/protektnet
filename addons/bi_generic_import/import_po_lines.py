# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import Warning
import binascii
import tempfile
from tempfile import TemporaryFile
from odoo.exceptions import UserError, ValidationError

try:
    import xlrd
except ImportError:
    _logger.debug('Cannot `import xlrd`.')

class import_po_line_wizard(models.TransientModel):

	_name='import.po.line.wizard'

	purchase_order_file=fields.Binary(string="Select File")

	@api.multi
	def import_pol(self):
		fp = tempfile.NamedTemporaryFile(delete= False,suffix=".xlsx")
		fp.write(binascii.a2b_base64(self.purchase_order_file))
		fp.seek(0)
		values = {}
		workbook = xlrd.open_workbook(fp.name)
		sheet = workbook.sheet_by_index(0)
		for row_no in range(sheet.nrows):
			val = {}
			if row_no <= 0:
				fields = map(lambda row:row.value.encode('utf-8'), sheet.row(row_no))
			else:
				line = list(map(lambda row:isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value), sheet.row(row_no)))
				values.update({
							   'product':line[0],
							   'quantity':line[1],
							   'uom':line[2],
							   'description':line[3],
							   'price':line[4],
							   'tax':line[5],
							})
				res = self.create_po_line(values)
		return res

	@api.multi
	def create_po_line(self,values):
		purchase_order_brw=self.env['purchase.order'].browse(self._context.get('active_id'))
		current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
		product=values.get('product')
		uom=values.get('uom')
		product_obj_search=self.env['product.product'].search([('name','=',product)])
		uom_obj_search=self.env['product.uom'].search([('name','=',uom)])
		tax_id_lst=[]
		if values.get('tax'):
		    if ',' in  values.get('tax'):
		        tax_names = values.get('tax').split(',')
		        for name in tax_names:
		            tax= self.env['account.tax'].search([('name', '=', name),('type_tax_use','=','sale')])
		            if not tax:
		                raise Warning(_('"%s" Tax not in your system') % name)
		            tax_id_lst.append(tax.id)
		    else:
		        tax_names = values.get('tax').split(',')
		        tax= self.env['account.tax'].search([('name', '=', tax_names),('type_tax_use','=','sale')])
		        if not tax:
		            raise Warning(_('"%s" Tax not in your system') % tax_names)
		        tax_id_lst.append(tax.id)

		if not uom_obj_search:
			raise Warning(_('UOM "%s" is Not Available') % uom)

		if product_obj_search:
			product_id=product_obj_search
		else:
			product_id=self.env['product.product'].create({'name':product,'lst_price':values.get('price')})

		if purchase_order_brw.state == 'draft':
		    po_order_lines=self.env['purchase.order.line'].create({
											    'order_id':purchase_order_brw.id,
											    'product_id':product_id.id,
											    'name':product,
											    'date_planned':current_time,
											    'product_qty':values.get('quantity'),
											    'product_uom':uom_obj_search.id,
											    'price_unit':values.get('price')
											    })
		elif purchase_order_brw.state == 'sent':
			po_order_lines=self.env['purchase.order.line'].create({
											    'order_id':purchase_order_brw.id,
											    'product_id':product_id.id,
											    'name':product,
											    'date_planned':current_time,
											    'product_qty':values.get('quantity'),
											    'product_uom':uom_obj_search.id,
											    'price_unit':values.get('price')
											    })
		elif purchase_order_brw.state != 'sent' or purchase_order_brw.state != 'draft':
			raise UserError(_('We cannot import data in validated or confirmed order.'))
            
		if tax_id_lst:
			po_order_lines.write({'taxes_id':([(6,0,tax_id_lst)])})
		return True
		
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: