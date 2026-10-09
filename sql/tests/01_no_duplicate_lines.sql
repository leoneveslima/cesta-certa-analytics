-- severity: error
-- description: cada linha (compra, nº da linha) aparece uma só vez na camada silver
SELECT purchase_id, line_no, COUNT(*) AS n FROM stg_items GROUP BY purchase_id, line_no HAVING COUNT(*) > 1;
