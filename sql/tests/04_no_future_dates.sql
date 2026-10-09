-- severity: error
-- description: nenhuma compra com data no futuro
SELECT purchase_id, purchase_date FROM stg_items WHERE purchase_date > date('now') GROUP BY purchase_id;
