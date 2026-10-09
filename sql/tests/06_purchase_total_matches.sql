-- severity: warn
-- description: o total registrado da compra bate com a soma das linhas (tolerância R$ 0,05; itens sem preço contam como 0)
SELECT p.purchase_id, p.total AS registrado, ROUND(SUM(COALESCE(s.line_total, 0)), 2) AS soma_linhas
FROM bronze_purchases p
LEFT JOIN stg_items s USING (purchase_id)
GROUP BY p.purchase_id
HAVING ABS(p.total - SUM(COALESCE(s.line_total, 0))) > 0.05;
