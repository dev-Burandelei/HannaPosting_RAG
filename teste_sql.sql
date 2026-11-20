-- Verificar se as FKs estão habilitadas
PRAGMA foreign_keys;

-- Verificar violações de integridade
PRAGMA foreign_key_check;

-- Verificar tabelas
SELECT name
FROM sqlite_master
WHERE type = 'table'
ORDER BY name;

-- Verificar índices
SELECT name, tbl_name
FROM sqlite_master
WHERE type = 'index'
ORDER BY tbl_name, name;