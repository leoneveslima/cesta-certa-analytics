-- severity: error
-- description: nenhum preço unitário zero ou negativo chega às tabelas analíticas
SELECT product_id, store, purchase_date, unit_price FROM fct_price_history WHERE unit_price <= 0;
