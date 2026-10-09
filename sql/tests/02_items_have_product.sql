-- severity: error
-- description: todo item válido foi associado a um produto (nenhum se perde no casamento de nomes)
SELECT s.purchase_id, s.line_no, s.name FROM stg_items s
WHERE NOT EXISTS (SELECT 1 FROM product_map m WHERE m.name_norm = s.name_norm);
