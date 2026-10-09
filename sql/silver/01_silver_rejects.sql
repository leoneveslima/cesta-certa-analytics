-- Quarentena: linhas que não entram na análise, com o motivo (nada é descartado em silêncio).
DROP TABLE IF EXISTS silver_rejects;
CREATE TABLE silver_rejects AS
SELECT purchase_id, line_no, name, price, qty, reason
FROM (
    SELECT purchase_id, line_no, name, price, qty,
           CASE
               WHEN norm_name(name) = ''          THEN 'nome_vazio'
               WHEN price IS NULL OR price <= 0   THEN 'sem_preco'
               WHEN qty IS NULL OR qty <= 0       THEN 'quantidade_invalida'
           END AS reason
    FROM bronze_items
)
WHERE reason IS NOT NULL;
