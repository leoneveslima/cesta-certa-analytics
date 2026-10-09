-- Fato: uma linha por observação de preço (produto x mercado x data).
DROP TABLE IF EXISTS fct_price_history;
CREATE TABLE fct_price_history AS
SELECT
    m.product_id,
    m.product_name,
    s.category,
    s.store,
    s.purchase_date,
    s.purchase_month,
    s.mode,
    s.qty,
    s.unit_price,
    s.line_total
FROM stg_items s
JOIN product_map m ON m.name_norm = s.name_norm;
