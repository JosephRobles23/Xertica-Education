"""Prompts centralizados de la API (un módulo por dominio).

Convención: cada módulo expone su system prompt como constante en MAYÚSCULAS
y los templates de mensajes de usuario como funciones puras que reciben las
variables y devuelven el string final. Los servicios importan desde aquí y
no definen texto de prompt inline.
"""
