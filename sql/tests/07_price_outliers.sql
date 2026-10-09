-- severity: warn
-- description: preço unitário até 2,5x acima ou abaixo da média do produto (possível erro de digitação)
WITH media AS (SELECT product_id, mode, AVG(unit_price) AS m FROM fct_price_history GROUP BY product_id, mode)
SELECT f.product_id, f.store, f.purchase_date, f.unit_price, ROUND(m.m, 2) AS media
FROM fct_price_history f JOIN media m USING (product_id, mode)
WHERE f.unit_price > 2.5 * m.m OR f.unit_price < m.m / 2.5;
