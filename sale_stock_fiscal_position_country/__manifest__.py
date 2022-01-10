{
    "name": "Fiscal Position on sales order from warehouse",
    "summary": "Alters the behavior for changing fiscal position to take the warehouse into consideration",
    "description": "Alters the logic in Oood that determines what fiscal position to use on a sales. The altered logic looks at the shipping address as well as the warehouses",
    "version": "1.0.0",
    "category": "E-Commerce",
    "author": "VK Data ApS",
    "website": "https://vkdata.dk",
    "depends": [
        'sale_stock',
        'sale',
        'fiscal_postion_by_origin_country',
    ],
    "data": [
        
    ],
    "installable": True,
    "license": "OPL-1"
}