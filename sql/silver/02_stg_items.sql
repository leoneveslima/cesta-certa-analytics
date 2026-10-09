-- Itens válidos, com data legível e preço unitário comparável.
--   mode 'un'    -> price é por unidade
--   mode 'total' -> price é o valor de todas as unidades (ex.: 8 maçãs por R$ 24): unit_price = price / qty
--   mode 'kg'    -> price é por kg/L; line_total = price * vol / 1000
DROP TABLE IF EXISTS stg_items;
CREATE TABLE stg_items AS
SELECT
    i.purchase_id,
    i.line_no,
    p.store,
    date(p.purchased_at_ms / 1000, 'unixepoch')                AS purchase_date,
    strftime('%Y-%m', p.purchased_at_ms / 1000, 'unixepoch')   AS purchase_month,
    i.name,
    norm_name(i.name)                                          AS name_norm,
    i.category,
    i.qty,
    COALESCE(i.mode, 'un')                                     AS mode,
    CASE COALESCE(i.mode, 'un')
        WHEN 'total' THEN i.price / i.qty
        ELSE i.price
    END                                                        AS unit_price,
    COALESCE(i.total,
        CASE COALESCE(i.mode, 'un')
            WHEN 'kg'    THEN i.price * COALESCE(i.vol, 0) / 1000.0
            WHEN 'total' THEN i.price
            ELSE i.price * i.qty
        END)                                                   AS line_total
FROM bronze_items i
JOIN bronze_purchases p USING (purchase_id)
WHERE NOT EXISTS (
    SELECT 1 FROM silver_rejects r WHERE r.purchase_id = i.purchase_id AND r.line_no = i.line_no
);
