# -*- coding: utf-8 -*-
# from odoo import http


# class Garaje(http.Controller):
#     @http.route('/garaje/garaje/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/garaje/garaje/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('garaje.listing', {
#             'root': '/garaje/garaje',
#             'objects': http.request.env['garaje.garaje'].search([]),
#         })

#     @http.route('/garaje/garaje/objects/<model("garaje.garaje"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('garaje.object', {
#             'object': obj
#         })
